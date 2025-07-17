"""
WebSocket处理模块 - 完整稳定版
"""

import json
import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime
from aiohttp import web, WSMsgType

from .config import WS_MESSAGE_TYPES

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self, chat_rooms: Dict, websockets: Dict):
        self.chat_rooms = chat_rooms
        self.websockets = websockets
    
    async def handle_websocket_connection(self, request):
        """处理WebSocket连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # 生成连接ID
        connection_id = str(uuid.uuid4())
        self.websockets[connection_id] = ws
        
        logger.info(f"WebSocket connected: {connection_id}")
        
        # 发送欢迎消息
        await ws.send_json({
            'type': WS_MESSAGE_TYPES['CONNECTION'],
            'connection_id': connection_id,
            'message': 'Connected to MultiAI Server'
        })
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(connection_id, data)
                    except json.JSONDecodeError:
                        await ws.send_json({
                            'type': WS_MESSAGE_TYPES['ERROR'],
                            'message': 'Invalid JSON format'
                        })
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            # 清理连接
            if connection_id in self.websockets:
                del self.websockets[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")
            
        return ws
    
    async def _handle_websocket_message(self, connection_id: str, data: Dict[str, Any]):
        """处理WebSocket消息"""
        msg_type = data.get('type')
        
        # 强制调试输出
        logger.info(f"Processing WebSocket message from {connection_id}")
        logger.info(f"Raw message type: '{msg_type}' (Python type: {type(msg_type)})")
        logger.info(f"Available message types in config: {WS_MESSAGE_TYPES}")
        logger.info(f"Full message data: {data}")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        
        # 消息类型标准化和清理
        if not msg_type:
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': 'Missing message type'
            })
            return
        
        msg_type_cleaned = str(msg_type).strip().lower()
        logger.info(f"Cleaned message type: '{msg_type_cleaned}'")
        
        # 创建消息类型映射（容错处理）
        message_handlers = {
            WS_MESSAGE_TYPES['JOIN_ROOM'].lower(): self._handle_join_room,
            WS_MESSAGE_TYPES['SEND_MESSAGE'].lower(): self._handle_send_message, 
            WS_MESSAGE_TYPES['GET_ROOMS'].lower(): self._handle_get_rooms,
            WS_MESSAGE_TYPES['CREATE_ROOM'].lower(): self._handle_create_room,
            WS_MESSAGE_TYPES['DELETE_ROOM'].lower(): self._handle_delete_room,
            WS_MESSAGE_TYPES['GET_ROOM_HISTORY'].lower(): self._handle_get_room_history,
            # 添加别名支持
            'join_room': self._handle_join_room,
            'send_message': self._handle_send_message,
            'get_rooms': self._handle_get_rooms,
            'create_room': self._handle_create_room,
            'createroom': self._handle_create_room,  # 无下划线版本
            'delete_room': self._handle_delete_room,
            'deleteroom': self._handle_delete_room,  # 无下划线版本
            # 添加get_room_history处理器
            'get_room_history': self._handle_get_room_history
        }
        
        # 调试输出所有消息类型
        logger.info(f"Available message types in WS_MESSAGE_TYPES: {WS_MESSAGE_TYPES}")
        logger.info(f"GET_ROOM_HISTORY value: {WS_MESSAGE_TYPES.get('GET_ROOM_HISTORY', 'NOT FOUND')}")
        logger.info(f"Registered handlers: {list(message_handlers.keys())}")
        
        # 查找处理器
        logger.info(f"Looking for handler for: '{msg_type_cleaned}'")
        logger.info(f"Available handlers: {list(message_handlers.keys())}")
        
        handler = message_handlers.get(msg_type_cleaned)
        
        if handler:
            logger.info(f"Found handler for message type: '{msg_type_cleaned}'")
            try:
                await handler(connection_id, data)
                logger.info(f"Successfully processed message type: '{msg_type_cleaned}'")
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await self._send_to_websocket(connection_id, {
                    'type': WS_MESSAGE_TYPES['ERROR'],
                    'message': f'Error processing message: {str(e)}'
                })
        else:
            logger.warning(f"Unsupported message type: {msg_type_cleaned}")
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': f'Unsupported message type: {msg_type}'
            })
    
    async def _handle_join_room(self, connection_id: str, data: Dict[str, Any]):
        """处理加入房间消息"""
        room_id = data.get('room_id')
        if room_id in self.chat_rooms:
            room = self.chat_rooms[room_id]
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ROOM_JOINED'],
                'room_id': room_id,
                'room_info': {
                    'room_id': room_id,
                    'room_name': room['config']['room_name'],
                    'agent_count': len(room['agents'])
                }
            })
        else:
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': f'Room {room_id} not found'
            })
    
    async def _handle_send_message(self, connection_id: str, data: Dict[str, Any]):
        """处理发送消息"""
        room_id = data.get('room_id')
        content = data.get('content')
        
        if room_id in self.chat_rooms:
            # 在实际实现中，这里会处理消息
            await self._broadcast_room_message(room_id, {
                'type': WS_MESSAGE_TYPES['NEW_MESSAGE'],
                'room_id': room_id,
                'message': {
                    'sender': 'user',
                    'content': content,
                    'timestamp': datetime.now().isoformat()
                }
            })
        else:
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': f'Room {room_id} not found'
            })
    
    async def _handle_get_rooms(self, connection_id: str, data: Dict[str, Any]):
        """处理获取房间列表消息 - 防回归修复版"""
        rooms_list = []
        for room_id, room in self.chat_rooms.items():
            try:
                # 多层级房间名称获取策略，确保向后兼容性
                room_name = None
                agent_count = 0
                last_message = "暂无消息"
                
                # 策略1：ChatRoom对象方式
                if hasattr(room, 'get_room_status'):
                    try:
                        room_status = room.get_room_status()
                        room_name = room_status.get('room_name')
                        agent_count = room_status.get('agent_count', 0)
                        logger.info(f"Method 1 - Room status for {room_id}: name='{room_name}', agents={agent_count}")
                    except Exception as e:
                        logger.warning(f"Method 1 failed for {room_id}: {e}")
                
                # 策略2：直接访问config属性
                if not room_name and hasattr(room, 'config'):
                    try:
                        if hasattr(room.config, 'room_name'):
                            room_name = room.config.room_name
                            logger.info(f"Method 2 - Direct config access for {room_id}: '{room_name}'")
                        elif hasattr(room.config, 'get'):
                            room_name = room.config.get('room_name')
                            logger.info(f"Method 2b - Config get method for {room_id}: '{room_name}'")
                    except Exception as e:
                        logger.warning(f"Method 2 failed for {room_id}: {e}")
                
                # 策略3：字典格式访问
                if not room_name and isinstance(room, dict):
                    try:
                        room_name = room.get('config', {}).get('room_name')
                        agent_count = len(room.get('agents', []))
                        logger.info(f"Method 3 - Dict access for {room_id}: '{room_name}', agents={agent_count}")
                    except Exception as e:
                        logger.warning(f"Method 3 failed for {room_id}: {e}")
                
                # 策略4：深度搜索房间名称
                if not room_name:
                    try:
                        # 尝试各种可能的属性路径
                        name_paths = [
                            ['config', 'room_name'],
                            ['config', 'name'],
                            ['room_name'],
                            ['name'],
                            ['settings', 'room_name'],
                            ['metadata', 'room_name']
                        ]
                        
                        for path in name_paths:
                            try:
                                current = room
                                for key in path:
                                    if hasattr(current, key):
                                        current = getattr(current, key)
                                    elif isinstance(current, dict) and key in current:
                                        current = current[key]
                                    else:
                                        current = None
                                        break
                                
                                if current and isinstance(current, str) and current.strip():
                                    room_name = current.strip()
                                    logger.info(f"Method 4 - Deep search for {room_id}: '{room_name}' via {path}")
                                    break
                            except:
                                continue
                    except Exception as e:
                        logger.warning(f"Method 4 failed for {room_id}: {e}")
                
                # 获取agent数量（如果前面没有获取到）
                if agent_count == 0:
                    try:
                        if hasattr(room, 'agents'):
                            agent_count = len(room.agents) if room.agents else 0
                        elif isinstance(room, dict) and 'agents' in room:
                            agent_count = len(room['agents']) if room['agents'] else 0
                    except:
                        agent_count = 0
                
                # 获取最后一条消息
                try:
                    if hasattr(room, 'message_history') and room.message_history:
                        last_msg = room.message_history[-1]
                        if isinstance(last_msg, dict):
                            last_message = last_msg.get('content', '暂无消息')
                        else:
                            last_message = str(last_msg)
                        
                        if len(last_message) > 30:
                            last_message = last_message[:30] + '...'
                    elif isinstance(room, dict) and 'message_history' in room and room['message_history']:
                        last_msg = room['message_history'][-1]
                        last_message = last_msg.get('content', '暂无消息') if isinstance(last_msg, dict) else str(last_msg)
                        if len(last_message) > 30:
                            last_message = last_message[:30] + '...'
                except:
                    last_message = "暂无消息"
                
                # 如果所有策略都失败了，生成一个有意义的默认名称
                if not room_name or room_name.startswith('Room_') and len(room_name) > 10:
                    # 检查是否是UUID格式的默认名称
                    import re
                    uuid_pattern = r'Room_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
                    if re.match(uuid_pattern, room_name or ''):
                        # 使用更友好的默认名称
                        room_name = f"聊天室 {len(rooms_list) + 1}"
                        logger.info(f"UUID pattern detected for {room_id}, using friendly name: '{room_name}'")
                    elif not room_name:
                        room_name = f"聊天室 {len(rooms_list) + 1}"
                        logger.info(f"No name found for {room_id}, using default: '{room_name}'")
                
                # 确保房间名称不为空
                if not room_name or not room_name.strip():
                    room_name = f"聊天室 {len(rooms_list) + 1}"
                
                rooms_list.append({
                    'id': room_id,
                    'room_id': room_id,  # 兼容性
                    'room_name': room_name,
                    'agent_count': agent_count,
                    'last_message': last_message
                })
                
                logger.info(f"✅ Room processed: {room_id} -> name='{room_name}', agents={agent_count}")
                
            except Exception as e:
                logger.error(f"❌ Error processing room {room_id}: {e}")
                # 提供友好的回退选项
                friendly_name = f"聊天室 {len(rooms_list) + 1}"
                rooms_list.append({
                    'id': room_id,
                    'room_id': room_id,
                    'room_name': friendly_name,
                    'agent_count': 0,
                    'last_message': '获取房间信息失败'
                })
                logger.info(f"🔄 Used fallback name for {room_id}: '{friendly_name}'")
        
        logger.info(f"📤 Sending rooms list with {len(rooms_list)} rooms: {[r['room_name'] for r in rooms_list]}")
        await self._send_to_websocket(connection_id, {
            'type': WS_MESSAGE_TYPES['ROOMS_LIST'],
            'rooms': rooms_list
        })
    
    async def _handle_create_room(self, connection_id: str, data: Dict[str, Any]):
        """处理创建房间消息 - 使用RoomManager创建聊天室"""
        try:
            room_name = data.get('room_name', '新聊天室')
            chat_type = data.get('chat_type', 'single')
            agents_config = data.get('agents', [])
            
            if not agents_config:
                await self._send_to_websocket(connection_id, {
                    'type': WS_MESSAGE_TYPES['ERROR'],
                    'message': '至少需要配置一个Agent'
                })
                return
            
            # 检查是否有room_manager
            if not hasattr(self, 'room_manager'):
                # 尝试导入并创建room_manager
                try:
                    from .room_manager import RoomManager
                    from Item.Workflow import WorkflowBuilder
                    
                    # 创建WorkflowBuilder实例
                    workflow_builder = WorkflowBuilder()
                    
                    # 创建RoomManager实例，传递必要的参数
                    self.room_manager = RoomManager(self.chat_rooms, workflow_builder)
                    logger.info("Created new RoomManager instance")
                except Exception as e:
                    logger.error(f"Failed to create RoomManager: {e}")
                    await self._send_to_websocket(connection_id, {
                        'type': WS_MESSAGE_TYPES['ERROR'],
                        'message': f'聊天室管理器不可用，无法创建聊天室: {str(e)}'
                    })
                    return
            
            # 验证Agent配置中的API密钥
            validation_result = await self._validate_agents_config(agents_config)
            if not validation_result['valid']:
                await self._send_to_websocket(connection_id, {
                    'type': WS_MESSAGE_TYPES['ERROR'],
                    'message': validation_result['message']
                })
                return
            
            # 使用room_manager创建聊天室
            try:
                # 检查并调整agents_config中的字段名称
                adjusted_agents = []
                for agent in agents_config:
                    adjusted_agent = agent.copy()
                    
                    # 确保platform字段存在
                    if 'platform' in adjusted_agent:
                        # 确保model_name字段存在（后端期望的字段名）
                        if 'model' in adjusted_agent and 'model_name' not in adjusted_agent:
                            adjusted_agent['model_name'] = adjusted_agent['model']
                    
                    # 确保role字段存在
                    if 'role' not in adjusted_agent and 'role_description' in adjusted_agent:
                        adjusted_agent['role'] = adjusted_agent['role_description']
                    elif 'role' not in adjusted_agent:
                        adjusted_agent['role'] = '助手'
                    
                    # 确保prompt字段存在
                    if 'prompt' not in adjusted_agent and 'system_prompt' in adjusted_agent:
                        adjusted_agent['prompt'] = adjusted_agent['system_prompt']
                    
                    adjusted_agents.append(adjusted_agent)
                
                logger.info(f"Adjusted agents config after validation: {adjusted_agents}")
                
                # 准备创建聊天室的请求数据
                create_data = {
                    'room_name': room_name,
                    'room_type': chat_type,
                    'agents': adjusted_agents
                }
                
                # 创建一个模拟的request对象
                class MockRequest:
                    def __init__(self, app, data):
                        self.app = app
                        self._data = data
                    
                    async def json(self):
                        return self._data
                
                # 创建一个简单的模拟请求对象，不依赖于全局app
                class SimpleRequest:
                    def __init__(self, data):
                        self._data = data
                        # 添加一个简单的app字典，包含必要的组件
                        self._settings_manager = None
                        self.app = {'settings_manager': self.get_settings_manager()}
                    
                    async def json(self):
                        return self._data
                    
                    def get_settings_manager(self):
                        # 如果已经有settings_manager实例，直接使用
                        if self._settings_manager:
                            return self._settings_manager
                        
                        # 否则创建一个新的实例
                        from .settings_manager import SettingsManager
                        self._settings_manager = SettingsManager()
                        
                        # 确保settings_manager有settings属性
                        if not hasattr(self._settings_manager, 'settings'):
                            # 尝试加载设置
                            if hasattr(self._settings_manager, 'get_settings'):
                                settings = self._settings_manager.get_settings()
                                # 如果get_settings返回的是字典，则将其设置为settings属性
                                if isinstance(settings, dict):
                                    self._settings_manager.settings = settings
                        
                        return self._settings_manager
                
                # 创建简化的请求对象
                simple_request = SimpleRequest(create_data)
                
                # 调用room_manager的handle_create_room方法
                response = await self.room_manager.handle_create_room(simple_request)
                
                # 解析响应
                try:
                    # 尝试使用json()方法
                    if hasattr(response, 'json') and callable(response.json):
                        response_data = await response.json()
                    else:
                        # 如果没有json()方法，尝试直接访问text属性并解析
                        if hasattr(response, 'text'):
                            import json
                            response_data = json.loads(response.text)
                        else:
                            # 如果都不行，假设response本身就是数据
                            response_data = response
                except Exception as e:
                    logger.error(f"Error parsing response: {e}")
                    response_data = {'success': False, 'message': f'解析响应时出错: {str(e)}'}
                
                # 检查response是否有status属性
                if hasattr(response, 'status'):
                    success = response.status == 200
                else:
                    # 如果response没有status属性，假设它是一个字典
                    success = response_data.get('success', False)
                
                if success:
                    # 创建成功
                    room_id = response_data.get('room_id')
                    
                    # 发送房间创建成功响应 - 包含agents信息用于前端立即显示
                    await self._send_to_websocket(connection_id, {
                        'type': WS_MESSAGE_TYPES['ROOM_CREATED'],
                        'success': True,
                        'room_id': room_id,
                        'room_name': room_name,
                        'agents': adjusted_agents,  # 添加agents信息
                        'message': f'聊天室 "{room_name}" 创建成功'
                    })
                    
                    # 延迟广播房间列表，确保房间完全创建完成
                    import asyncio
                    async def delayed_broadcast():
                        await asyncio.sleep(0.5)  # 延迟500ms
                        await self._broadcast_rooms_list()
                        logger.info(f"Delayed broadcast completed for room: {room_id}")
                    
                    # 立即执行延迟广播
                    asyncio.create_task(delayed_broadcast())
                    
                    logger.info(f"Room created: {room_id} by connection {connection_id}")
                else:
                    # 创建失败
                    error_message = response_data.get('message', '创建聊天室失败')
                    await self._send_to_websocket(connection_id, {
                        'type': WS_MESSAGE_TYPES['ERROR'],
                        'message': error_message
                    })
            except Exception as e:
                logger.error(f"Error calling room_manager.handle_create_room: {e}")
                await self._send_to_websocket(connection_id, {
                    'type': WS_MESSAGE_TYPES['ERROR'],
                    'message': f'创建聊天室时出错: {str(e)}'
                })
            
        except Exception as e:
            logger.error(f"Error creating room: {e}")
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': f'创建房间失败: {str(e)}'
            })
    
    async def _validate_agents_config(self, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证Agent配置，确保平台和模型有效"""
        from .settings_manager import SettingsManager
        
        try:
            # 获取系统设置
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            
            logger.info(f"Validating agents config with settings: {settings}")
            
            if not settings or 'models' not in settings or 'platforms' not in settings['models']:
                logger.error("System settings unavailable or incomplete")
                return {
                    'valid': False,
                    'message': '系统设置不可用，无法验证Agent配置'
                }
            
            platforms = settings['models']['platforms']
            logger.info(f"Available platforms in settings: {list(platforms.keys())}")
            
            # 获取所有已配置API密钥的平台列表
            available_platforms = []
            for platform_name, platform_config in platforms.items():
                # 检查API密钥是否已配置
                api_key = platform_config.get('api_key', '')
                if api_key:
                    available_platforms.append(platform_name)
            
            logger.info(f"Available platforms with API keys: {available_platforms}")
            
            # 如果没有可用平台，返回错误
            if not available_platforms:
                return {
                    'valid': False,
                    'message': '没有配置任何平台的API密钥，请先在设置中配置API密钥'
                }
            
            # 验证每个Agent的平台和模型
            for i, agent in enumerate(agents):
                platform = agent.get('platform')
                model = agent.get('model')
                name = agent.get('name', f'Agent {i+1}')
                
                # 验证平台是否存在且API密钥已配置
                if not platform or platform not in available_platforms:
                    platform_display_name = platform
                    if platform in {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}:
                        platform_display_name = {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}[platform]
                    
                    # 如果指定的平台没有配置API密钥，但有其他平台配置了API密钥，则自动选择第一个可用的平台
                    if platform in platforms:
                        logger.info(f"Platform {platform} exists but has no API key. Auto-selecting first available platform: {available_platforms[0]}")
                        # 自动更新agent配置中的平台
                        agent['platform'] = available_platforms[0]
                        platform = available_platforms[0]
                        
                        # 获取更新后的平台配置
                        platform_config = platforms[platform]
                        
                        # 自动选择平台的默认模型或第一个可用模型
                        default_model = platform_config.get('default_model')
                        enabled_models = platform_config.get('enabled_models', [])
                        
                        if enabled_models:
                            agent['model'] = default_model if default_model in enabled_models else enabled_models[0]
                            model = agent['model']
                            logger.info(f"Auto-selected model {model} for platform {platform}")
                        else:
                            return {
                                'valid': False,
                                'message': f'平台 {platform_display_name} 没有可用的模型'
                            }
                    else:
                        return {
                            'valid': False,
                            'message': f'Agent "{name}" 使用的平台 {platform_display_name or "未知"} 不存在'
                        }
                
                # 验证模型是否在平台的已启用模型列表中
                platform_config = platforms[platform]
                enabled_models = platform_config.get('enabled_models', [])
                
                if not model or model not in enabled_models:
                    platform_display_name = platform
                    if platform in {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}:
                        platform_display_name = {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}[platform]
                    
                    # 如果指定的模型不可用，但平台有其他可用模型，则自动选择平台的默认模型或第一个可用模型
                    if enabled_models:
                        default_model = platform_config.get('default_model')
                        agent['model'] = default_model if default_model in enabled_models else enabled_models[0]
                        logger.info(f"Auto-selected model {agent['model']} for platform {platform} as {model} is not available")
                    else:
                        return {
                            'valid': False,
                            'message': f'平台 {platform_display_name} 没有可用的模型'
                        }
                
            
            return {
                'valid': True,
                'message': '所有Agent配置验证通过'
            }
            
        except Exception as e:
            logger.error(f"Error validating agents config: {e}")
            return {
                'valid': False,
                'message': f'验证Agent配置时出错: {str(e)}'
            }
    
    async def _handle_delete_room(self, connection_id: str, data: Dict[str, Any]):
        """处理删除房间消息"""
        room_id = data.get('room_id')
        
        if not room_id:
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': '缺少房间ID'
            })
            return
        
        if room_id not in self.chat_rooms:
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': f'房间 {room_id} 不存在'
            })
            return
        
        try:
            # 获取房间信息用于日志记录
            room = self.chat_rooms[room_id]
            room_name = "Unknown Room"
            
            # 标准化获取房间名称
            if hasattr(room, 'config') and hasattr(room.config, 'room_name'):
                room_name = room.config.room_name
            elif hasattr(room, 'room_name'):
                room_name = room.room_name
            elif isinstance(room, dict):
                room_name = room.get('config', {}).get('room_name', f'Room_{room_id}')
            
            # 停止房间（如果是ChatRoom对象）
            if hasattr(room, 'stop'):
                await room.stop()
                logger.info(f"Stopped room {room_name} ({room_id})")
            
            # 从房间字典中删除
            del self.chat_rooms[room_id]
            
            # 发送删除成功响应
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ROOM_DELETED'],
                'success': True,
                'room_id': room_id,
                'room_name': room_name,
                'message': f'聊天室 "{room_name}" 已删除'
            })
            
            # 广播最新的房间列表
            await self._broadcast_rooms_list()
            
            logger.info(f"Room deleted: {room_id} ({room_name}) by connection {connection_id}")
            
        except Exception as e:
            logger.error(f"Error deleting room {room_id}: {e}")
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': f'删除房间失败: {str(e)}'
            })
    
    async def _handle_get_room_history(self, connection_id: str, data: Dict[str, Any]):
        """处理获取房间历史消息"""
        room_id = data.get('room_id')
        
        if room_id not in self.chat_rooms:
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': f'Room {room_id} not found'
            })
            return
        
        # 在实际实现中，这里会从房间获取历史消息
        # 这里提供一个简单的模拟实现
        history = []
        
        await self._send_to_websocket(connection_id, {
            'type': WS_MESSAGE_TYPES['ROOM_HISTORY'],
            'room_id': room_id,
            'messages': history
        })
        
        logger.info(f"Room history sent for room {room_id} to connection {connection_id}")
    
    async def _send_to_websocket(self, connection_id: str, data: Dict[str, Any]):
        """发送消息到WebSocket"""
        if connection_id in self.websockets:
            try:
                await self.websockets[connection_id].send_json(data)
            except Exception as e:
                logger.error(f"Error sending to websocket {connection_id}: {e}")
    
    async def _broadcast_room_message(self, room_id: str, data: Dict[str, Any]):
        """广播消息到房间内所有连接"""
        # 在实际实现中，这里会获取房间内的所有连接
        # 这里简单地广播给所有连接
        await self.broadcast_to_all(data)
    
    async def _broadcast_rooms_list(self):
        """广播最新的房间列表到所有连接 - 防回归修复版"""
        try:
            # 构建房间列表 - 使用与_handle_get_rooms完全相同的逻辑
            rooms_list = []
            for room_id, room in self.chat_rooms.items():
                try:
                    # 多层级房间名称获取策略，与_handle_get_rooms保持一致
                    room_name = None
                    agent_count = 0
                    last_message = "暂无消息"
                    
                    # 策略1：ChatRoom对象方式
                    if hasattr(room, 'get_room_status'):
                        try:
                            room_status = room.get_room_status()
                            room_name = room_status.get('room_name')
                            agent_count = room_status.get('agent_count', 0)
                            logger.info(f"Broadcast Method 1 - Room status for {room_id}: name='{room_name}', agents={agent_count}")
                        except Exception as e:
                            logger.warning(f"Broadcast Method 1 failed for {room_id}: {e}")
                    
                    # 策略2：直接访问config属性
                    if not room_name and hasattr(room, 'config'):
                        try:
                            if hasattr(room.config, 'room_name'):
                                room_name = room.config.room_name
                                logger.info(f"Broadcast Method 2 - Direct config access for {room_id}: '{room_name}'")
                            elif hasattr(room.config, 'get'):
                                room_name = room.config.get('room_name')
                                logger.info(f"Broadcast Method 2b - Config get method for {room_id}: '{room_name}'")
                        except Exception as e:
                            logger.warning(f"Broadcast Method 2 failed for {room_id}: {e}")
                    
                    # 策略3：字典格式访问
                    if not room_name and isinstance(room, dict):
                        try:
                            room_name = room.get('config', {}).get('room_name')
                            agent_count = len(room.get('agents', []))
                            logger.info(f"Broadcast Method 3 - Dict access for {room_id}: '{room_name}', agents={agent_count}")
                        except Exception as e:
                            logger.warning(f"Broadcast Method 3 failed for {room_id}: {e}")
                    
                    # 策略4：深度搜索房间名称
                    if not room_name:
                        try:
                            # 尝试各种可能的属性路径
                            name_paths = [
                                ['config', 'room_name'],
                                ['config', 'name'],
                                ['room_name'],
                                ['name'],
                                ['settings', 'room_name'],
                                ['metadata', 'room_name']
                            ]
                            
                            for path in name_paths:
                                try:
                                    current = room
                                    for key in path:
                                        if hasattr(current, key):
                                            current = getattr(current, key)
                                        elif isinstance(current, dict) and key in current:
                                            current = current[key]
                                        else:
                                            current = None
                                            break
                                    
                                    if current and isinstance(current, str) and current.strip():
                                        room_name = current.strip()
                                        logger.info(f"Broadcast Method 4 - Deep search for {room_id}: '{room_name}' via {path}")
                                        break
                                except:
                                    continue
                        except Exception as e:
                            logger.warning(f"Broadcast Method 4 failed for {room_id}: {e}")
                    
                    # 获取agent数量（如果前面没有获取到）
                    if agent_count == 0:
                        try:
                            if hasattr(room, 'agents'):
                                agent_count = len(room.agents) if room.agents else 0
                            elif isinstance(room, dict) and 'agents' in room:
                                agent_count = len(room['agents']) if room['agents'] else 0
                        except:
                            agent_count = 0
                    
                    # 获取最后一条消息
                    try:
                        if hasattr(room, 'message_history') and room.message_history:
                            last_msg = room.message_history[-1]
                            if isinstance(last_msg, dict):
                                last_message = last_msg.get('content', '暂无消息')
                            else:
                                last_message = str(last_msg)
                            
                            if len(last_message) > 30:
                                last_message = last_message[:30] + '...'
                        elif isinstance(room, dict) and 'message_history' in room and room['message_history']:
                            last_msg = room['message_history'][-1]
                            last_message = last_msg.get('content', '暂无消息') if isinstance(last_msg, dict) else str(last_msg)
                            if len(last_message) > 30:
                                last_message = last_message[:30] + '...'
                    except:
                        last_message = "暂无消息"
                    
                    # 如果所有策略都失败了，生成一个有意义的默认名称
                    if not room_name or room_name.startswith('Room_') and len(room_name) > 10:
                        # 检查是否是UUID格式的默认名称
                        import re
                        uuid_pattern = r'Room_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
                        if re.match(uuid_pattern, room_name or ''):
                            # 使用更友好的默认名称
                            room_name = f"聊天室 {len(rooms_list) + 1}"
                            logger.info(f"Broadcast UUID pattern detected for {room_id}, using friendly name: '{room_name}'")
                        elif not room_name:
                            room_name = f"聊天室 {len(rooms_list) + 1}"
                            logger.info(f"Broadcast No name found for {room_id}, using default: '{room_name}'")
                    
                    # 确保房间名称不为空
                    if not room_name or not room_name.strip():
                        room_name = f"聊天室 {len(rooms_list) + 1}"
                    
                    rooms_list.append({
                        'id': room_id,
                        'room_id': room_id,  # 兼容性
                        'room_name': room_name,
                        'agent_count': agent_count,
                        'last_message': last_message
                    })
                    
                    logger.info(f"✅ Broadcast Room processed: {room_id} -> name='{room_name}', agents={agent_count}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing room {room_id} for broadcast: {e}")
                    # 提供友好的回退选项
                    friendly_name = f"聊天室 {len(rooms_list) + 1}"
                    rooms_list.append({
                        'id': room_id,
                        'room_id': room_id,
                        'room_name': friendly_name,
                        'agent_count': 0,
                        'last_message': '获取房间信息失败'
                    })
                    logger.info(f"🔄 Broadcast Used fallback name for {room_id}: '{friendly_name}'")
            
            # 广播房间列表
            await self.broadcast_to_all({
                'type': WS_MESSAGE_TYPES['ROOMS_LIST'],
                'rooms': rooms_list
            })
            
            logger.info(f"📢 Broadcasted rooms list with {len(rooms_list)} rooms: {[r['room_name'] for r in rooms_list]}")
        except Exception as e:
            logger.error(f"❌ Error broadcasting rooms list: {e}")
    
    async def broadcast_to_all(self, data: Dict[str, Any]):
        """广播消息到所有连接"""
        for connection_id, ws in self.websockets.items():
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
