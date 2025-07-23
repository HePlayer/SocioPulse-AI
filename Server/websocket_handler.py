"""
WebSocket处理模块 - 完整稳定版
增强的模型错误处理，与前端完全兼容
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
    """WebSocket处理器 - 增强的模型错误处理"""
    
    def __init__(self, chat_rooms: Dict, websockets: Dict, server_instance=None):
        self.chat_rooms = chat_rooms
        self.websockets = websockets
        self.server_instance = server_instance  # 添加服务器实例引用
        self.model_manager = None
        self._initialize_model_manager()
    
    def _initialize_model_manager(self):
        """初始化模型管理器"""
        try:
            from Item.Agentlib.model_manager import ModelManagerFactory
            self.model_manager = ModelManagerFactory.get_instance(self.chat_rooms)
            self.model_manager.set_websocket_handler(self)
            logger.info("Model manager initialized for WebSocket handler")
        except Exception as e:
            logger.warning(f"Failed to initialize model manager: {e}")
            self.model_manager = None
    
    async def initialize_model_manager_async(self):
        """异步初始化模型管理器配置"""
        if self.model_manager:
            try:
                from Server.settings_manager import SettingsManager
                settings_manager = SettingsManager()
                settings = settings_manager.get_settings()
                
                if settings and 'models' in settings and 'platforms' in settings['models']:
                    await self.model_manager.initialize(settings['models']['platforms'])
                    logger.info("Model manager configurations loaded")
                else:
                    logger.warning("No model settings found for initialization")
            except Exception as e:
                logger.error(f"Failed to initialize model manager configurations: {e}")
    
    async def handle_websocket_connection(self, request):
        """处理WebSocket连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # 生成连接ID
        connection_id = str(uuid.uuid4())
        self.websockets[connection_id] = ws
        
        logger.info(f"WebSocket connected: {connection_id}")
        
        # 发送欢迎消息，包含服务器重启ID
        welcome_data = {
            'type': WS_MESSAGE_TYPES['CONNECTION'],
            'connection_id': connection_id,
            'message': 'Connected to MultiAI Server'
        }
        
        # 添加服务器重启ID（如果可用）
        if self.server_instance and hasattr(self.server_instance, 'server_restart_id'):
            welcome_data['server_restart_id'] = self.server_instance.server_restart_id
            logger.info(f"Sending server restart ID to {connection_id}: {self.server_instance.server_restart_id}")
        
        await ws.send_json(welcome_data)
        
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
        """处理加入房间消息 - 增强错误处理"""
        room_id = data.get('room_id')
        
        if room_id in self.chat_rooms:
            room = self.chat_rooms[room_id]
            try:
                # 获取房间信息
                room_info = {
                    'room_id': room_id,
                    'agent_count': 0
                }
                
                # 多策略获取房间名称
                room_name = None
                if hasattr(room, 'config') and hasattr(room.config, 'room_name'):
                    room_name = room.config.room_name
                elif isinstance(room, dict):
                    room_name = room.get('config', {}).get('room_name')
                
                room_info['room_name'] = room_name or f'Room_{room_id[:8]}'
                
                # 获取Agent数量
                if hasattr(room, 'agents'):
                    room_info['agent_count'] = len(room.agents) if room.agents else 0
                elif isinstance(room, dict) and 'agents' in room:
                    room_info['agent_count'] = len(room.get('agents', []))
                
                await self._send_to_websocket(connection_id, {
                    'type': WS_MESSAGE_TYPES['ROOM_JOINED'],
                    'room_id': room_id,
                    'room_info': room_info
                })
            except Exception as e:
                logger.error(f"Error processing room join for {room_id}: {e}")
                await self._handle_room_not_found_error(connection_id, room_id, 'join_room')
        else:
            await self._handle_room_not_found_error(connection_id, room_id, 'join_room')
    
    async def _handle_send_message(self, connection_id: str, data: Dict[str, Any]):
        """处理发送消息 - 增强的错误处理版本"""
        room_id = data.get('room_id')
        content = data.get('content', '').strip()
        target_agent_id = data.get('target_agent_id')
        
        logger.info(f"Processing send_message: room_id={room_id}, content_length={len(content)}, target_agent={target_agent_id}")
        
        if not content:
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': '消息内容不能为空'
            })
            return
        
        # 简化房间存在性检查 - 只在必要时进行验证
        if room_id not in self.chat_rooms:
            logger.warning(f"Room {room_id} not found in chat_rooms dict")
            # 不立即返回错误，而是尝试从持久化存储恢复
            if hasattr(self, 'server_instance') and hasattr(self.server_instance, 'room_persistence'):
                try:
                    # 尝试从持久化存储恢复房间
                    recovered = await self.server_instance.room_persistence.recover_room(room_id)
                    if recovered:
                        logger.info(f"Successfully recovered room {room_id} from persistence")
                        # 继续处理消息
                    else:
                        logger.warning(f"Room {room_id} not found in persistence either")
                        await self._handle_room_not_found_error(connection_id, room_id, 'send_message')
                        return
                except Exception as e:
                    logger.error(f"Error recovering room {room_id}: {e}")
                    # 如果恢复失败，但用户能发送消息，说明房间可能存在，继续处理
                    logger.info(f"Continuing message processing for room {room_id} despite recovery failure")
            else:
                # 没有持久化管理器，但用户能发送消息，可能是状态不同步
                logger.warning(f"No persistence manager available, but user can send messages to {room_id}")
                # 不阻止消息处理，只记录警告
        
        # 增强的房间对象验证和自动修复机制
        room = self.chat_rooms[room_id]
        validation_result = await self._validate_and_repair_room(room_id, room)
        
        if not validation_result['valid']:
            logger.warning(f"Room {room_id} validation failed: {validation_result['reason']}")
            
            # 尝试自动修复
            if validation_result['repairable']:
                logger.info(f"Attempting to repair room {room_id}")
                repair_result = await self._attempt_room_repair(room_id, room)
                
                if repair_result['success']:
                    logger.info(f"Successfully repaired room {room_id}")
                    # 更新房间对象
                    self.chat_rooms[room_id] = repair_result['room']
                    room = repair_result['room']
                else:
                    logger.error(f"Failed to repair room {room_id}: {repair_result['error']}")
                    # 清理无效房间
                    del self.chat_rooms[room_id]
                    await self._send_to_websocket(connection_id, {
                        'type': WS_MESSAGE_TYPES['ERROR'],
                        'message': f'聊天室 {room_id} 状态异常且无法修复，已自动清理',
                        'error_code': 'ROOM_REPAIR_FAILED',
                        'room_id': room_id,
                        'action': 'room_cleaned',
                        'suggestion': '请重新创建聊天室',
                        'details': {
                            'repair_error': repair_result['error'],
                            'original_issue': validation_result['reason']
                        }
                    })
                    # 广播更新的房间列表
                    await self._broadcast_rooms_list()
                    return
            else:
                # 不可修复，直接清理
                del self.chat_rooms[room_id]
                await self._send_to_websocket(connection_id, {
                    'type': WS_MESSAGE_TYPES['ERROR'],
                    'message': f'聊天室 {room_id} 状态异常，已自动清理',
                    'error_code': 'ROOM_INVALID',
                    'room_id': room_id,
                    'action': 'room_cleaned',
                    'suggestion': '请重新创建聊天室',
                    'details': {
                        'validation_issue': validation_result['reason'],
                        'repairable': False
                    }
                })
                # 广播更新的房间列表
                await self._broadcast_rooms_list()
                return
        
        try:
            room = self.chat_rooms[room_id]
            
            # 首先广播用户消息
            user_message = {
                'type': WS_MESSAGE_TYPES['NEW_MESSAGE'],
                'room_id': room_id,
                'message': {
                    'id': str(uuid.uuid4()),
                    'sender': 'user',
                    'sender_id': 'user',
                    'content': content,
                    'timestamp': datetime.now().isoformat(),
                    'message_type': 'text'
                }
            }
            
            # 广播用户消息到所有连接
            await self._broadcast_room_message(room_id, user_message)
            logger.info(f"Broadcasted user message to room {room_id}")
            
            # 使用增强的模型管理器处理用户输入（如果可用）
            if self.model_manager:
                try:
                    logger.info(f"Using enhanced model manager for room {room_id}")
                    result = await self.model_manager.process_user_input(room_id, content, target_agent_id)
                    
                    if result.get('success', False):
                        # 成功处理，广播Agent响应
                        agent_message = {
                            'type': WS_MESSAGE_TYPES['NEW_MESSAGE'],
                            'room_id': room_id,
                            'message': {
                                'id': result.get('message_id', str(uuid.uuid4())),
                                'sender': 'agent',  # 保持为'agent'用于前端样式判断
                                'sender_id': result.get('agent_id', 'agent'),
                                'agent_name': result.get('agent_name', 'Agent'),  # 添加agent_name字段
                                'content': result.get('response', ''),
                                'timestamp': datetime.now().isoformat(),
                                'message_type': 'text',
                                'metadata': result.get('metadata', {})
                            }
                        }
                        
                        await self._broadcast_room_message(room_id, agent_message)
                        logger.info(f"Enhanced model manager: Broadcasted agent response to room {room_id}")
                        
                        # 发送成功确认 - 确保Agent名字一致性
                        correct_agent_name = result.get('agent_name', 'Agent')
                        await self._send_to_websocket(connection_id, {
                            'type': WS_MESSAGE_TYPES['MESSAGE_SENT'],
                            'success': True,
                            'room_id': room_id,
                            'agent_response': {
                                'agent_name': correct_agent_name,  # 使用相同的Agent名字
                                'response_length': len(result.get('response', ''))
                            }
                        })
                        return  # 成功处理，直接返回
                    elif result.get('fallback_required', False) and result.get('should_continue', False):
                        # 模型管理器要求回退到原始方法，记录信息并继续
                        logger.info(f"Enhanced model manager requested fallback for room {room_id}: {result.get('reason', 'unknown')}")
                        # 继续使用原有的ChatRoom方法
                    else:
                        # 模型管理器处理失败，记录错误但继续使用原有方法
                        logger.warning(f"Enhanced model manager failed for room {room_id}: {result.get('error', result.get('message', 'unknown error'))}")
                        # 不直接返回，继续使用原有的ChatRoom方法作为备用
                except Exception as e:
                    logger.warning(f"Enhanced model manager error for room {room_id}: {e}")
                    # 继续使用原有方法作为备用
            
            # 原有的ChatRoom处理逻辑（作为备用或主要方法）
            if hasattr(room, 'process_user_input'):
                logger.info(f"Using original ChatRoom method for room {room_id}")
                
                # 调用ChatRoom的process_user_input方法
                result = await room.process_user_input(content, target_agent_id)
                
                logger.info(f"Agent processing result: {result}")
                
                if result.get('success', False):
                    # Agent成功响应，广播Agent的回复
                    agent_message = {
                        'type': WS_MESSAGE_TYPES['NEW_MESSAGE'],
                        'room_id': room_id,
                        'message': {
                            'id': result.get('message_id', str(uuid.uuid4())),
                            'sender': 'agent',  # 保持为'agent'用于前端样式判断
                            'sender_id': result.get('agent_id', 'agent'),
                            'agent_name': result.get('agent_name', 'Agent'),  # 添加agent_name字段
                            'content': result.get('response', ''),
                            'timestamp': datetime.now().isoformat(),
                            'message_type': 'text',
                            'metadata': result.get('metadata', {})
                        }
                    }
                    
                    # 广播Agent响应到所有连接
                    await self._broadcast_room_message(room_id, agent_message)
                    logger.info(f"Broadcasted agent response to room {room_id}")
                    
                    # 发送处理成功确认给发送者 - 确保Agent名字一致性
                    correct_agent_name = result.get('agent_name', 'Agent')
                    await self._send_to_websocket(connection_id, {
                        'type': WS_MESSAGE_TYPES['MESSAGE_SENT'],
                        'success': True,
                        'room_id': room_id,
                        'agent_response': {
                            'agent_name': correct_agent_name,  # 使用相同的Agent名字
                            'response_length': len(result.get('response', ''))
                        }
                    })
                else:
                    # Agent处理失败，发送错误响应
                    error_message = result.get('response', result.get('error', '处理消息时出现错误'))
                    
                    # 广播错误消息
                    error_response = {
                        'type': WS_MESSAGE_TYPES['NEW_MESSAGE'],
                        'room_id': room_id,
                        'message': {
                            'id': str(uuid.uuid4()),
                            'sender': result.get('agent_name', 'System'),
                            'sender_id': result.get('agent_id', 'system'),
                            'content': error_message,
                            'timestamp': datetime.now().isoformat(),
                            'message_type': 'error'
                        }
                    }
                    
                    await self._broadcast_room_message(room_id, error_response)
                    logger.warning(f"Agent processing failed for room {room_id}: {result.get('error')}")
                    
                    # 发送错误确认给发送者
                    await self._send_to_websocket(connection_id, {
                        'type': WS_MESSAGE_TYPES['ERROR'],
                        'message': f'Agent处理失败: {result.get("error", "未知错误")}'
                    })
            else:
                # 如果ChatRoom没有process_user_input方法，发送基础响应
                logger.warning(f"Room {room_id} does not have process_user_input method")
                
                basic_response = {
                    'type': WS_MESSAGE_TYPES['NEW_MESSAGE'],
                    'room_id': room_id,
                    'message': {
                        'id': str(uuid.uuid4()),
                        'sender': 'System',
                        'sender_id': 'system',
                        'content': '抱歉，当前聊天室的Agent暂时无法处理消息。请检查Agent配置。',
                        'timestamp': datetime.now().isoformat(),
                        'message_type': 'system'
                    }
                }
                
                await self._broadcast_room_message(room_id, basic_response)
                
                await self._send_to_websocket(connection_id, {
                    'type': WS_MESSAGE_TYPES['ERROR'],
                    'message': '聊天室Agent暂时不可用'
                })
                
        except Exception as e:
            logger.error(f"Error processing send_message for room {room_id}: {e}")
            
            # 发送系统错误消息
            error_response = {
                'type': WS_MESSAGE_TYPES['NEW_MESSAGE'],
                'room_id': room_id,
                'message': {
                    'id': str(uuid.uuid4()),
                    'sender': 'System',
                    'sender_id': 'system',
                    'content': f'系统错误：{str(e)}',
                    'timestamp': datetime.now().isoformat(),
                    'message_type': 'error'
                }
            }
            
            await self._broadcast_room_message(room_id, error_response)
            
            await self._send_to_websocket(connection_id, {
                'type': WS_MESSAGE_TYPES['ERROR'],
                'message': f'处理消息时发生错误: {str(e)}'
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
                    
                    # 保存房间数据到持久化存储
                    if hasattr(self, 'room_persistence') and self.room_persistence:
                        try:
                            # 获取服务器实例的chat_rooms
                            chat_rooms = getattr(self, 'chat_rooms', {})
                            if hasattr(self, 'server_instance') and self.server_instance:
                                chat_rooms = self.server_instance.chat_rooms
                            
                            await self.room_persistence.save_room_data(chat_rooms)
                            logger.info(f"Room {room_id} data saved to persistent storage")
                        except Exception as e:
                            logger.error(f"Failed to save room {room_id} to persistent storage: {e}")
                    
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
            platform_status = {}
            for platform_name, platform_config in platforms.items():
                # 检查API密钥是否已配置
                api_key = platform_config.get('api_key', '')
                if api_key and api_key.strip():
                    available_platforms.append(platform_name)
                    platform_status[platform_name] = 'available'
                else:
                    platform_status[platform_name] = 'no_api_key'
            
            logger.info(f"Platform status: {platform_status}")
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
                
                logger.info(f"Validating agent {name}: platform={platform}, model={model}")
                
                # 验证平台是否存在
                if not platform or platform not in platforms:
                    return {
                        'valid': False,
                        'message': f'Agent "{name}" 使用的平台 "{platform}" 不存在'
                    }
                
                # 检查平台是否配置了API密钥
                if platform not in available_platforms:
                    platform_display_name = {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}.get(platform, platform)
                    return {
                        'valid': False,
                        'message': f'平台 "{platform_display_name}" 未配置API密钥，请先在设置中配置该平台的API密钥'
                    }
                
                # 验证模型是否在平台的已启用模型列表中
                platform_config = platforms[platform]
                enabled_models = platform_config.get('enabled_models', [])
                
                if not model or model not in enabled_models:
                    platform_display_name = {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}.get(platform, platform)
                    
                    if enabled_models:
                        return {
                            'valid': False,
                            'message': f'模型 "{model}" 在平台 "{platform_display_name}" 中不可用。可用模型: {", ".join(enabled_models)}'
                        }
                    else:
                        return {
                            'valid': False,
                            'message': f'平台 "{platform_display_name}" 没有可用的模型'
                        }
                
                logger.info(f"Agent {name} validation passed: platform={platform}, model={model}")
            
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
            
            # 从持久化存储中删除房间数据
            if hasattr(self, 'room_persistence') and self.room_persistence:
                try:
                    await self.room_persistence.delete_room_data(room_id)
                    logger.info(f"Room {room_id} data deleted from persistent storage")
                    
                    # 保存更新后的房间列表
                    chat_rooms = getattr(self, 'chat_rooms', {})
                    if hasattr(self, 'server_instance') and self.server_instance:
                        chat_rooms = self.server_instance.chat_rooms
                    
                    await self.room_persistence.save_room_data(chat_rooms)
                    logger.info("Updated room list saved to persistent storage")
                except Exception as e:
                    logger.error(f"Failed to delete room {room_id} from persistent storage: {e}")
            
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
    
    async def _handle_room_not_found_error(self, connection_id: str, room_id: str, action: str):
        """处理房间不存在错误 - 增强的错误处理和状态清理"""
        logger.warning(f"Room {room_id} not found during {action}, triggering cleanup")
        
        # 发送详细的错误信息给客户端
        await self._send_to_websocket(connection_id, {
            'type': WS_MESSAGE_TYPES['ERROR'],
            'message': f'聊天室 {room_id} 不存在',
            'error_code': 'ROOM_NOT_FOUND',
            'room_id': room_id,
            'action': 'cleanup_required',
            'details': {
                'action_attempted': action,
                'timestamp': datetime.now().isoformat(),
                'suggestion': '请刷新页面或重新创建聊天室'
            }
        })
        
        # 广播最新的房间列表，帮助所有连接同步状态
        await self._broadcast_rooms_list()
        
        # 如果有房间持久化管理器，也清理持久化数据
        if hasattr(self, 'room_persistence'):
            try:
                await self.room_persistence.delete_room_data(room_id)
                logger.info(f"Cleaned up persistent data for room {room_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup persistent data for room {room_id}: {e}")

    async def _validate_and_repair_room(self, room_id: str, room) -> Dict[str, Any]:
        """验证房间对象并评估修复可能性"""
        try:
            # 基础验证：检查是否是ChatRoom对象
            if hasattr(room, 'process_user_input') and callable(getattr(room, 'process_user_input')):
                # 进一步验证ChatRoom对象的完整性
                required_methods = ['add_agent', 'get_room_status', 'send_message']
                required_attributes = ['config', 'agents', 'message_history']
                
                missing_methods = []
                missing_attributes = []
                
                for method_name in required_methods:
                    if not hasattr(room, method_name) or not callable(getattr(room, method_name)):
                        missing_methods.append(method_name)
                
                for attr_name in required_attributes:
                    if not hasattr(room, attr_name):
                        missing_attributes.append(attr_name)
                
                if missing_methods or missing_attributes:
                    return {
                        'valid': False,
                        'reason': f'ChatRoom对象不完整: 缺少方法{missing_methods}, 缺少属性{missing_attributes}',
                        'repairable': False  # 不完整的ChatRoom对象难以修复
                    }
                
                # 验证配置对象
                if hasattr(room.config, 'room_id') and hasattr(room.config, 'room_name'):
                    return {
                        'valid': True,
                        'reason': 'ChatRoom对象验证通过'
                    }
                else:
                    return {
                        'valid': False,
                        'reason': 'ChatRoom配置对象不完整',
                        'repairable': True  # 配置问题可能可以修复
                    }
            
            # 检查是否是字典格式的房间数据（持久化恢复的常见情况）
            elif isinstance(room, dict):
                # 检查字典是否包含必要的房间信息
                if 'config' in room and 'agents' in room:
                    config = room.get('config', {})
                    agents = room.get('agents', [])
                    
                    if config.get('room_name') and len(agents) > 0:
                        return {
                            'valid': False,
                            'reason': '房间是字典对象而非ChatRoom实例',
                            'repairable': True,  # 字典数据可以转换为ChatRoom对象
                            'repair_data': {
                                'type': 'dict_to_chatroom',
                                'config': config,
                                'agents': agents
                            }
                        }
                    else:
                        return {
                            'valid': False,
                            'reason': '字典房间数据不完整',
                            'repairable': False
                        }
                else:
                    return {
                        'valid': False,
                        'reason': '字典房间缺少必要字段',
                        'repairable': False
                    }
            
            # 其他类型的对象
            else:
                return {
                    'valid': False,
                    'reason': f'房间对象类型无效: {type(room)}',
                    'repairable': False
                }
                
        except Exception as e:
            logger.error(f"Error validating room {room_id}: {e}")
            return {
                'valid': False,
                'reason': f'验证过程出错: {str(e)}',
                'repairable': False
            }
    
    async def _attempt_room_repair(self, room_id: str, room) -> Dict[str, Any]:
        """尝试修复房间对象"""
        try:
            # 如果是字典数据，尝试转换为ChatRoom对象
            if isinstance(room, dict) and 'config' in room and 'agents' in room:
                logger.info(f"Attempting to convert dict room {room_id} to ChatRoom object")
                
                # 使用服务器实例的房间恢复方法
                if self.server_instance and hasattr(self.server_instance, '_recover_room_from_data'):
                    try:
                        recovered_room = await self.server_instance._recover_room_from_data(room_id, room)
                        
                        if recovered_room:
                            # 验证恢复的房间对象
                            validation_result = await self._validate_and_repair_room(room_id, recovered_room)
                            
                            if validation_result['valid']:
                                logger.info(f"Successfully repaired room {room_id} by converting dict to ChatRoom")
                                return {
                                    'success': True,
                                    'room': recovered_room,
                                    'method': 'dict_to_chatroom_conversion'
                                }
                            else:
                                return {
                                    'success': False,
                                    'error': f'恢复的房间对象仍然无效: {validation_result["reason"]}'
                                }
                        else:
                            return {
                                'success': False,
                                'error': '房间恢复方法返回None'
                            }
                            
                    except Exception as e:
                        logger.error(f"Error using server room recovery method: {e}")
                        return {
                            'success': False,
                            'error': f'使用服务器恢复方法失败: {str(e)}'
                        }
                else:
                    return {
                        'success': False,
                        'error': '服务器实例不可用或缺少房间恢复方法'
                    }
            
            # 如果是ChatRoom对象但配置不完整，尝试修复配置
            elif hasattr(room, 'process_user_input') and hasattr(room, 'config'):
                logger.info(f"Attempting to repair ChatRoom config for room {room_id}")
                
                try:
                    # 尝试修复配置对象
                    if not hasattr(room.config, 'room_id'):
                        room.config.room_id = room_id
                    
                    if not hasattr(room.config, 'room_name') or not room.config.room_name:
                        room.config.room_name = f'Repaired Room {room_id[:8]}'
                    
                    # 重新验证
                    validation_result = await self._validate_and_repair_room(room_id, room)
                    
                    if validation_result['valid']:
                        logger.info(f"Successfully repaired ChatRoom config for room {room_id}")
                        return {
                            'success': True,
                            'room': room,
                            'method': 'config_repair'
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'配置修复后仍然无效: {validation_result["reason"]}'
                        }
                        
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'修复配置时出错: {str(e)}'
                    }
            
            else:
                return {
                    'success': False,
                    'error': '房间对象类型不支持修复'
                }
                
        except Exception as e:
            logger.error(f"Error attempting to repair room {room_id}: {e}")
            return {
                'success': False,
                'error': f'修复过程出错: {str(e)}'
            }

    async def broadcast_to_all(self, data: Dict[str, Any]):
        """广播消息到所有连接"""
        for connection_id, ws in self.websockets.items():
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")

    async def _smart_room_validation(self, room_id: str, connection_id: str, action: str) -> bool:
        """智能房间验证 - 减少虚假错误"""
        if room_id in self.chat_rooms:
            return True
        
        # 房间不在内存中，尝试恢复
        logger.info(f"Room {room_id} not in memory, attempting recovery for action: {action}")
        
        # 尝试从持久化存储恢复
        if hasattr(self, 'server_instance') and hasattr(self.server_instance, 'room_persistence'):
            try:
                recovered = await self.server_instance.room_persistence.recover_room(room_id)
                if recovered:
                    logger.info(f"Successfully recovered room {room_id}")
                    return True
            except Exception as e:
                logger.error(f"Room recovery failed for {room_id}: {e}")
        
        # 如果是发送消息操作，且用户能够发送，可能是状态不同步
        if action == 'send_message':
            logger.warning(f"Message sent to non-existent room {room_id}, possible state desync")
            # 发送警告但不阻止操作
            await self._send_to_websocket(connection_id, {
                'type': 'warning',
                'message': f'房间状态可能不同步，正在尝试修复',
                'room_id': room_id,
                'action': 'state_sync_warning'
            })
            return True  # 允许继续处理
        
        # 其他操作则严格验证
        await self._handle_room_not_found_error(connection_id, room_id, action)
        return False
