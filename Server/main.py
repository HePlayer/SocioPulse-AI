"""
SocioPulse AI 主服务器

模块化的SocioPulse服务器，整合了所有功能组件
包含增强的多Agent讨论框架支持
"""

import os
import logging
import asyncio
from aiohttp import web
from aiohttp_cors import setup as cors_setup, ResourceOptions

from Item.Workflow import WorkflowBuilder
from Item.Agentlib.agent_factory import AgentFactory, AgentCreationConfig, AgentCreationMode
from Item.Agentlib.config_manager import ConfigManager

from .config import HOST, PORT, INDEX_FILE_PATH
from .settings_manager import SettingsManager
from .websocket_handler import WebSocketHandler
from .room_manager import RoomManager
from .room_persistence import RoomPersistence

# 导入多Agent讨论框架组件
from comm.discussion_framework import (
    ContinuousDiscussionController,
    DiscussionFrameworkManager,
    DiscussionEventInterface
)

# 导入消息类型
from Item.Communication.message_types import ChatMessage, MessageType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SocioPulseServer:
    """SocioPulse服务器主类（兼容保留 MultiAIServer 别名）"""

    def __init__(self):
        # 核心状态
        self.app = web.Application()
        self.chat_rooms = {}
        self.websockets = {}

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 初始化工作流构建器（传入配置管理器）
        self.workflow_builder = WorkflowBuilder(config_manager=self.config_manager)

        # 初始化管理器
        self.settings_manager = SettingsManager()
        self.room_persistence = RoomPersistence()

        # 🔧 CRITICAL FIX: 先初始化讨论框架管理器
        self.discussion_framework_manager = DiscussionFrameworkManager()

        # 🔧 CRITICAL FIX: 再初始化WebSocket处理器（传递服务器实例）
        self.websocket_handler = WebSocketHandler(self.chat_rooms, self.websockets, self)

        # 🔧 CRITICAL FIX: 确保WebSocket处理器正确设置到框架管理器
        self._ensure_websocket_integration()

        self.room_manager = RoomManager(self.chat_rooms, self.workflow_builder)

        # 将持久化管理器注入到WebSocket处理器中
        self.websocket_handler.room_persistence = self.room_persistence

        # 初始化增强的模型管理器
        self._initialize_model_manager()

        # 设置讨论框架管理器的引用
        self.room_manager.discussion_framework_manager = self.discussion_framework_manager

        # 将管理器添加到app对象中，以便其他组件可以访问
        self.app['settings_manager'] = self.settings_manager
        self.app['room_manager'] = self.room_manager
        self.app['websocket_handler'] = self.websocket_handler
        self.app['discussion_framework_manager'] = self.discussion_framework_manager

        # 设置路由和CORS
        self._setup_routes()
        self._setup_cors()

        # 记录初始化完成状态
        websocket_status = "✅ 已集成" if (self.discussion_framework_manager and
                                      self.discussion_framework_manager.websocket_handler) else "❌ 未集成"
        logger.info(f"SocioPulse Server with Enhanced Discussion Framework initialized")
        logger.info(f"  WebSocket处理器集成状态: {websocket_status}")

        # 诊断配置状态
        self._log_configuration_status()
    
    def _initialize_model_manager(self):
        """初始化增强的模型管理器"""
        try:
            # 模型管理器已经在WebSocket处理器中初始化
            # 这里只需要确保配置正确传递
            logger.info("Enhanced model manager initialization completed")
        except Exception as e:
            logger.warning(f"Enhanced model manager initialization failed: {e}")

    def _ensure_websocket_integration(self):
        """确保WebSocket处理器正确集成到讨论框架管理器"""
        try:
            logger.info("🔧 开始WebSocket处理器集成验证...")

            if self.discussion_framework_manager and self.websocket_handler:
                # 强制设置WebSocket处理器
                self.discussion_framework_manager.set_websocket_handler(self.websocket_handler)

                # 验证设置是否成功
                if self.discussion_framework_manager.websocket_handler:
                    logger.info("✅ WebSocket处理器成功集成到讨论框架管理器")
                    logger.info(f"  框架管理器WebSocket处理器类型: {type(self.discussion_framework_manager.websocket_handler).__name__}")
                    logger.info(f"  WebSocket处理器实例ID: {id(self.websocket_handler)}")
                    logger.info(f"  框架管理器处理器实例ID: {id(self.discussion_framework_manager.websocket_handler)}")
                else:
                    logger.error("❌ WebSocket处理器集成失败：框架管理器中的处理器为None")
                    raise RuntimeError("WebSocket处理器集成失败")
            else:
                error_details = []
                if not self.discussion_framework_manager:
                    error_details.append("discussion_framework_manager为None")
                if not self.websocket_handler:
                    error_details.append("websocket_handler为None")

                error_msg = f"无法集成WebSocket处理器：{', '.join(error_details)}"
                logger.error(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

        except Exception as e:
            logger.error(f"❌ WebSocket集成过程发生错误: {e}")
            logger.error("这将导致Agent响应无法广播到前端!")
            # 不抛出异常，允许服务器继续启动，但记录严重错误
            logger.error("服务器将继续启动，但讨论功能可能受影响")

    def _setup_routes(self):
        """设置路由"""
        # 首页路由
        self.app.router.add_get('/', self._serve_index)
        # 静态文件服务 - 直接映射UserInterface目录下的所有文件
        self.app.router.add_static('/assets/', 'UserInterface/assets/', show_index=False)
        
        # WebSocket路由
        self.app.router.add_get('/ws', self.websocket_handler.handle_websocket_connection)
        
        # 聊天室API路由
        self.app.router.add_get('/api/rooms', self.room_manager.handle_get_rooms)
        self.app.router.add_post('/api/rooms', self.room_manager.handle_create_room)
        self.app.router.add_get('/api/rooms/{room_id}', self.room_manager.handle_get_room_info)
        self.app.router.add_delete('/api/rooms/{room_id}', self.room_manager.handle_delete_room)
        self.app.router.add_post('/api/rooms/{room_id}/messages', self.room_manager.handle_send_message_to_room)
        self.app.router.add_get('/api/rooms/{room_id}/history', self.room_manager.handle_get_room_history)
        self.app.router.add_get('/api/rooms/{room_id}/export', self.room_manager.handle_export_room_history)
        self.app.router.add_get('/api/rooms/{room_id}/agents', self.room_manager.handle_get_room_agents)
        
        # 设置API路由
        self.app.router.add_get('/api/settings', self.settings_manager.handle_get_settings)
        self.app.router.add_post('/api/settings', self.settings_manager.handle_update_settings)  # 修复：改为POST
        self.app.router.add_put('/api/settings', self.settings_manager.handle_update_settings)   # 保持兼容性
        self.app.router.add_post('/api/test-connection', self.settings_manager.handle_test_api_connection)
        self.app.router.add_post('/api/test_model', self.settings_manager.handle_test_api_connection)  # 添加前端期望的路由
        self.app.router.add_get('/api/available-models', self.settings_manager.handle_get_available_models)
        
        # 增强讨论框架API路由
        self.app.router.add_post('/api/discussion/start', self._handle_start_enhanced_discussion)
        self.app.router.add_get('/api/discussion/status/{room_id}', self._handle_get_discussion_status)
        self.app.router.add_post('/api/discussion/control/{room_id}', self._handle_control_discussion)
        self.app.router.add_get('/api/discussion/all-status', self._handle_get_all_discussion_statuses)
        self.app.router.add_get('/ws/discussion/{room_id}', self._handle_discussion_websocket)

        # 健康检查路由
        self.app.router.add_get('/api/health', self._handle_health_check)

        # 诊断路由
        self.app.router.add_get('/api/debug/config', self._handle_debug_config)
        self.app.router.add_get('/api/debug/platforms', self._handle_debug_platforms)

        logger.info("Routes configured with Enhanced Discussion Framework")

    def _log_configuration_status(self):
        """记录配置状态用于诊断"""
        try:
            available_platforms = self.workflow_builder._get_available_platforms()
            logger.info(f"Available platforms with API keys: {available_platforms}")

            if not available_platforms:
                logger.warning("⚠️ No platforms with API keys found! Agents will use fallback responses.")
                logger.warning("Please check your config.yaml file and ensure API keys are properly configured.")
            else:
                logger.info(f"✅ Found {len(available_platforms)} configured platform(s): {', '.join(available_platforms)}")

            # 测试配置文件路径
            config_path = self.config_manager.config_file_path
            if os.path.exists(config_path):
                logger.info(f"✅ Config file found: {config_path}")
            else:
                logger.error(f"❌ Config file not found: {config_path}")

        except Exception as e:
            logger.error(f"Error during configuration diagnosis: {e}")
    
    def _setup_cors(self):
        """设置CORS"""
        cors = cors_setup(self.app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)
        
        logger.info("CORS configured")
    
    async def _serve_index(self, request):
        """服务主页"""
        try:
            # 优先使用UserInterface中的index.html
            if os.path.exists('UserInterface/index.html'):
                return web.FileResponse('UserInterface/index.html')
            # 备用原始MultiAI.html
            elif os.path.exists(INDEX_FILE_PATH):
                return web.FileResponse(INDEX_FILE_PATH)
            else:
                return web.Response(
                    text="Index file not found. Please ensure UserInterface/index.html or MultiAI.html exists.",
                    status=404
                )
        except Exception as e:
            logger.error(f"Error serving index: {e}")
            return web.Response(text=f"Error: {e}", status=500)
    
    async def _handle_start_enhanced_discussion(self, request):
        """启动增强讨论"""
        try:
            data = await request.json()
            room_id = data.get('room_id')
            user_input = data.get('user_input', '')

            if not room_id:
                return web.json_response(
                    {'success': False, 'error': 'room_id is required'},
                    status=400
                )

            if room_id not in self.chat_rooms:
                return web.json_response(
                    {'success': False, 'error': f'Room {room_id} not found'},
                    status=404
                )

            room = self.chat_rooms[room_id]

            # 创建用户消息
            user_message = ChatMessage(
                sender_id="user",
                content=user_input,
                message_type=MessageType.TEXT
            )

            # 启动增强讨论
            result = await self.discussion_framework_manager.start_enhanced_discussion(
                room_id=room_id,
                topic=user_input[:100],  # 使用前100字符作为主题
                participants=room.agents,
                initial_message=user_message,
                enhanced_history=getattr(room, 'enhanced_history', None),
                communication_strategy=getattr(room, 'communication_strategy', None)
            )

            return web.json_response(result)

        except Exception as e:
            logger.error(f"启动增强讨论错误: {e}")
            return web.json_response(
                {'success': False, 'error': str(e)},
                status=500
            )

    async def _handle_get_discussion_status(self, request):
        """获取讨论状态"""
        try:
            room_id = request.match_info['room_id']
            status = await self.discussion_framework_manager.get_discussion_status(room_id)
            return web.json_response(status)

        except Exception as e:
            logger.error(f"获取讨论状态错误: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def _handle_control_discussion(self, request):
        """控制讨论（暂停、恢复、停止）"""
        try:
            room_id = request.match_info['room_id']
            data = await request.json()
            action = data.get('action')

            if action not in ['pause', 'resume', 'stop']:
                return web.json_response(
                    {'success': False, 'error': 'Invalid action'},
                    status=400
                )

            result = await self.discussion_framework_manager.control_discussion(room_id, action)
            return web.json_response(result)

        except Exception as e:
            logger.error(f"控制讨论错误: {e}")
            return web.json_response(
                {'success': False, 'error': str(e)},
                status=500
            )

    async def _handle_get_all_discussion_statuses(self, request):
        """获取所有活跃讨论的状态"""
        try:
            statuses = await self.discussion_framework_manager.get_all_discussion_statuses()
            return web.json_response(statuses)

        except Exception as e:
            logger.error(f"获取所有讨论状态错误: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def _handle_discussion_websocket(self, request):
        """讨论WebSocket端点"""
        room_id = request.match_info['room_id']
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        try:
            # 检查讨论会话是否存在
            if room_id not in self.discussion_framework_manager.active_sessions:
                await ws.send_json({
                    'error': f'Room {room_id} has no active discussion'
                })
                return ws

            session_info = self.discussion_framework_manager.active_sessions[room_id]
            event_interface = session_info.event_interface

            # 发送初始状态
            await ws.send_json({
                'type': 'initial_status',
                'data': event_interface.get_frontend_status()
            })

            # 监听事件
            while not ws.closed:
                try:
                    # 获取下一个事件（带超时）
                    controller = session_info.controller
                    event = await controller.get_next_event(timeout=1.0)

                    if event:
                        await ws.send_json({
                            'type': 'event',
                            'event_type': event.event_type,
                            'timestamp': event.timestamp,
                            'data': event.data
                        })

                    # 发送心跳
                    await ws.send_json({'type': 'ping'})

                except asyncio.TimeoutError:
                    # 发送周期性状态更新
                    await ws.send_json({
                        'type': 'status_update',
                        'data': event_interface.get_frontend_status()
                    })

                except Exception as e:
                    logger.error(f"WebSocket错误: {e}")
                    break

        except Exception as e:
            logger.error(f"WebSocket连接错误: {e}")

        finally:
            if not ws.closed:
                await ws.close()

        return ws

    async def _handle_debug_config(self, request):
        """调试配置信息"""
        try:
            config_info = {
                'config_file_path': self.config_manager.config_file_path,
                'config_exists': os.path.exists(self.config_manager.config_file_path),
                'available_platforms': [],
                'platform_details': {}
            }

            # 检查各平台API密钥
            test_platforms = ['zhipu', 'aihubmix', 'openai']  # 移除zhipuai别名，避免重复
            for platform in test_platforms:
                api_key = self.config_manager.get_api_key(platform)
                has_key = bool(api_key and api_key.strip())

                if has_key:
                    config_info['available_platforms'].append(platform)

                config_info['platform_details'][platform] = {
                    'has_api_key': has_key,
                    'api_key_length': len(api_key) if api_key else 0,
                    'api_key_preview': f"{api_key[:8]}..." if api_key and len(api_key) > 8 else "None"
                }

            return web.json_response(config_info)

        except Exception as e:
            return web.json_response({
                'error': str(e),
                'config_file_path': getattr(self.config_manager, 'config_file_path', 'Unknown')
            }, status=500)

    async def _handle_debug_platforms(self, request):
        """调试平台信息"""
        try:
            platforms_info = {
                'workflow_builder_platforms': self.workflow_builder._get_available_platforms(),
                'config_manager_test': {}
            }

            # 测试每个平台的API密钥获取
            test_platforms = ['zhipu', 'aihubmix', 'openai']  # 移除zhipuai别名，避免重复
            for platform in test_platforms:
                try:
                    api_key = self.config_manager.get_api_key(platform)
                    platforms_info['config_manager_test'][platform] = {
                        'success': True,
                        'has_key': bool(api_key and api_key.strip()),
                        'key_length': len(api_key) if api_key else 0
                    }
                except Exception as e:
                    platforms_info['config_manager_test'][platform] = {
                        'success': False,
                        'error': str(e)
                    }

            return web.json_response(platforms_info)

        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def _handle_health_check(self, request):
        """健康检查"""
        framework_stats = self.discussion_framework_manager.get_framework_statistics()

        # 添加配置诊断信息
        available_platforms = self.workflow_builder._get_available_platforms()

        return web.json_response({
            'status': 'healthy',
            'version': '1.0.0',
            'active_rooms': len(self.chat_rooms),
            'active_websockets': len(self.websockets),
            'available_platforms': available_platforms,
            'config_file_exists': os.path.exists(self.config_manager.config_file_path),
            'discussion_framework': {
                'active_sessions': framework_stats['active_sessions'],
                'total_sessions_created': framework_stats['total_sessions_created'],
                'total_sessions_completed': framework_stats['total_sessions_completed']
            }
        })
    
    async def start_server(self):
        """启动服务器"""
        try:
            logger.info(f"Starting SocioPulse Server on {HOST}:{PORT}")
            
            # 加载持久化的房间数据
            await self._load_persisted_rooms()
            
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, HOST, PORT)
            await site.start()
            
            # 异步初始化模型管理器配置
            await self._initialize_model_manager_async()
            
            # 启动自动备份
            await self.room_persistence.start_auto_backup(self.chat_rooms)
            
            logger.info(f"Server started successfully on http://{HOST}:{PORT}")
            return runner
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    async def _initialize_model_manager_async(self):
        """异步初始化模型管理器配置"""
        try:
            # 初始化WebSocket处理器的模型管理器
            if hasattr(self.websocket_handler, 'initialize_model_manager_async'):
                await self.websocket_handler.initialize_model_manager_async()
                logger.info("WebSocket handler model manager initialized")
            else:
                logger.warning("WebSocket handler does not support async model manager initialization")
        except Exception as e:
            logger.error(f"Failed to initialize model manager configurations: {e}")
    
    async def _load_persisted_rooms(self):
        """增强的房间恢复策略 - 启用完整的房间持久化恢复"""
        try:
            # 设置服务器重启标记
            self.server_restart_id = f"restart_{int(__import__('time').time())}"
            logger.info(f"Server restart ID: {self.server_restart_id}")
            
            # 检查是否有持久化数据
            persisted_rooms = await self.room_persistence.load_room_data()
            
            if persisted_rooms:
                logger.info(f"Found {len(persisted_rooms)} persisted rooms in storage")
                
                # 恢复房间
                recovered_count = 0
                failed_count = 0
                
                for room_id, room_data in persisted_rooms.items():
                    try:
                        # 恢复房间
                        recovered_room = await self._recover_room_from_data(room_id, room_data)
                        if recovered_room:
                            self.chat_rooms[room_id] = recovered_room
                            recovered_count += 1
                            logger.info(f"✅ Successfully recovered room: {room_id}")
                        else:
                            failed_count += 1
                            logger.warning(f"❌ Failed to recover room: {room_id}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"❌ Error recovering room {room_id}: {e}")
                
                logger.info(f"Room recovery completed: {recovered_count} successful, {failed_count} failed")
                
                # 如果有恢复成功的房间，保存当前状态
                if recovered_count > 0:
                    await self.room_persistence.save_room_data(self.chat_rooms)
                    logger.info("Saved recovered room states")
            else:
                logger.info("No persisted rooms found - starting with clean state")
                
        except Exception as e:
            logger.error(f"Error during room persistence recovery: {e}")
            logger.info("Continuing with clean room state")
    
    async def _recover_room_from_data(self, room_id: str, room_data: dict):
        """从持久化数据恢复房间对象 - 增强版，确保创建真正的ChatRoom对象"""
        try:
            logger.info(f"🔄 Recovering room {room_id} from persistent data")
            
            # 获取房间配置
            config = room_data.get('config', {})
            room_name = config.get('room_name', f'Recovered Room {room_id[:8]}')
            agents_data = room_data.get('agents', [])
            
            if not agents_data:
                logger.warning(f"No agents data found for room {room_id}")
                return None
            
            # 验证Agent配置的有效性
            from .settings_manager import SettingsManager
            settings_manager = SettingsManager()
            settings = settings_manager.get_settings()
            
            if not settings or 'models' not in settings:
                logger.error(f"Cannot recover room {room_id}: system settings unavailable")
                return None
            
            platforms = settings['models']['platforms']
            
            # 验证并调整Agent配置
            valid_agents_config = []
            for agent_data in agents_data:
                try:
                    platform = agent_data.get('platform')
                    model_name = agent_data.get('model_name') or agent_data.get('model')
                    
                    # 检查平台是否仍然可用
                    if platform not in platforms:
                        logger.warning(f"Platform {platform} no longer available for agent {agent_data.get('name')}")
                        continue
                    
                    # 检查API密钥是否仍然配置
                    platform_config = platforms[platform]
                    if not platform_config.get('api_key', '').strip():
                        logger.warning(f"No API key for platform {platform} for agent {agent_data.get('name')}")
                        continue
                    
                    # 检查模型是否仍然可用
                    enabled_models = platform_config.get('enabled_models', [])
                    if model_name not in enabled_models:
                        logger.warning(f"Model {model_name} no longer available on platform {platform}")
                        # 尝试使用平台的默认模型
                        default_model = platform_config.get('default_model')
                        if default_model and default_model in enabled_models:
                            logger.info(f"Using default model {default_model} instead of {model_name}")
                            model_name = default_model
                        else:
                            continue
                    
                    # 确保必要字段存在
                    agent_config = {
                        'name': agent_data.get('name', 'Recovered Agent'),
                        'role': agent_data.get('role', 'assistant'),
                        'platform': platform,
                        'model_name': model_name,
                        'prompt': agent_data.get('custom_prompt') or agent_data.get('prompt', '你是一个有用的AI助手。')
                    }
                    
                    valid_agents_config.append(agent_config)
                    logger.info(f"✅ Agent {agent_config['name']} validated for recovery")
                    
                except Exception as e:
                    logger.error(f"Error validating agent {agent_data.get('name', 'Unknown')}: {e}")
                    continue
            
            if not valid_agents_config:
                logger.error(f"No valid agents found for room {room_id}")
                return None
            
            # 直接创建ChatRoom对象而不是通过RoomManager
            try:
                # 导入必要的类
                from Item.ChatRoom import ChatRoom, ChatRoomConfig, CommunicationMode
                from Item.Agentlib import Agent, AgentRole
                
                # 创建ChatRoom配置
                communication_mode = CommunicationMode.DIRECT
                if config.get('communication_mode'):
                    try:
                        mode_str = config['communication_mode'].replace('CommunicationMode.', '')
                        communication_mode = CommunicationMode[mode_str.upper()]
                    except (KeyError, AttributeError):
                        logger.warning(f"Invalid communication mode in config, using DIRECT")
                
                chat_room_config = ChatRoomConfig(
                    room_id=room_id,
                    room_name=room_name,
                    description=config.get('description', ''),
                    max_agents=config.get('max_agents', 10),
                    communication_mode=communication_mode
                )
                
                # 创建ChatRoom对象
                chat_room = ChatRoom(chat_room_config)
                logger.info(f"✅ Created ChatRoom object for {room_id}")
                
                # 创建并添加Agent对象
                agents_created = 0
                for agent_config in valid_agents_config:
                    try:
                        # 确定Agent角色
                        role = AgentRole.CHAT
                        if agent_config.get('role'):
                            try:
                                role_str = agent_config['role'].replace('AgentRole.', '')
                                role = AgentRole[role_str.upper()]
                            except (KeyError, AttributeError):
                                logger.warning(f"Invalid agent role, using CHAT")
                        
                        # 使用AgentFactory创建Agent对象
                        config_manager = ConfigManager()
                        agent_factory = AgentFactory(config_manager)

                        agent_config_obj = AgentCreationConfig(
                            name=agent_config['name'],
                            role=role,
                            model_type=agent_config['platform'],
                            model_name=agent_config['model_name'],
                            system_prompt=agent_config['prompt'],
                            creation_mode=AgentCreationMode.STANDARD
                        )

                        agent = agent_factory.create_agent(agent_config_obj)
                        
                        # 添加Agent到ChatRoom
                        success = await chat_room.add_agent(agent)
                        if success:
                            agents_created += 1
                            logger.info(f"✅ Added agent {agent.name} to room {room_id}")
                        else:
                            logger.warning(f"Failed to add agent {agent.name} to room {room_id}")
                            
                    except Exception as e:
                        logger.error(f"Error creating agent {agent_config.get('name')}: {e}")
                        continue
                
                if agents_created == 0:
                    logger.error(f"No agents were successfully added to room {room_id}")
                    return None
                
                # 验证ChatRoom对象的完整性
                if not self._validate_chatroom_object(chat_room):
                    logger.error(f"ChatRoom object validation failed for {room_id}")
                    return None
                
                logger.info(f"✅ Successfully recovered room {room_id} with {agents_created} agents")
                return chat_room
                
            except Exception as e:
                logger.error(f"Error creating ChatRoom object for {room_id}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error recovering room {room_id}: {e}")
            return None
    
    def _validate_chatroom_object(self, chat_room) -> bool:
        """验证ChatRoom对象的完整性"""
        try:
            # 检查必要的方法
            required_methods = ['process_user_input', 'add_agent', 'get_room_status', 'send_message']
            for method_name in required_methods:
                if not hasattr(chat_room, method_name):
                    logger.error(f"ChatRoom missing required method: {method_name}")
                    return False
                if not callable(getattr(chat_room, method_name)):
                    logger.error(f"ChatRoom method {method_name} is not callable")
                    return False
            
            # 检查必要的属性
            required_attributes = ['config', 'agents', 'message_history']
            for attr_name in required_attributes:
                if not hasattr(chat_room, attr_name):
                    logger.error(f"ChatRoom missing required attribute: {attr_name}")
                    return False
            
            # 检查配置对象
            if not hasattr(chat_room.config, 'room_id') or not hasattr(chat_room.config, 'room_name'):
                logger.error("ChatRoom config missing required fields")
                return False
            
            # 检查Agent字典
            if not isinstance(chat_room.agents, dict):
                logger.error("ChatRoom agents is not a dictionary")
                return False
            
            # 检查消息历史
            if not isinstance(chat_room.message_history, list):
                logger.error("ChatRoom message_history is not a list")
                return False
            
            logger.info(f"✅ ChatRoom object validation passed for {chat_room.config.room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating ChatRoom object: {e}")
            return False

    async def stop_server(self, runner):
        """停止服务器"""
        try:
            # 停止所有活跃的讨论会话
            if hasattr(self, 'discussion_framework_manager'):
                try:
                    for room_id in list(self.discussion_framework_manager.active_sessions.keys()):
                        await self.discussion_framework_manager.control_discussion(room_id, 'stop')
                    logger.info("All discussion sessions stopped")
                except Exception as e:
                    logger.error(f"Error stopping discussion sessions: {e}")

            # 保存房间数据到持久化存储
            if self.chat_rooms:
                await self.room_persistence.save_room_data(self.chat_rooms)
                logger.info("Room data saved to persistent storage")

            # 停止所有聊天室
            for room_id, room in list(self.chat_rooms.items()):
                try:
                    if hasattr(room, 'stop'):
                        await room.stop()
                except Exception as e:
                    logger.error(f"Error stopping room {room_id}: {e}")

            # 关闭所有WebSocket连接
            for connection_id, ws in list(self.websockets.items()):
                try:
                    await ws.close()
                except Exception as e:
                    logger.error(f"Error closing websocket {connection_id}: {e}")

            # 停止服务器
            await runner.cleanup()
            logger.info("Server stopped")

        except Exception as e:
            logger.error(f"Error stopping server: {e}")


async def create_server():
    """创建并启动服务器实例"""
    server = SocioPulseServer()
    runner = await server.start_server()
    return server, runner


async def main():
    """主函数 - 用于直接运行服务器"""
    import asyncio

    server, runner = await create_server()

    try:
        # 保持服务器运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await server.stop_server(runner)

# 兼容：保留 MultiAIServer 名称指向 SocioPulseServer
MultiAIServer = SocioPulseServer

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
