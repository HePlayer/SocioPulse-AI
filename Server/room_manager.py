"""
聊天室管理模块
"""

import logging
import time
import uuid
from typing import Dict, Any, List
from aiohttp import web

from Item.ChatRoom import ChatRoom, ChatRoomConfig, CommunicationMode
from Item.Workflow import WorkflowBuilder
from Item.Agentlib import Agent, AgentRole

from .config import HTTP_STATUS, ROOM_TYPES, COMMUNICATION_MODES
from .utils import (
    validate_agent_config, 
    is_room_name_unique, 
    suggest_unique_room_name, 
    format_room_info,
    create_error_response,
    create_success_response
)

logger = logging.getLogger(__name__)


class RoomManager:
    """聊天室管理器"""
    
    def __init__(self, chat_rooms: Dict, workflow_builder: WorkflowBuilder):
        self.chat_rooms = chat_rooms
        self.workflow_builder = workflow_builder
    
    async def handle_get_rooms(self, request):
        """获取所有聊天室"""
        try:
            rooms = []
            for room_id, room in self.chat_rooms.items():
                rooms.append(format_room_info(room_id, room))
            
            return web.json_response({'rooms': rooms})
        except Exception as e:
            logger.error(f"Error getting rooms: {e}")
            return web.json_response(
                create_error_response(str(e)), 
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
    
    async def handle_create_room(self, request):
        """创建聊天室"""
        created_room = None
        room_id = None
        
        try:
            data = await request.json()
            
            room_id = data.get('room_id', str(uuid.uuid4()))
            room_name = data.get('room_name', '').strip()  # 确保移除空白字符
            
            # 如果用户没有提供房间名称或提供的是空字符串，使用默认名称
            if not room_name:
                room_name = f'Room_{room_id[:8]}'
            
            room_type = data.get('room_type', ROOM_TYPES['SINGLE'])
            description = data.get('description', '')
            max_agents = data.get('max_agents', 10)
            
            logger.info(f"Creating room with user-provided name: '{room_name}' (room_id: {room_id})")
            
            # 检查房间名称是否唯一
            if not is_room_name_unique(room_name, self.chat_rooms):
                suggested_name = suggest_unique_room_name(room_name, self.chat_rooms)
                return web.json_response(
                    create_error_response(
                        f'房间名称 "{room_name}" 已存在',
                        'room_name_exists'
                    ),
                    status=HTTP_STATUS['BAD_REQUEST']
                )
            
            # 验证Agent配置
            agents_config = data.get('agents', [])
            if not agents_config:
                return web.json_response(
                    create_error_response('至少需要配置一个Agent', 'no_agents'),
                    status=HTTP_STATUS['BAD_REQUEST']
                )
            
            # 获取API配置 - 兼容SimpleRequest
            settings_manager = None
            
            # 尝试从app获取settings_manager
            if hasattr(request, 'app'):
                if isinstance(request.app, dict):
                    # 如果app是字典，直接获取
                    settings_manager = request.app.get('settings_manager')
                else:
                    # 如果app是Application对象，使用get方法
                    try:
                        settings_manager = request.app.get('settings_manager')
                    except AttributeError:
                        # 如果app没有get方法，尝试直接访问
                        try:
                            settings_manager = request.app['settings_manager']
                        except (KeyError, TypeError):
                            pass
            
            # 如果上面的方法都失败了，尝试使用get_settings_manager方法
            if not settings_manager and hasattr(request, 'get_settings_manager'):
                settings_manager = request.get_settings_manager()
            
            if not settings_manager:
                logger.error("Settings manager not available")
                return web.json_response(
                    create_error_response('无法获取系统设置，请检查配置'),
                    status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
                )
            
            # 确保settings_manager有settings属性
            if not hasattr(settings_manager, 'settings'):
                # 尝试加载设置
                if hasattr(settings_manager, 'get_settings'):
                    settings = settings_manager.get_settings()
                    # 如果get_settings返回的是字典，则将其设置为settings属性
                    if isinstance(settings, dict):
                        settings_manager.settings = settings
                else:
                    logger.error("Settings manager does not have settings or get_settings method")
                    return web.json_response(
                        create_error_response('系统设置管理器配置错误'),
                        status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
                    )
            
            platforms_config = settings_manager.settings.get('models', {}).get('platforms', {})
            
            # 获取所有已配置API密钥的平台列表
            available_platforms = []
            for platform_name, platform_config in platforms_config.items():
                # 检查API密钥是否已配置
                api_key = platform_config.get('api_key', '')
                if api_key:
                    available_platforms.append(platform_name)
            
            logger.info(f"Available platforms with API keys: {available_platforms}")
            
            # 如果没有可用平台，返回错误
            if not available_platforms:
                return web.json_response(
                    create_error_response('没有配置任何平台的API密钥，请先在设置中配置API密钥'),
                    status=HTTP_STATUS['BAD_REQUEST']
                )
            
            # 预验证所有Agent配置并检查API可用性
            validated_agents = []
            for i, agent_config in enumerate(agents_config):
                try:
                    # 验证基本配置
                    validated_agent = validate_agent_config(agent_config, i)
                    
                    # 检查平台是否存在且API密钥已配置
                    platform_name = validated_agent['platform']
                    
                    logger.info(f"Validating agent {validated_agent.get('name', f'Agent {i+1}')}: platform={platform_name}")
                    
                    # 检查平台是否存在
                    if platform_name not in platforms_config:
                        platform_display_name = {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}.get(platform_name, platform_name)
                        raise Exception(f"平台 '{platform_display_name}' 不存在")
                    
                    # 检查平台是否配置了API密钥
                    if platform_name not in available_platforms:
                        platform_display_name = {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}.get(platform_name, platform_name)
                        raise Exception(f"平台 '{platform_display_name}' 未配置API密钥，请先在设置中配置该平台的API密钥")
                    
                    # 获取平台配置
                    platform_config = platforms_config.get(platform_name, {})
                    
                    # 检查模型是否在平台的可用模型列表中
                    model_name = validated_agent['model_name']
                    enabled_models = platform_config.get('enabled_models', [])
                    
                    if model_name not in enabled_models:
                        platform_display_name = {'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}.get(platform_name, platform_name)
                        
                        if enabled_models:
                            raise Exception(f"模型 '{model_name}' 在平台 '{platform_display_name}' 中不可用。可用模型: {', '.join(enabled_models)}")
                        else:
                            raise Exception(f"平台 '{platform_display_name}' 没有可用的模型")
                    
                    # 确保model_type_str正确设置
                    validated_agent['model_type_str'] = f"{platform_name}:{model_name}"
                    
                    validated_agents.append(validated_agent)
                    logger.info(f"Agent validation passed: {validated_agent}")
                except Exception as e:
                    logger.error(f"Agent validation failed: {e}")
                    return web.json_response(
                        create_error_response(str(e), 'invalid_agent_config'),
                        status=HTTP_STATUS['BAD_REQUEST']
                    )
            
            # 根据房间类型设置通信模式
            communication_mode = (
                COMMUNICATION_MODES['NETWORK'] if room_type == ROOM_TYPES['GROUP'] 
                else COMMUNICATION_MODES['DIRECT']
            )
            
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
                    
                    # 创建Agent - 使用验证阶段已更新的平台名称
                    # 确保使用的平台已经配置了API密钥
                    platform_name = agent_config['platform']
                    
                    # 这里不需要再次检查和切换平台，因为在验证阶段已经完成了
                    # 直接使用validated_agent中已更新的平台名称
                    
                    agent = self.workflow_builder.create_agent(
                        agent_id,
                        agent_config['name'],
                        AgentRole(agent_config['role']),
                        platform_name,
                        model_name=agent_config['model_name']  # 传递用户选择的模型名称
                    )
                    
                    # 设置自定义Prompt
                    if agent_config['prompt']:
                        agent.set_system_prompt(agent_config['prompt'])
                    
                    # 设置Agent元数据 - 确保所有信息正确设置
                    agent.set_metadata(
                        role_description=agent_config['role'],
                        custom_prompt=agent_config['prompt'],
                        platform=agent_config['platform'],
                        model_name=agent_config['model_name'],
                        model_type=agent_config['model_type_str'],
                        # 添加更多详细信息用于前端显示
                        platform_display_name={'openai': 'OpenAI', 'aihubmix': 'AiHubMix', 'zhipu': '智谱AI', 'zhipuai': '智谱AI'}.get(agent_config['platform'], agent_config['platform']),
                        model_display_name=agent_config['model_name'],
                        api_configured=True,  # 标记API已配置
                        creation_timestamp=time.time()
                    )
                    
                    # 额外验证：确保元数据正确设置
                    metadata = agent.get_metadata()
                    logger.info(f"Agent {agent_config['name']} metadata after setting: {metadata}")
                    
                    # 添加到房间
                    await created_room.add_agent(agent)
                    created_agents.append(agent)
                    
                    logger.info(f"Added agent {agent_config['name']} to room {room_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create agent {agent_config['name']}: {e}")
                    # 清理已创建的资源
                    if created_room:
                        await created_room.stop()
                    raise Exception(f"创建Agent '{agent_config['name']}' 失败: {str(e)}")
            
            # 只有所有Agent创建成功后才将房间添加到字典中
            self.chat_rooms[room_id] = created_room
            
            return web.json_response(create_success_response(
                message=f'成功创建{room_type}聊天室，包含 {len(created_agents)} 个Agent',
                room_id=room_id,
                room_info=created_room.get_room_status()
            ))
            
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
            
            return web.json_response(
                create_error_response(f'创建聊天室失败: {str(e)}'),
                status=HTTP_STATUS['BAD_REQUEST']
            )
    
    async def handle_get_room_info(self, request):
        """获取聊天室信息"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response(
                create_error_response(f'Room {room_id} not found'),
                status=HTTP_STATUS['NOT_FOUND']
            )
        
        room = self.chat_rooms[room_id]
        return web.json_response(room.get_room_status())
    
    async def handle_delete_room(self, request):
        """删除聊天室"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response(
                create_error_response(f'Room {room_id} not found'),
                status=HTTP_STATUS['NOT_FOUND']
            )
        
        try:
            room = self.chat_rooms[room_id]
            await room.stop()
            del self.chat_rooms[room_id]
            
            return web.json_response(create_success_response(
                message=f'Room {room_id} deleted'
            ))
        except Exception as e:
            logger.error(f"Error deleting room {room_id}: {e}")
            return web.json_response(
                create_error_response(str(e)),
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
    
    async def handle_send_message_to_room(self, request):
        """发送消息到聊天室"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response(
                create_error_response(f'Room {room_id} not found'),
                status=HTTP_STATUS['NOT_FOUND']
            )
        
        try:
            data = await request.json()
            content = data.get('content', '')
            target_agent_id = data.get('target_agent_id')
            
            room = self.chat_rooms[room_id]
            result = await room.process_user_input(content, target_agent_id)
            
            if result.get('success', False):
                return web.json_response(create_success_response(
                    message='Message sent successfully',
                    agent_response={
                        'agent_name': result.get('agent_name'),
                        'response': result.get('response'),
                        'agent_id': result.get('agent_id')
                    }
                ))
            else:
                return web.json_response(
                    create_error_response(result.get('error', 'Failed to process message')),
                    status=HTTP_STATUS['BAD_REQUEST']
                )
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return web.json_response(
                create_error_response(str(e)),
                status=HTTP_STATUS['BAD_REQUEST']
            )
    
    async def handle_get_room_history(self, request):
        """获取聊天室历史"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response(
                create_error_response(f'Room {room_id} not found'),
                status=HTTP_STATUS['NOT_FOUND']
            )
        
        try:
            limit = int(request.query.get('limit', 50))
            
            room = self.chat_rooms[room_id]
            history = room.get_message_history(limit)
            
            return web.json_response({
                'room_id': room_id,
                'history': history,
                'total_messages': len(room.message_history)
            })
        except Exception as e:
            logger.error(f"Error getting room history: {e}")
            return web.json_response(
                create_error_response(str(e)),
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
    
    async def handle_export_room_history(self, request):
        """导出聊天室历史"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response(
                create_error_response(f'Room {room_id} not found'),
                status=HTTP_STATUS['NOT_FOUND']
            )
        
        try:
            room = self.chat_rooms[room_id]
            history = room.get_message_history()
            
            # 生成导出内容
            export_content = f"# {room.config.room_name} 聊天记录\n\n"
            export_content += f"房间ID: {room_id}\n"
            export_content += f"创建时间: {room.config.room_name}\n"
            export_content += f"消息总数: {len(history)}\n\n"
            export_content += "---\n\n"
            
            for msg in history:
                timestamp = msg.get('timestamp', '')
                sender = msg.get('sender', 'Unknown')
                content = msg.get('content', '')
                export_content += f"**{sender}** ({timestamp})\n{content}\n\n"
            
            # 返回文本文件
            return web.Response(
                text=export_content,
                content_type='text/plain; charset=utf-8',
                headers={
                    'Content-Disposition': f'attachment; filename="room_{room_id}_history.txt"'
                }
            )
            
        except Exception as e:
            logger.error(f"Error exporting room history: {e}")
            return web.json_response(
                create_error_response(str(e)),
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
    
    async def handle_get_room_agents(self, request):
        """获取聊天室中的Agent信息"""
        room_id = request.match_info['room_id']
        
        if room_id not in self.chat_rooms:
            return web.json_response(
                create_error_response(f'Room {room_id} not found'),
                status=HTTP_STATUS['NOT_FOUND']
            )
        
        try:
            room = self.chat_rooms[room_id]
            agents_info = []
            
            # 获取房间中所有Agent的信息
            for agent_id, agent in room.agents.items():
                # 获取Agent元数据
                metadata = agent.get_metadata()
                
                agent_info = {
                    'id': agent_id,
                    'name': agent.name,
                    'role': metadata.get('role_description', '助手'),
                    'model': metadata.get('model_name', 'unknown'),
                    'platform': metadata.get('platform', 'unknown'),
                    'status': 'online',  # 默认为在线
                    'prompt': metadata.get('custom_prompt', '')
                }
                
                agents_info.append(agent_info)
            
            return web.json_response({
                'success': True,
                'room_id': room_id,
                'agents': agents_info
            })
            
        except Exception as e:
            logger.error(f"Error getting room agents: {e}")
            return web.json_response(
                create_error_response(str(e)),
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
