"""
ChatRoom - 聊天室管理
管理聊天室中的Agent通信和协作
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json

from .FlowTools.base_component import BaseComponent
from .Agentlib import Agent, AgentMessage, AgentRole
from .Communication.strategy_factory import CommunicationStrategyFactory
from .Communication.base_strategy import CommunicationContext, CommunicationResponse
from .Communication.message_types import ChatMessage, MessageType, CommunicationMode
from .Communication.discussion_types import EnhancedMessageHistory, DiscussionSession, DiscussionTurn, TurnType





@dataclass
class ChatRoomConfig:
    """聊天室配置"""
    room_id: str
    room_name: str
    description: str = ""
    max_agents: int = 10
    communication_mode: CommunicationMode = CommunicationMode.BROADCAST
    allow_dynamic_join: bool = True
    message_history_limit: int = 1000
    discussion_enabled: bool = False  # 是否启用多Agent讨论模式
    metadata: Dict[str, Any] = field(default_factory=dict)


class NetworkTopology:
    """网络拓扑管理"""
    
    def __init__(self):
        # 邻接表表示的网络拓扑
        self.connections: Dict[str, Set[str]] = {}
        self.connection_weights: Dict[tuple, float] = {}  # (from, to) -> weight
    
    def add_agent(self, agent_id: str) -> None:
        """添加Agent到网络"""
        if agent_id not in self.connections:
            self.connections[agent_id] = set()
    
    def remove_agent(self, agent_id: str) -> None:
        """从网络移除Agent"""
        if agent_id in self.connections:
            # 移除所有相关连接
            for other_id in list(self.connections[agent_id]):
                self.disconnect(agent_id, other_id)
            del self.connections[agent_id]
    
    def connect(self, agent1_id: str, agent2_id: str, weight: float = 1.0, bidirectional: bool = True) -> None:
        """连接两个Agent"""
        self.add_agent(agent1_id)
        self.add_agent(agent2_id)
        
        self.connections[agent1_id].add(agent2_id)
        self.connection_weights[(agent1_id, agent2_id)] = weight
        
        if bidirectional:
            self.connections[agent2_id].add(agent1_id)
            self.connection_weights[(agent2_id, agent1_id)] = weight
    
    def disconnect(self, agent1_id: str, agent2_id: str, bidirectional: bool = True) -> None:
        """断开两个Agent的连接"""
        if agent1_id in self.connections:
            self.connections[agent1_id].discard(agent2_id)
            self.connection_weights.pop((agent1_id, agent2_id), None)
        
        if bidirectional and agent2_id in self.connections:
            self.connections[agent2_id].discard(agent1_id)
            self.connection_weights.pop((agent2_id, agent1_id), None)
    
    def get_neighbors(self, agent_id: str) -> Set[str]:
        """获取Agent的邻居"""
        return self.connections.get(agent_id, set())
    
    def get_shortest_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """获取最短路径（简单BFS实现）"""
        if from_id not in self.connections or to_id not in self.connections:
            return None
        
        if from_id == to_id:
            return [from_id]
        
        visited = {from_id}
        queue = [(from_id, [from_id])]
        
        while queue:
            current, path = queue.pop(0)
            
            for neighbor in self.connections[current]:
                if neighbor == to_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None


class ChatRoom(BaseComponent):
    """聊天室 - 管理Agent之间的通信"""
    
    def __init__(self, config: ChatRoomConfig):
        super().__init__(config.room_id, "chatroom")
        
        self.config = config
        self.agents: Dict[str, Agent] = {}

        # 增强的消息历史管理
        self.enhanced_history = EnhancedMessageHistory()

        # 保持向后兼容的属性
        self.message_history = self.enhanced_history.linear_history

        self.network_topology = NetworkTopology()
        
        # 消息队列
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # 运行状态
        self.is_running = False
        self.message_handler_task: Optional[asyncio.Task] = None
        
        self.log_info(f"ChatRoom {config.room_name} created", {
            'room_id': config.room_id,
            'mode': config.communication_mode.value,
            'max_agents': config.max_agents
        })
    
    async def add_agent(self, agent: Agent) -> bool:
        """添加Agent到聊天室"""
        if len(self.agents) >= self.config.max_agents:
            self.log_warning(f"ChatRoom is full, cannot add agent {agent.name}")
            return False
        
        if agent.component_id in self.agents:
            self.log_warning(f"Agent {agent.name} already in chatroom")
            return False
        
        # 添加Agent
        self.agents[agent.component_id] = agent
        
        # 更新Agent的其他Agent引用
        for other_agent in self.agents.values():
            if other_agent.component_id != agent.component_id:
                agent.add_other_agent(other_agent)
                other_agent.add_other_agent(agent)
        
        # 在网络拓扑中添加
        self.network_topology.add_agent(agent.component_id)
        
        # 根据通信模式设置初始连接
        if self.config.communication_mode == CommunicationMode.NETWORK:
            # 默认连接到已存在的所有Agent（全连接）
            for other_id in self.agents:
                if other_id != agent.component_id:
                    self.network_topology.connect(agent.component_id, other_id)
        
        # 发送加入消息
        join_message = ChatMessage(
            sender_id="system",
            content=f"{agent.name} 加入了聊天室",
            message_type=MessageType.JOIN,
            metadata={'agent_info': agent.get_agent_info()}
        )
        
        await self.broadcast_message(join_message)
        
        self.log_info(f"Agent {agent.name} joined chatroom", {
            'agent_id': agent.component_id,
            'total_agents': len(self.agents)
        })
        
        return True
    
    async def remove_agent(self, agent_id: str) -> bool:
        """从聊天室移除Agent"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        
        # 发送离开消息
        leave_message = ChatMessage(
            sender_id="system",
            content=f"{agent.name} 离开了聊天室",
            message_type=MessageType.LEAVE,
            metadata={'agent_id': agent_id}
        )
        
        await self.broadcast_message(leave_message)
        
        # 从其他Agent的引用中移除
        for other_agent in self.agents.values():
            if agent_id in other_agent.other_agents:
                del other_agent.other_agents[agent_id]
        
        # 从网络拓扑中移除
        self.network_topology.remove_agent(agent_id)
        
        # 移除Agent
        del self.agents[agent_id]
        
        self.log_info(f"Agent {agent.name} left chatroom", {
            'agent_id': agent_id,
            'remaining_agents': len(self.agents)
        })
        
        return True
    
    async def send_message(self, message: ChatMessage, discussion_context: Optional[Dict[str, Any]] = None) -> None:
        """发送消息 - 支持讨论上下文"""
        # 使用增强的消息历史管理
        self.enhanced_history.add_message(message, discussion_context)

        # 限制线性历史记录大小（保持向后兼容）
        if len(self.message_history) > self.config.message_history_limit:
            # 移除最旧的消息
            removed_count = len(self.message_history) - self.config.message_history_limit
            self.message_history = self.message_history[removed_count:]
        
        # 使用通信策略处理消息
        await self._process_message_with_strategy(message)
    
    async def _process_message_with_strategy(self, message: ChatMessage) -> None:
        """使用通信策略处理消息"""
        try:
            # 获取通信策略
            strategy = CommunicationStrategyFactory.create_strategy(
                mode=self.config.communication_mode,
                discussion_enabled=self.config.discussion_enabled
            )

            # 设置日志记录器
            strategy.logger = self.logger

            # 构建通信上下文
            context = CommunicationContext(
                sender_id=message.sender_id,
                message=message,
                room_id=self.config.room_id,
                room_name=self.config.room_name,
                available_agents=self.agents,
                message_history=self.message_history,
                metadata=message.metadata or {}
            )

            # 执行通信策略
            response = await strategy.deliver_message(context)

            # 处理响应
            await self._handle_communication_response(response, strategy)

        except Exception as e:
            self.log_error(f"Error in communication strategy processing", e)

    async def _handle_communication_response(self, response: CommunicationResponse, strategy) -> None:
        """处理通信策略的响应"""
        if response.result.value == "success" or response.result.value == "partial_success":
            # 将Agent响应添加到消息历史
            for response_message in response.responses:
                self.message_history.append(response_message)

                # 限制历史记录大小
                if len(self.message_history) > self.config.message_history_limit:
                    self.message_history = self.message_history[-self.config.message_history_limit:]

            self.log_info(f"Communication strategy {strategy.strategy_name} completed successfully", {
                'delivered_to': response.delivered_to,
                'responses_count': len(response.responses),
                'metadata': response.metadata
            })
        else:
            self.log_warning(f"Communication strategy {strategy.strategy_name} failed", {
                'result': response.result.value,
                'failed_deliveries': response.failed_deliveries,
                'error': response.error_message
            })
    
    async def broadcast_message(self, message: ChatMessage) -> None:
        """广播消息给所有Agent"""
        original_mode = self.config.communication_mode
        self.config.communication_mode = CommunicationMode.BROADCAST
        await self.send_message(message)
        self.config.communication_mode = original_mode
    
    async def process_user_input(self, user_input: str, target_agent_id: Optional[str] = None) -> Dict[str, Any]:
        """处理用户输入 - 支持单Agent和多Agent讨论模式"""
        user_message = ChatMessage(
            sender_id="user",
            receiver_id=target_agent_id,
            content=user_input,
            message_type=MessageType.TEXT,
            metadata={'source': 'user_input'}
        )

        # 添加到消息历史
        self.message_history.append(user_message)

        # 检查是否启用多Agent讨论模式
        is_discussion_mode = (
            hasattr(self.config, 'discussion_enabled') and
            self.config.discussion_enabled and
            len(self.agents) > 1
        )

        if is_discussion_mode:
            # 多Agent讨论模式
            return await self._process_discussion_mode(user_input, user_message)
        else:
            # 传统单Agent模式
            return await self._process_single_agent_mode(user_input, user_message, target_agent_id)

    async def _process_single_agent_mode(self, user_input: str, user_message: ChatMessage, target_agent_id: Optional[str] = None) -> Dict[str, Any]:
        """处理单Agent模式的用户输入"""
        # 选择目标Agent
        target_agent = None
        if target_agent_id and target_agent_id in self.agents:
            target_agent = self.agents[target_agent_id]
        elif self.agents:
            # 如果没有指定目标，选择第一个Agent
            target_agent = list(self.agents.values())[0]

        if not target_agent:
            self.log_error("No agents available to process user input")
            return {
                'success': False,
                'error': 'No agents available',
                'response': '抱歉，当前没有可用的Agent来处理您的请求。'
            }

        try:
            # 调用Agent处理用户输入
            self.log_info(f"Processing user input with agent {target_agent.name}", {
                'user_input': user_input,
                'agent_id': target_agent.component_id
            })

            # 构建输入数据
            input_data = {
                'user_input': user_input,
                'room_context': {
                    'room_id': self.config.room_id,
                    'room_name': self.config.room_name,
                    'message_history': [msg.to_dict() for msg in self.message_history[-5:]]  # 最近5条消息
                }
            }

            # 调用Agent的think方法
            result = await target_agent.think(input_data)

            if result.get('success', True):
                response_content = result.get('response', '抱歉，我无法生成回复。')

                # 创建Agent响应消息
                agent_response = ChatMessage(
                    sender_id=target_agent.component_id,
                    receiver_id="user",
                    content=response_content,
                    message_type=MessageType.TEXT,
                    metadata={
                        'agent_name': target_agent.name,
                        'agent_role': target_agent.role.value,
                        'processing_time': result.get('processing_time', 0)
                    }
                )

                # 添加到消息历史
                self.message_history.append(agent_response)

                # 限制历史记录大小
                if len(self.message_history) > self.config.message_history_limit:
                    self.message_history = self.message_history[-self.config.message_history_limit:]

                self.log_info(f"Agent {target_agent.name} responded successfully", {
                    'response_length': len(response_content),
                    'total_messages': len(self.message_history)
                })

                return {
                    'success': True,
                    'response': response_content,
                    'agent_id': target_agent.component_id,
                    'agent_name': target_agent.name,
                    'message_id': agent_response.id,
                    'metadata': agent_response.metadata
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                self.log_error(f"Agent {target_agent.name} failed to process input: {error_msg}")

                return {
                    'success': False,
                    'error': error_msg,
                    'response': result.get('response', '抱歉，处理您的请求时出现了错误。'),
                    'agent_id': target_agent.component_id,
                    'agent_name': target_agent.name
                }

        except Exception as e:
            self.log_error(f"Error processing user input with agent {target_agent.name}", e)

            return {
                'success': False,
                'error': str(e),
                'response': f'抱歉，处理您的请求时出现了错误：{str(e)}',
                'agent_id': target_agent.component_id if target_agent else None,
                'agent_name': target_agent.name if target_agent else None
            }

    async def _process_discussion_mode(self, user_input: str, user_message: ChatMessage) -> Dict[str, Any]:
        """处理多Agent讨论模式的用户输入 - 使用通信策略和增强历史"""
        try:
            self.log_info("Starting multi-agent discussion mode with enhanced history", {
                'user_input': user_input,
                'agent_count': len(self.agents)
            })

            # 启动讨论会话（如果还没有活跃的讨论）
            if not self.enhanced_history.current_discussion:
                participants = list(self.agents.keys())
                discussion_session = self.enhanced_history.start_discussion(
                    room_id=self.config.room_id,
                    topic=user_input[:100],  # 使用用户输入的前100字符作为主题
                    participants=participants
                )
                self.log_info(f"Started new discussion session: {discussion_session.session_id}")

            # 使用讨论通信策略
            strategy = CommunicationStrategyFactory.create_strategy(
                mode=self.config.communication_mode,
                discussion_enabled=True
            )
            strategy.logger = self.logger

            # 构建通信上下文
            context = CommunicationContext(
                sender_id="user",
                message=user_message,
                room_id=self.config.room_id,
                room_name=self.config.room_name,
                available_agents=self.agents,
                message_history=self.message_history,
                metadata={'discussion_mode': True}
            )

            # 执行讨论策略
            response = await strategy.deliver_message(context)

            if response.result.value == "success":
                # 处理成功的讨论响应
                if response.responses:
                    first_response = response.responses[0]

                    # 构建讨论上下文
                    discussion_context = {
                        'agent_name': first_response.metadata.get('agent_name', 'Agent'),
                        'turn_type': 'initial',  # 第一轮发言
                        'discussion_mode': True,
                        'discussion_status': response.metadata.get('discussion_status', 'started'),
                        'svr_values': first_response.metadata.get('svr_values', {}),
                        'content_analysis': {
                            'content_length': len(first_response.content),
                            'response_to_user': True
                        }
                    }

                    # 使用增强的消息历史添加
                    await self.send_message(first_response, discussion_context)

                    return {
                        'success': True,
                        'response': first_response.content,
                        'agent_name': first_response.metadata.get('agent_name', 'Agent'),
                        'agent_id': first_response.sender_id,
                        'message_id': first_response.id,
                        'metadata': first_response.metadata,
                        'discussion_mode': True,
                        'discussion_status': response.metadata.get('discussion_status', 'started'),
                        'discussion_session_id': self.enhanced_history.current_discussion.session_id if self.enhanced_history.current_discussion else None,
                        # 传递用户输入和房间上下文给WebSocket处理器
                        'user_input': user_input,
                        'room_context': response.metadata.get('room_context', {}),
                        'trigger_continuous_discussion': response.metadata.get('trigger_continuous_discussion', False)
                    }
                else:
                    return {
                        'success': False,
                        'error': '讨论策略未返回响应',
                        'response': '抱歉，无法启动多Agent讨论。'
                    }
            else:
                return {
                    'success': False,
                    'error': response.error_message or '讨论启动失败',
                    'response': '抱歉，无法启动多Agent讨论。'
                }

        except Exception as e:
            self.log_error(f"Error in discussion mode with communication strategy", e)
            return {
                'success': False,
                'error': str(e),
                'response': f'讨论模式处理错误: {str(e)}'
            }
    
    def update_network_topology(self, connections: List[tuple]) -> None:
        """更新网络拓扑"""
        # 清空现有连接
        self.network_topology = NetworkTopology()
        
        # 添加所有Agent
        for agent_id in self.agents:
            self.network_topology.add_agent(agent_id)
        
        # 添加连接
        for connection in connections:
            if len(connection) >= 2:
                agent1_id, agent2_id = connection[0], connection[1]
                weight = connection[2] if len(connection) > 2 else 1.0
                self.network_topology.connect(agent1_id, agent2_id, weight)
    
    def get_message_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取消息历史（向后兼容）"""
        recent_messages = self.enhanced_history.get_linear_history(limit)
        return [msg.to_dict() for msg in recent_messages]

    def get_discussion_history(self) -> Optional[Dict[str, Any]]:
        """获取当前讨论历史"""
        discussion = self.enhanced_history.get_discussion_history()
        return discussion.to_dict() if discussion else None

    def get_discussion_context_for_svr(self, agent_id: str) -> Dict[str, Any]:
        """获取SVR算法所需的讨论上下文"""
        return self.enhanced_history.get_svr_context(agent_id)

    def end_current_discussion(self) -> Optional[Dict[str, Any]]:
        """结束当前讨论会话"""
        ended_session = self.enhanced_history.end_discussion()
        if ended_session:
            self.log_info(f"Discussion session ended: {ended_session.session_id}", {
                'total_rounds': ended_session.total_rounds,
                'total_turns': ended_session.total_turns,
                'duration': ended_session.get_duration(),
                'participants': ended_session.all_participants
            })
            return ended_session.to_dict()
        return None

    def is_discussion_active(self) -> bool:
        """检查是否有活跃的讨论"""
        return (self.enhanced_history.current_discussion is not None and
                self.enhanced_history.current_discussion.is_active)
    
    def get_room_status(self) -> Dict[str, Any]:
        """获取聊天室状态"""
        return {
            'room_id': self.config.room_id,
            'room_name': self.config.room_name,
            'description': self.config.description,
            'communication_mode': self.config.communication_mode.value,
            'agents': {
                agent_id: {
                    'name': agent.name,
                    'role': agent.role.value,
                    'status': agent.status.value
                }
                for agent_id, agent in self.agents.items()
            },
            'agent_count': len(self.agents),
            'message_count': len(self.message_history),
            'network_connections': len(self.network_topology.connection_weights) if self.config.communication_mode == CommunicationMode.NETWORK else None
        }
    
    async def start(self) -> None:
        """启动聊天室"""
        if self.is_running:
            return
        
        self.is_running = True
        self.message_handler_task = asyncio.create_task(self._message_handler())
        
        self.log_info(f"ChatRoom {self.config.room_name} started")
    
    async def stop(self) -> None:
        """停止聊天室"""
        self.is_running = False
        
        if self.message_handler_task:
            self.message_handler_task.cancel()
            try:
                await self.message_handler_task
            except asyncio.CancelledError:
                pass
        
        self.log_info(f"ChatRoom {self.config.room_name} stopped")
    
    async def _message_handler(self) -> None:
        """消息处理循环"""
        while self.is_running:
            try:
                # 处理消息队列中的消息
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self.send_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.log_error("Error in message handler", e)
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')
            
            if action == 'get_status':
                return self.get_room_status()
            elif action == 'get_history':
                limit = input_data.get('limit', 50)
                return self.get_message_history(limit)
            else:
                return {'error': f'Unknown action: {action}'}
        
        return {'error': 'Invalid input'}
