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


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    JOIN = "join"
    LEAVE = "leave"


class CommunicationMode(Enum):
    """通信模式"""
    BROADCAST = "broadcast"      # 广播模式：消息发送给所有人
    DIRECT = "direct"           # 直接模式：点对点通信
    NETWORK = "network"         # 网络模式：动态拓扑
    SEQUENTIAL = "sequential"   # 顺序模式：按顺序传递


@dataclass
class ChatMessage:
    """聊天消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: Optional[str] = None  # None表示广播
    content: str = ""
    message_type: MessageType = MessageType.TEXT
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


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
        self.message_history: List[ChatMessage] = []
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
    
    async def send_message(self, message: ChatMessage) -> None:
        """发送消息"""
        # 添加到消息历史
        self.message_history.append(message)
        
        # 限制历史记录大小
        if len(self.message_history) > self.config.message_history_limit:
            self.message_history = self.message_history[-self.config.message_history_limit:]
        
        # 根据通信模式处理消息
        if self.config.communication_mode == CommunicationMode.BROADCAST:
            await self._handle_broadcast(message)
        elif self.config.communication_mode == CommunicationMode.DIRECT:
            await self._handle_direct(message)
        elif self.config.communication_mode == CommunicationMode.NETWORK:
            await self._handle_network(message)
        elif self.config.communication_mode == CommunicationMode.SEQUENTIAL:
            await self._handle_sequential(message)
    
    async def _handle_broadcast(self, message: ChatMessage) -> None:
        """处理广播消息"""
        sender_id = message.sender_id
        
        # 发送给所有其他Agent
        for agent_id, agent in self.agents.items():
            if agent_id != sender_id:
                agent_message = AgentMessage(
                    sender_id=sender_id,
                    receiver_id=agent_id,
                    content=message.content,
                    message_type=message.message_type.value,
                    metadata=message.metadata
                )
                await agent.receive_message(agent_message)
    
    async def _handle_direct(self, message: ChatMessage) -> None:
        """处理直接消息"""
        if message.receiver_id and message.receiver_id in self.agents:
            receiver = self.agents[message.receiver_id]
            agent_message = AgentMessage(
                sender_id=message.sender_id,
                receiver_id=message.receiver_id,
                content=message.content,
                message_type=message.message_type.value,
                metadata=message.metadata
            )
            await receiver.receive_message(agent_message)
    
    async def _handle_network(self, message: ChatMessage) -> None:
        """处理网络模式消息"""
        sender_id = message.sender_id
        
        if message.receiver_id:
            # 如果指定了接收者，通过网络路由
            path = self.network_topology.get_shortest_path(sender_id, message.receiver_id)
            if path and len(path) > 1:
                # 发送给路径上的下一个节点
                next_hop = path[1]
                if next_hop in self.agents:
                    await self._forward_message(message, next_hop)
        else:
            # 广播给所有邻居
            neighbors = self.network_topology.get_neighbors(sender_id)
            for neighbor_id in neighbors:
                if neighbor_id in self.agents:
                    await self._forward_message(message, neighbor_id)
    
    async def _handle_sequential(self, message: ChatMessage) -> None:
        """处理顺序模式消息"""
        # 获取Agent列表并排序
        agent_ids = sorted(self.agents.keys())
        
        # 找到发送者的位置
        try:
            sender_index = agent_ids.index(message.sender_id)
            # 发送给下一个Agent
            next_index = (sender_index + 1) % len(agent_ids)
            next_agent_id = agent_ids[next_index]
            
            if next_agent_id in self.agents:
                await self._forward_message(message, next_agent_id)
        except ValueError:
            # 发送者不在列表中，可能是系统消息
            pass
    
    async def _forward_message(self, message: ChatMessage, target_id: str) -> None:
        """转发消息给指定Agent"""
        if target_id in self.agents:
            agent = self.agents[target_id]
            agent_message = AgentMessage(
                sender_id=message.sender_id,
                receiver_id=target_id,
                content=message.content,
                message_type=message.message_type.value,
                metadata=message.metadata
            )
            await agent.receive_message(agent_message)
    
    async def broadcast_message(self, message: ChatMessage) -> None:
        """广播消息给所有Agent"""
        original_mode = self.config.communication_mode
        self.config.communication_mode = CommunicationMode.BROADCAST
        await self.send_message(message)
        self.config.communication_mode = original_mode
    
    async def process_user_input(self, user_input: str, target_agent_id: Optional[str] = None) -> Dict[str, Any]:
        """处理用户输入并获取Agent响应"""
        user_message = ChatMessage(
            sender_id="user",
            receiver_id=target_agent_id,
            content=user_input,
            message_type=MessageType.TEXT,
            metadata={'source': 'user_input'}
        )
        
        # 添加到消息历史
        self.message_history.append(user_message)
        
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
        """获取消息历史"""
        recent_messages = self.message_history[-limit:]
        return [msg.to_dict() for msg in recent_messages]
    
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
