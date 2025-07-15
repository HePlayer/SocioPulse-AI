"""
Server - MultiAI后端服务器
提供WebSocket和RESTful API接口
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

from aiohttp import web
import aiohttp_cors
from aiohttp import WSMsgType

from Item.ChatRoom import ChatRoom, ChatRoomConfig, CommunicationMode, ChatMessage
from Item.Workflow import WorkflowBuilder, WorkflowExecutor
from Item.Agentlib import Agent, AgentRole, ModelFactory, ModelConfig


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiAIServer:
    """MultiAI服务器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        
        # 存储活跃的聊天室
        self.chat_rooms: Dict[str, ChatRoom] = {}
        
        # 存储WebSocket连接
        self.websockets: Dict[str, web.WebSocketResponse] = {}
        
        # 工作流构建器
        self.workflow_builder = WorkflowBuilder()
        
        # 设置路由
        self._setup_routes()
        
        # 设置CORS
        self._setup_cors()
        
        logger.info(f"SocioPulse AI Server initialized on {host}:{port}")
    
    def _setup_routes(self):
        """设置路由"""
        # WebSocket路由
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # RESTful API路由
        self.app.router.add_get('/api/health', self.health_check)
        self.app.router.add_get('/api/rooms', self.get_rooms)
        self.app.router.add_post('/api/rooms', self.create_room)
        self.app.router.add_get('/api/rooms/{room_id}', self.get_room_info)
        self.app.router.add_delete('/api/rooms/{room_id}', self.delete_room)
        self.app.router.add_post('/api/rooms/{room_id}/agents', self.add_agent_to_room)
        self.app.router.add_delete('/api/rooms/{room_id}/agents/{agent_id}', self.remove_agent_from_room)
        self.app.router.add_post('/api/rooms/{room_id}/message', self.send_message_to_room)
        self.app.router.add_get('/api/rooms/{room_id}/history', self.get_room_history)
        
        # 设置相关API
        self.app.router.add_get('/api/settings', self.get_settings)
        self.app.router.add_post('/api/settings', self.update_settings)
        self.app.router.add_post('/api/test-connection', self.test_api_connection)
        self.app.router.add_get('/api/available-models', self.get_available_models)
        
        # 前端服务 - 直接使用MultiAI.html
        self.app.router.add_get('/', self.serve_index)
        logger.info("Frontend served from MultiAI.html")
    
    def _setup_cors(self):
        """设置CORS"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def serve_index(self, request):
        """服务主页"""
        index_path = os.path.join(os.getcwd(), 'MultiAI.html')
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return web.Response(text=content, content_type='text/html')
        except FileNotFoundError:
            return web.Response(text='MultiAI.html not found', status=404)
    
    async def health_check(self, request):
        """健康检查"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'active_rooms': len(self.chat_rooms),
            'active_connections': len(self.websockets)
        })
    
    async def websocket_handler(self, request):
        """WebSocket处理器"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # 生成连接ID
        connection_id = str(uuid.uuid4())
        self.websockets[connection_id] = ws
        
        logger.info(f"WebSocket connected: {connection_id}")
        
        # 发送欢迎消息
        await ws.send_json({
            'type': 'connection',
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
                            'type': 'error',
                            'message': 'Invalid JSON format'
                        })
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            # 清理连接
            del self.websockets[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")
            
        return ws
    
    async def _handle_websocket_message(self, connection_id: str, data: Dict[str, Any]):
        """处理WebSocket消息"""
        msg_type = data.get('type')
        
        if msg_type == 'join_room':
            room_id = data.get('room_id')
            if room_id in self.chat_rooms:
                # 订阅房间消息
                await self._send_to_websocket(connection_id, {
                    'type': 'room_joined',
                    'room_id': room_id,
                    'room_info': self.chat_rooms[room_id].get_room_status()
                })
            else:
                await self._send_to_websocket(connection_id, {
                    'type': 'error',
                    'message': f'Room {room_id} not found'
                })
        
        elif msg_type == 'send_message':
            room_id = data.get('room_id')
            content = data.get('content')
            target_agent_id = data.get('target_agent_id')
            
            if room_id in self.chat_rooms:
                room = self.chat_rooms[room_id]
                await room.process_user_input(content, target_agent_id)
                
                # 广播消息给所有连接
                await self._broadcast_room_message(room_id, {
                    'type': 'new_message',
                    'room_id': room_id,
                    'message': {
                        'sender': 'user',
                        'content': content,
                        'timestamp': datetime.now().isoformat()
                    }
                })
        
        elif msg_type == 'get_rooms':
            await self._send_to_websocket(connection_id, {
                'type': 'rooms_list',
                'rooms': [
                    {
                        'room_id': room_id,
                        'room_name': room.config.room_name,
                        'agent_count': len(room.agents)
                    }
                    for room_id, room in self.chat_rooms.items()
                ]
            })
    
    async def _send_to_websocket(self, connection_id: str, data: Dict[str, Any]):
        """发送消息到特定WebSocket连接"""
        if connection_id in self.websockets:
            ws = self.websockets[connection_id]
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"Error sending to websocket {connection_id}: {e}")
    
    async def _broadcast_room_message(self, room_id: str, data: Dict[str, Any]):
        """广播房间消息给所有连接"""
        # 这里简化处理，实际应该只发送给订阅了该房间的连接
        for connection_id, ws in self.websockets.items():
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
    
    async def get_rooms(self, request):
        """获取所有聊天室"""
        rooms = []
        for room_id, room in self.chat_rooms.items():
            status = room.get_room_status()
            rooms.append({
                'room_id': room_id,
                'room_name': status['room_name'],
                'description': status['description'],
                'agent_count': status['agent_count'],
                'message_count': status['message_count'],
                'communication_mode': status['communication_mode']
            })
        
        return web.json_response({'rooms': rooms})
    
    def _parse_model_type(self, model_type_str: str) -> tuple[str, str]:
        """
        解析模型类型字符串
        
        Args:
            model_type_str: 格式为 "platform:model" 或 "platform"
            
        Returns:
            (platform, model_name) 元组
        """
        if ':' in model_type_str:
            platform, model_name = model_type_str.split(':', 1)
            return platform.strip(), model_name.strip()
        else:
            # 如果没有指定模型，使用默认模型
            platform = model_type_str.strip()
            default_models = {
                'openai': 'gpt-4',
                'aihubmix': 'gpt-4o-mini',
                'zhipu': 'glm-4'
            }
            return platform, default_models.get(platform, 'gpt-3.5-turbo')
    
    def _is_room_name_unique(self, room_name: str) -> bool:
        """检查房间名称是否唯一"""
        return not any(
            room.config.room_name == room_name 
            for room in self.chat_rooms.values()
        )
    
    def _suggest_unique_room_name(self, base_name: str) -> str:
        """生成唯一的房间名称"""
        if self._is_room_name_unique(base_name):
            return base_name
        
        counter = 1
        while True:
            suggested_name = f"{base_name} ({counter})"
            if self._is_room_name_unique(suggested_name):
                return suggested_name
            counter += 1

    async def create_room(self, request):
        """创建聊天室"""
        created_room = None
        room_id = None
        
        try:
            data = await request.json()
            
            room_id = data.get('room_id', str(uuid.uuid4()))
            room_name = data.get('room_name', f'Room_{room_id[:8]}')
            room_type = data.get('room_type', 'single')  # single 或 group
            description = data.get('description', '')
            max_agents = data.get('max_agents', 10)
            
            # 检查房间名称是否唯一
            if not self._is_room_name_unique(room_name):
                suggested_name = self._suggest_unique_room_name(room_name)
                return web.json_response({
                    'success': False,
                    'error': 'room_name_exists',
                    'message': f'房间名称 "{room_name}" 已存在',
                    'suggested_name': suggested_name
                }, status=400)
            
            # 验证Agent配置
            agents_config = data.get('agents', [])
            if not agents_config:
                return web.json_response({
                    'success': False,
                    'error': 'no_agents',
                    'message': '至少需要配置一个Agent'
                }, status=400)
            
            # 预验证所有Agent配置
            validated_agents = []
            for i, agent_config in enumerate(agents_config):
                agent_name = agent_config.get('name', f'Agent{i+1}')
                # 统一使用CHAT角色，具体专业化通过自定义Prompt实现
                agent_role = 'chat'
                model_type_str = agent_config.get('model_type', 'aihubmix')
                
                # 解析模型类型
                try:
                    platform, model_name = self._parse_model_type(model_type_str)
                    logger.info(f"Parsed model type '{model_type_str}' -> platform: '{platform}', model: '{model_name}'")
                except Exception as e:
                    logger.error(f"Failed to parse model type '{model_type_str}': {e}")
                    return web.json_response({
                        'success': False,
                        'error': 'invalid_model_type',
                        'message': f'Agent "{agent_name}" 的模型类型格式无效: {model_type_str}'
                    }, status=400)
                
                validated_agents.append({
                    'name': agent_name,
                    'role': agent_role,
                    'prompt': agent_config.get('prompt', ''),
                    'platform': platform,
                    'model_name': model_name,
                    'model_type_str': model_type_str
                })
            
            # 根据房间类型设置通信模式
            if room_type == 'group':
                communication_mode = 'network'  # 群聊使用网络模式
            else:
                communication_mode = 'direct'   # 单聊使用直接模式
            
            # 创建聊天室配置
            config = ChatRoomConfig(
                room_id=room_id,
                room_name=room_name,
                description=description,
                max_agents=max_agents,
                communication_mode=CommunicationMode(communication_mode)
            )
            
            # 创建聊天室
            created_room = ChatRoom(config)
            await created_room.start()
            
            logger.info(f"Created room {room_name} ({room_id})")
            
            # 创建并添加Agents
            created_agents = []
            for agent_config in validated_agents:
                try:
                    agent_id = str(uuid.uuid4())
                    
                    # 创建Agent - 使用解析后的平台名称
                    agent = self.workflow_builder.create_agent(
                        agent_id,
                        agent_config['name'],
                        AgentRole(agent_config['role']),
                        agent_config['platform']  # 使用平台名称而不是完整字符串
                    )
                    
                    # 设置自定义Prompt
                    if agent_config['prompt']:
                        agent.set_system_prompt(agent_config['prompt'])
                    
                    # 设置Agent元数据（包含完整的模型信息）
                    agent.set_metadata(
                        role_description=agent_config['role'],
                        custom_prompt=agent_config['prompt'],
                        platform=agent_config['platform'],
                        model_name=agent_config['model_name'],
                        model_type=agent_config['model_type_str']
                    )
                    
                    # 添加到房间
                    await created_room.add_agent(agent)
                    created_agents.append(agent)
                    
                    logger.info(f"Added agent {agent_config['name']} ({agent_config['role']}) "
                              f"with model {agent_config['platform']}:{agent_config['model_name']} to room {room_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create agent {agent_config['name']}: {e}")
                    # 清理已创建的资源
                    if created_room:
                        await created_room.stop()
                    raise Exception(f"创建Agent '{agent_config['name']}' 失败: {str(e)}")
            
            # 只有所有Agent创建成功后才将房间添加到字典中
            self.chat_rooms[room_id] = created_room
            
            return web.json_response({
                'success': True,
                'room_id': room_id,
                'room_info': created_room.get_room_status(),
                'message': f'成功创建{room_type}聊天室，包含 {len(created_agents)} 个Agent'
            })
            
        except Exception as e:
            logger.error(f"Error creating room: {e}")
            
            # 清理资源
            if created_room:
                try:
                    await created_room.stop()
                    logger.info("Cleaned up failed room creation")
                except:
                    pass
            
            # 确保不会留下半创建的房间
            if room_id and room_id in self.chat_rooms:
                del self.chat_rooms[room_id]
            
            return web.json_response({
                'success': False,
                'error': str(e),
                'message': f'创建聊天室失败: {str(e)}'
            }, status=400)
    
    async def get_room_info(self, request):
        """获取聊天室信息"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response({
                'error': f'Room {room_id} not found'
            }, status=404)
        
        room = self.chat_rooms[room_id]
        return web.json_response(room.get_room_status())
    
    async def delete_room(self, request):
        """删除聊天室"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response({
                'error': f'Room {room_id} not found'
            }, status=404)
        
        room = self.chat_rooms[room_id]
        await room.stop()
        del self.chat_rooms[room_id]
        
        return web.json_response({
            'success': True,
            'message': f'Room {room_id} deleted'
        })
    
    async def add_agent_to_room(self, request):
        """添加Agent到聊天室"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response({
                'error': f'Room {room_id} not found'
            }, status=404)
        
        try:
            data = await request.json()
            
            agent = self.workflow_builder.create_agent(
                data.get('agent_id', str(uuid.uuid4())),
                data.get('name', 'New Agent'),
                AgentRole(data.get('role', 'chat')),
                data.get('model_type', 'openai')
            )
            
            # 设置额外的元数据
            if 'metadata' in data:
                agent.set_metadata(**data['metadata'])
            
            room = self.chat_rooms[room_id]
            success = await room.add_agent(agent)
            
            if success:
                return web.json_response({
                    'success': True,
                    'agent_id': agent.component_id,
                    'agent_info': agent.get_agent_info()
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Failed to add agent to room'
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error adding agent: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=400)
    
    async def remove_agent_from_room(self, request):
        """从聊天室移除Agent"""
        room_id = request.match_info['room_id']
        agent_id = request.match_info['agent_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response({
                'error': f'Room {room_id} not found'
            }, status=404)
        
        room = self.chat_rooms[room_id]
        success = await room.remove_agent(agent_id)
        
        if success:
            return web.json_response({
                'success': True,
                'message': f'Agent {agent_id} removed from room'
            })
        else:
            return web.json_response({
                'success': False,
                'error': f'Agent {agent_id} not found in room'
            }, status=404)
    
    async def send_message_to_room(self, request):
        """发送消息到聊天室"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response({
                'error': f'Room {room_id} not found'
            }, status=404)
        
        try:
            data = await request.json()
            content = data.get('content', '')
            target_agent_id = data.get('target_agent_id')
            
            room = self.chat_rooms[room_id]
            await room.process_user_input(content, target_agent_id)
            
            return web.json_response({
                'success': True,
                'message': 'Message sent'
            })
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=400)
    
    async def get_room_history(self, request):
        """获取聊天室历史"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response({
                'error': f'Room {room_id} not found'
            }, status=404)
        
        limit = int(request.query.get('limit', 50))
        
        room = self.chat_rooms[room_id]
        history = room.get_message_history(limit)
        
        return web.json_response({
            'room_id': room_id,
            'history': history,
            'total_messages': len(room.message_history)
        })
    
    async def get_settings(self, request):
        """获取系统设置"""
        try:
            # 从配置文件读取设置
            config_path = os.path.join(os.getcwd(), 'config.yaml')
            if os.path.exists(config_path):
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                return web.json_response({
                    'success': True,
                    'settings': config
                })
            else:
                # 返回默认设置
                default_settings = {
                    'models': {
                        'default_platform': 'aihubmix',
                        'platforms': {
                            'openai': {
                                'api_key': '',
                                'api_base': 'https://api.openai.com/v1',
                                'enabled_models': ['gpt-4'],
                                'default_model': 'gpt-4'
                            },
                            'aihubmix': {
                                'api_key': '',
                                'api_base': 'https://aihubmix.com/v1',
                                'enabled_models': ['gpt-4o-mini'],
                                'default_model': 'gpt-4o-mini'
                            },
                            'zhipu': {
                                'api_key': '',
                                'api_base': 'https://open.bigmodel.cn/api/paas/v4',
                                'enabled_models': ['glm-4'],
                                'default_model': 'glm-4'
                            }
                        }
                    },
                    'features': {
                        'proactive_chat': {
                            'enabled': True,
                            'monitoring_interval': 5,
                            'confidence_threshold': 0.8,
                            'max_suggestions_per_hour': 3
                        }
                    }
                }
                
                return web.json_response({
                    'success': True,
                    'settings': default_settings
                })
                
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    async def update_settings(self, request):
        """更新系统设置"""
        try:
            data = await request.json()
            
            # 保存设置到配置文件
            config_path = os.path.join(os.getcwd(), 'config.yaml')
            
            # 读取现有配置
            existing_config = {}
            if os.path.exists(config_path):
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            
            # 更新配置
            if 'models' in data:
                existing_config['models'] = data['models']
            
            if 'features' in data:
                existing_config['features'] = data['features']
            
            # 保存配置
            import yaml
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info("Settings updated successfully")
            
            return web.json_response({
                'success': True,
                'message': 'Settings updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    async def test_api_connection(self, request):
        """测试API连接"""
        try:
            data = await request.json()
            platform = data.get('platform')
            api_key = data.get('api_key')
            api_base = data.get('api_base')
            
            if not platform or not api_key:
                return web.json_response({
                    'success': False,
                    'error': 'Platform and API key are required'
                }, status=400)
            
            # 根据平台测试连接
            if platform == 'openai':
                success, error = await self._test_openai_connection(api_key, api_base)
            elif platform == 'aihubmix':
                success, error = await self._test_aihubmix_connection(api_key, api_base)
            elif platform == 'zhipu':
                success, error = await self._test_zhipu_connection(api_key, api_base)
            else:
                return web.json_response({
                    'success': False,
                    'error': f'Unsupported platform: {platform}'
                }, status=400)
            
            if success:
                return web.json_response({
                    'success': True,
                    'message': f'{platform} connection successful'
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': error
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error testing API connection: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    async def _test_openai_connection(self, api_key: str, api_base: str) -> tuple[bool, str]:
        """测试OpenAI API连接"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 测试模型列表API
            url = f"{api_base.rstrip('/')}/models"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        return True, "Connection successful"
                    else:
                        error_text = await response.text()
                        return False, f"HTTP {response.status}: {error_text}"
                        
        except Exception as e:
            return False, str(e)
    
    async def _test_aihubmix_connection(self, api_key: str, api_base: str) -> tuple[bool, str]:
        """测试AiHubMix API连接"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 测试模型列表API
            url = f"{api_base.rstrip('/')}/models"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        return True, "Connection successful"
                    else:
                        error_text = await response.text()
                        return False, f"HTTP {response.status}: {error_text}"
                        
        except Exception as e:
            return False, str(e)
    
    async def _test_zhipu_connection(self, api_key: str, api_base: str) -> tuple[bool, str]:
        """测试智谱AI API连接"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 测试简单的聊天API
            url = f"{api_base.rstrip('/')}/chat/completions"
            
            payload = {
                'model': 'glm-4',
                'messages': [{'role': 'user', 'content': 'test'}],
                'max_tokens': 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                    if response.status == 200:
                        return True, "Connection successful"
                    else:
                        error_text = await response.text()
                        return False, f"HTTP {response.status}: {error_text}"
                        
        except Exception as e:
            return False, str(e)
    
    async def get_available_models(self, request):
        """获取可用模型列表"""
        try:
            # 从配置文件读取设置
            config_path = os.path.join(os.getcwd(), 'config.yaml')
            models = []
            
            if os.path.exists(config_path):
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 从配置中提取模型信息
                if 'models' in config and 'platforms' in config['models']:
                    platforms = config['models']['platforms']
                    
                    for platform_name, platform_config in platforms.items():
                        enabled_models = platform_config.get('enabled_models', [])
                        
                        for model_name in enabled_models:
                            models.append({
                                'value': f"{platform_name}:{model_name}",
                                'label': f"{self._get_platform_display_name(platform_name)} - {self._get_model_display_name(model_name)}",
                                'platform': platform_name,
                                'model': model_name,
                                'is_default': model_name == platform_config.get('default_model')
                            })
            
            # 如果没有配置文件，返回默认模型
            if not models:
                default_models = [
                    {
                        'value': 'aihubmix:gpt-4o-mini',
                        'label': 'AiHubMix - GPT-4o Mini',
                        'platform': 'aihubmix',
                        'model': 'gpt-4o-mini',
                        'is_default': True
                    },
                    {
                        'value': 'openai:gpt-4',
                        'label': 'OpenAI - GPT-4',
                        'platform': 'openai',
                        'model': 'gpt-4',
                        'is_default': True
                    },
                    {
                        'value': 'zhipu:glm-4',
                        'label': '智谱AI - GLM-4',
                        'platform': 'zhipu',
                        'model': 'glm-4',
                        'is_default': True
                    }
                ]
                models = default_models
            
            return web.json_response({
                'success': True,
                'models': models
            })
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _get_platform_display_name(self, platform: str) -> str:
        """获取平台显示名称"""
        names = {
            'openai': 'OpenAI',
            'aihubmix': 'AiHubMix',
            'zhipu': '智谱AI'
        }
        return names.get(platform, platform)
    
    def _get_model_display_name(self, model: str) -> str:
        """获取模型显示名称"""
        names = {
            'gpt-4': 'GPT-4',
            'gpt-4-turbo': 'GPT-4 Turbo',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo',
            'gpt-4o-mini': 'GPT-4o Mini',
            'gpt-4o-search-preview': 'GPT-4o Search Preview',
            'gpt-4o-mini-search-preview': 'GPT-4o Mini Search Preview',
            'glm-4': 'GLM-4',
            'glm-4-plus': 'GLM-4 Plus',
            'glm-3-turbo': 'GLM-3 Turbo'
        }
        return names.get(model, model)
    
    async def start(self):
        """启动服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"MultiAI Server started on http://{self.host}:{self.port}")
        
        # 保持服务器运行
        await asyncio.Event().wait()


def main():
    """主函数"""
    # 从环境变量或配置文件读取配置
    host = os.getenv('MULTIAI_HOST', '0.0.0.0')
    port = int(os.getenv('MULTIAI_PORT', 8080))
    
    # 创建并启动服务器
    server = MultiAIServer(host, port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == '__main__':
    main()
