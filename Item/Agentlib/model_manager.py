"""
Model Manager - 统一模型管理器
与现有ChatRoom系统集成，提供增强的错误处理和健康监控
完全兼容现有前端接口，不破坏现有功能
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import json

# 导入增强的模型组件
from .enhanced_models import (
    EnhancedModelAdapter, EnhancedModelConfig, ErrorReporter, HealthMonitor,
    EnhancedZhipuAIAdapter, EnhancedOpenAIAdapter, EnhancedAiHubMixAdapter,
    ModelError, ErrorType, ModelNotFoundError, ModelUnavailableError
)

# 导入现有的基础类
from .Models import ModelConfig


@dataclass
class ModelRequest:
    """模型请求"""
    messages: List[Dict[str, str]]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None


class ModelManager:
    """统一模型管理器 - 与现有ChatRoom系统集成"""
    
    def __init__(self, chat_rooms: Dict = None):
        self.chat_rooms = chat_rooms or {}
        self.adapters: Dict[str, EnhancedModelAdapter] = {}
        self.health_monitor = HealthMonitor()
        self.error_reporter = ErrorReporter()
        self.logger = logging.getLogger(__name__)
        
        # 统计信息
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'error_counts': {}
        }
    
    def set_websocket_handler(self, websocket_handler):
        """设置WebSocket处理器用于错误报告"""
        self.error_reporter.set_websocket_handler(websocket_handler)
    
    async def initialize(self, configs: Dict[str, Dict[str, Any]]):
        """初始化所有模型适配器"""
        for platform, platform_config in configs.items():
            try:
                # 检查是否有API密钥
                api_key = platform_config.get('api_key', '').strip()
                if not api_key:
                    self.logger.warning(f"Platform {platform} has no API key, skipping initialization")
                    continue
                
                # 获取启用的模型列表
                enabled_models = platform_config.get('enabled_models', [])
                if not enabled_models:
                    self.logger.warning(f"Platform {platform} has no enabled models")
                    continue
                
                # 为每个启用的模型创建适配器
                for model_name in enabled_models:
                    adapter_key = f"{platform}_{model_name}"
                    
                    # 创建增强配置
                    enhanced_config = self._create_enhanced_config(platform, model_name, platform_config)
                    
                    # 创建适配器
                    adapter = self._create_adapter(platform, enhanced_config)
                    
                    if adapter:
                        self.adapters[adapter_key] = adapter
                        self.logger.info(f"Initialized adapter: {adapter_key}")
                    
            except Exception as e:
                self.logger.error(f"Failed to initialize platform {platform}: {e}")
        
        self.logger.info(f"Model manager initialized with {len(self.adapters)} adapters")
    
    def _create_enhanced_config(self, platform: str, model_name: str, platform_config: Dict[str, Any]) -> EnhancedModelConfig:
        """创建增强的模型配置"""
        # 基础配置
        config = EnhancedModelConfig(
            model_name=model_name,
            api_key=platform_config['api_key'],
            api_base=platform_config.get('api_base'),
            temperature=platform_config.get('temperature', 0.7),
            max_tokens=platform_config.get('max_tokens', 2000),
            top_p=platform_config.get('top_p', 0.9),
            timeout=platform_config.get('timeout', 60)
        )
        
        # 平台特定配置
        if platform in ['zhipu', 'zhipuai']:
            config.timeout = 120  # 智谱AI需要更长的超时时间
            config.retry_config.max_attempts = 3
            config.retry_config.base_delay = 2.0
        elif platform == 'openai':
            config.retry_config.max_attempts = 3
            config.retry_config.base_delay = 1.0
        elif platform == 'aihubmix':
            config.retry_config.max_attempts = 3
            config.retry_config.base_delay = 1.0
        
        return config
    
    def _create_adapter(self, platform: str, config: EnhancedModelConfig) -> Optional[EnhancedModelAdapter]:
        """创建适配器实例"""
        adapter_classes = {
            'zhipuai': EnhancedZhipuAIAdapter,
            'zhipu': EnhancedZhipuAIAdapter,  # 别名
            'openai': EnhancedOpenAIAdapter,
            'aihubmix': EnhancedAiHubMixAdapter
        }
        
        adapter_class = adapter_classes.get(platform.lower())
        if not adapter_class:
            self.logger.error(f"Unknown platform: {platform}")
            return None
        
        try:
            return adapter_class(f"{platform}_{config.model_name}", config)
        except Exception as e:
            self.logger.error(f"Failed to create adapter for {platform}: {e}")
            return None
    
    async def process_user_input(self, room_id: str, user_input: str, 
                               target_agent_id: Optional[str] = None) -> Dict[str, Any]:
        """处理用户输入 - 与现有ChatRoom接口兼容"""
        self.metrics['total_requests'] += 1
        
        try:
            # 获取房间 - 修复房间验证逻辑，提供更好的兼容性
            room = None
            
            # 方式1：从传入的聊天室字典中查找
            if hasattr(self, 'chat_rooms') and self.chat_rooms and room_id in self.chat_rooms:
                room = self.chat_rooms[room_id]
                self.logger.debug(f"Found room {room_id} in model manager chat_rooms")
            
            # 方式2：如果没有找到，尝试从全局房间管理器获取（如果可用）
            if not room:
                try:
                    # 尝试导入并使用房间管理器
                    from Server.room_manager import RoomManager
                    room_manager = RoomManager()
                    if hasattr(room_manager, 'get_room'):
                        room = room_manager.get_room(room_id)
                        if room:
                            self.logger.debug(f"Found room {room_id} via RoomManager")
                except (ImportError, AttributeError, Exception) as e:
                    self.logger.debug(f"Could not access RoomManager: {e}")
            
            # 方式3：如果仍然没有找到，记录警告但不阻止后续处理
            if not room:
                # 记录警告但不返回成功，让WebSocket处理器继续使用原始ChatRoom方法
                self.logger.warning(f"Room {room_id} not found in model manager, falling back to original ChatRoom method")
                
                # 返回失败状态，但标记为需要回退到原始方法
                return {
                    'success': False,
                    'fallback_required': True,
                    'reason': 'room_not_found_in_model_manager',
                    'message': f'Model manager could not find room {room_id}, fallback to original method',
                    'should_continue': True  # 指示WebSocket处理器应该继续处理
                }
            
            # 如果房间有原生的process_user_input方法，优先使用但增加错误处理
            if hasattr(room, 'process_user_input'):
                try:
                    # 调用原有方法
                    result = await room.process_user_input(user_input, target_agent_id)
                    
                    # 如果原有方法成功，记录成功并返回
                    if result.get('success', True):
                        self.metrics['successful_requests'] += 1
                        return result
                    
                    # 如果原有方法失败，分析错误并报告
                    error_msg = result.get('error', result.get('response', '未知错误'))
                    
                    # 检查是否是模型相关错误
                    if self._is_model_error(error_msg):
                        error_type = self._classify_error_message(error_msg)
                        model_type = self._extract_model_type_from_room(room)
                        
                        await self._report_error(
                            error_type,
                            error_msg,
                            model_type,
                            {'room_id': room_id, 'user_input': user_input[:100]}
                        )
                    
                    self.metrics['failed_requests'] += 1
                    return result
                    
                except Exception as e:
                    # 原有方法抛出异常，进行错误分类和报告
                    error_type = self._classify_exception(e)
                    model_type = self._extract_model_type_from_room(room)
                    
                    await self._report_error(
                        error_type,
                        str(e),
                        model_type,
                        {'room_id': room_id, 'exception_type': type(e).__name__}
                    )
                    
                    self.metrics['failed_requests'] += 1
                    return {
                        'success': False,
                        'error': self._get_user_friendly_error(error_type, model_type)
                    }
            else:
                # 房间没有process_user_input方法
                error_msg = '聊天室Agent暂时不可用'
                await self._report_error('AGENT_UNAVAILABLE', error_msg, 'system', {'room_id': room_id})
                self.metrics['failed_requests'] += 1
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            # 系统级错误
            await self._report_error(
                'SYSTEM_ERROR',
                str(e),
                'system',
                {'room_id': room_id}
            )
            
            self.metrics['failed_requests'] += 1
            return {'success': False, 'error': f'系统错误：{str(e)}'}
    
    def _is_model_error(self, error_msg: str) -> bool:
        """判断是否是模型相关错误"""
        model_error_keywords = [
            'model', 'api', 'timeout', 'connection', 'request timed out',
            'api key', 'quota', 'rate limit', 'authentication', 'unauthorized',
            'openai', 'zhipu', 'aihubmix', 'gpt', 'glm'
        ]
        return any(keyword in error_msg.lower() for keyword in model_error_keywords)
    
    def _classify_error_message(self, error_msg: str) -> str:
        """根据错误消息分类错误类型"""
        error_msg_lower = error_msg.lower()
        
        if 'timeout' in error_msg_lower or 'timed out' in error_msg_lower:
            return 'MODEL_TIMEOUT'
        elif 'api key' in error_msg_lower or 'unauthorized' in error_msg_lower:
            return 'API_KEY_INVALID'
        elif 'quota' in error_msg_lower or 'limit' in error_msg_lower:
            return 'QUOTA_EXCEEDED'
        elif 'connection' in error_msg_lower or 'network' in error_msg_lower:
            return 'CONNECTION_ERROR'
        elif 'rate limit' in error_msg_lower:
            return 'RATE_LIMIT_EXCEEDED'
        else:
            return 'MODEL_CALL_FAILED'
    
    def _classify_exception(self, exception: Exception) -> str:
        """根据异常类型分类错误"""
        if isinstance(exception, asyncio.TimeoutError):
            return 'MODEL_TIMEOUT'
        elif isinstance(exception, ConnectionError):
            return 'CONNECTION_ERROR'
        elif 'api key' in str(exception).lower():
            return 'API_KEY_INVALID'
        else:
            return 'MODEL_CALL_FAILED'
    
    def _extract_model_type_from_room(self, room) -> str:
        """从房间中提取模型类型"""
        try:
            # 尝试多种方式获取模型信息
            if hasattr(room, 'agents') and room.agents:
                # 获取第一个agent的模型信息
                first_agent = list(room.agents.values())[0] if isinstance(room.agents, dict) else room.agents[0]
                
                if hasattr(first_agent, 'model'):
                    model = first_agent.model
                    if hasattr(model, 'config'):
                        return getattr(model.config, 'model_name', 'unknown')
                    elif hasattr(model, 'model_name'):
                        return model.model_name
                
                # 尝试从agent配置中获取
                if hasattr(first_agent, 'config'):
                    config = first_agent.config
                    if hasattr(config, 'model_name'):
                        return config.model_name
                    elif hasattr(config, 'model'):
                        return config.model
            
            # 尝试从房间配置中获取
            if hasattr(room, 'config'):
                config = room.config
                if hasattr(config, 'agents') and config.agents:
                    first_agent_config = config.agents[0] if isinstance(config.agents, list) else list(config.agents.values())[0]
                    if isinstance(first_agent_config, dict):
                        return first_agent_config.get('model', first_agent_config.get('model_name', 'unknown'))
            
            return 'unknown'
        except Exception as e:
            self.logger.warning(f"Failed to extract model type from room: {e}")
            return 'unknown'
    
    def _get_user_friendly_error(self, error_type: str, model_type: str) -> str:
        """获取用户友好的错误消息"""
        friendly_messages = {
            'MODEL_TIMEOUT': f'模型 "{model_type}" 响应超时，请稍后重试',
            'API_KEY_INVALID': f'模型 "{model_type}" 的API密钥无效，请检查设置',
            'QUOTA_EXCEEDED': f'模型 "{model_type}" 配额已用完，请检查账户余额',
            'CONNECTION_ERROR': f'无法连接到模型 "{model_type}"，请检查网络',
            'RATE_LIMIT_EXCEEDED': f'模型 "{model_type}" 请求频率过高，请稍后重试',
            'MODEL_CALL_FAILED': f'模型 "{model_type}" 调用失败，请稍后重试',
            'AGENT_UNAVAILABLE': '聊天室Agent暂时不可用，请检查配置',
            'ROOM_NOT_FOUND': '聊天室不存在',
            'SYSTEM_ERROR': '系统错误，请联系管理员'
        }
        return friendly_messages.get(error_type, f'模型 "{model_type}" 出现未知错误')
    
    async def _report_error(self, error_type: str, error_message: str, 
                          model_type: str, details: Dict[str, Any] = None):
        """报告错误"""
        # 更新错误统计
        if error_type not in self.metrics['error_counts']:
            self.metrics['error_counts'][error_type] = 0
        self.metrics['error_counts'][error_type] += 1
        
        # 使用错误报告器报告
        await self.error_reporter.report_error(error_type, error_message, model_type, details)
    
    async def check_model_health(self, platform: str, model_name: str) -> Dict[str, Any]:
        """检查特定模型的健康状态"""
        adapter_key = f"{platform}_{model_name}"
        
        if adapter_key not in self.adapters:
            return {
                'is_healthy': False,
                'error': f'模型 {platform}/{model_name} 未配置',
                'adapter_key': adapter_key
            }
        
        adapter = self.adapters[adapter_key]
        
        try:
            health_status = await self.health_monitor.check_health(adapter)
            return {
                'is_healthy': health_status.is_healthy,
                'error': health_status.error,
                'response_time': health_status.response_time,
                'consecutive_failures': health_status.consecutive_failures,
                'last_check': health_status.last_check,
                'adapter_key': adapter_key
            }
        except Exception as e:
            return {
                'is_healthy': False,
                'error': str(e),
                'adapter_key': adapter_key
            }
    
    async def get_all_models_health(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的健康状态"""
        health_results = {}
        
        for adapter_key, adapter in self.adapters.items():
            try:
                health_status = await self.health_monitor.check_health(adapter)
                health_results[adapter_key] = health_status.to_dict()
            except Exception as e:
                health_results[adapter_key] = {
                    'is_healthy': False,
                    'error': str(e),
                    'last_check': time.time()
                }
        
        return health_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_rate = 0
        if self.metrics['total_requests'] > 0:
            success_rate = self.metrics['successful_requests'] / self.metrics['total_requests']
        
        return {
            'total_requests': self.metrics['total_requests'],
            'successful_requests': self.metrics['successful_requests'],
            'failed_requests': self.metrics['failed_requests'],
            'success_rate': success_rate,
            'error_counts': self.metrics['error_counts'].copy(),
            'adapters_count': len(self.adapters),
            'available_adapters': list(self.adapters.keys())
        }
    
    async def cleanup(self):
        """清理资源"""
        for adapter in self.adapters.values():
            try:
                if hasattr(adapter, '_cleanup_http_client'):
                    await adapter._cleanup_http_client()
            except Exception as e:
                self.logger.warning(f"Error cleaning up adapter: {e}")
        
        self.adapters.clear()
        self.logger.info("Model manager cleaned up")


class ModelManagerFactory:
    """模型管理器工厂"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls, chat_rooms: Dict = None) -> ModelManager:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = ModelManager(chat_rooms)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        if cls._instance:
            # 异步清理需要在事件循环中执行
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务
                    asyncio.create_task(cls._instance.cleanup())
                else:
                    # 如果事件循环未运行，直接运行
                    loop.run_until_complete(cls._instance.cleanup())
            except Exception as e:
                logging.getLogger(__name__).warning(f"Error during cleanup: {e}")
        
        cls._instance = None


# 兼容性函数，用于与现有代码集成
async def integrate_with_websocket_handler(websocket_handler, chat_rooms: Dict):
    """与WebSocket处理器集成"""
    # 获取模型管理器实例
    model_manager = ModelManagerFactory.get_instance(chat_rooms)
    
    # 设置WebSocket处理器用于错误报告
    model_manager.set_websocket_handler(websocket_handler)
    
    # 尝试从设置中初始化模型配置
    try:
        from Server.settings_manager import SettingsManager
        settings_manager = SettingsManager()
        settings = settings_manager.get_settings()
        
        if settings and 'models' in settings and 'platforms' in settings['models']:
            await model_manager.initialize(settings['models']['platforms'])
        else:
            logging.getLogger(__name__).warning("No model settings found, model manager not initialized")
    
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to initialize model manager: {e}")
    
    return model_manager


# 为WebSocket处理器提供的增强方法
async def enhance_websocket_send_message(websocket_handler, connection_id: str, data: Dict[str, Any]):
    """增强的WebSocket消息发送处理"""
    room_id = data.get('room_id')
    content = data.get('content', '').strip()
    target_agent_id = data.get('target_agent_id')
    
    # 获取模型管理器
    model_manager = ModelManagerFactory.get_instance(websocket_handler.chat_rooms)
    
    # 使用模型管理器处理用户输入
    try:
        result = await model_manager.process_user_input(room_id, content, target_agent_id)
        
        # 根据结果发送相应的WebSocket消息
        if result.get('success', False):
            # 成功处理，发送确认消息
            await websocket_handler._send_to_websocket(connection_id, {
                'type': 'message_sent',
                'success': True,
                'room_id': room_id,
                'agent_response': {
                    'agent_name': result.get('agent_name', 'Agent'),
                    'response_length': len(result.get('response', ''))
                }
            })
        else:
            # 处理失败，发送错误消息（使用现有格式）
            error_message = result.get('error', '处理消息时出现错误')
            await websocket_handler._send_to_websocket(connection_id, {
                'type': 'error',
                'message': error_message
            })
    
    except Exception as e:
        # 系统级错误
        await websocket_handler._send_to_websocket(connection_id, {
            'type': 'error',
            'message': f'系统错误：{str(e)}'
        })
