"""
Agent - Agent基类
定义所有Agent的通用行为和接口
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..FlowTools.flow_node import FlowNode, NodeType, NodeResult
from ..ContextEngineer.context_manager import ContextManager, StructuredContext
from .Models import ModelBase
from .Prompt import PromptManager


class AgentRole(Enum):
    """Agent角色枚举"""
    CHAT = "chat"                    # 聊天Agent
    TOOLS = "tools"                  # 工具调用Agent
    COORDINATOR = "coordinator"      # 协调Agent
    SPECIALIST = "specialist"        # 专家Agent（数学家、历史学家等）
    CUSTOM = "custom"                # 自定义Agent


class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"                    # 空闲
    THINKING = "thinking"            # 思考中
    EXECUTING = "executing"          # 执行中
    WAITING = "waiting"              # 等待中
    ERROR = "error"                  # 错误状态
    TERMINATED = "terminated"        # 已终止


@dataclass
class AgentMetadata:
    """Agent元数据"""
    name: str
    role: AgentRole
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Agent消息"""
    sender_id: str
    receiver_id: str
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Agent(FlowNode):
    """Agent基类 - 所有Agent的父类"""
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 role: AgentRole = AgentRole.CHAT,
                 model: Optional[ModelBase] = None,
                 context_manager: Optional[ContextManager] = None,
                 prompt_manager: Optional[PromptManager] = None):
        """
        初始化Agent
        
        Args:
            agent_id: Agent唯一标识
            name: Agent名称
            role: Agent角色
            model: 使用的模型实例
            context_manager: 上下文管理器
            prompt_manager: 提示词管理器
        """
        super().__init__(agent_id, NodeType.CUSTOM)
        
        # Agent基本信息
        self.name = name
        self.role = role
        self.status = AgentStatus.IDLE
        
        # Agent元数据
        self.metadata = AgentMetadata(
            name=name,
            role=role,
            description=f"{role.value} agent: {name}"
        )
        
        # 核心组件
        self.model = model
        self.context_manager = context_manager or ContextManager(f"{agent_id}_context")
        self.prompt_manager = prompt_manager or PromptManager(f"{agent_id}_prompt")
        
        # 消息队列
        self.message_queue: List[AgentMessage] = []
        self.conversation_history: List[Dict[str, Any]] = []
        
        # 工具注册
        self.available_tools: Dict[str, Callable] = {}
        
        # 其他Agent的引用（用于群聊）
        self.other_agents: Dict[str, 'Agent'] = {}
        
        # 回调函数
        self.on_message_received: Optional[Callable] = None
        self.on_status_changed: Optional[Callable] = None
        
        self.log_debug(f"Agent {name} initialized", {
            'agent_id': agent_id,
            'role': role.value,
            'model': type(model).__name__ if model else 'None'
        })
    
    def set_metadata(self, **kwargs) -> None:
        """设置Agent元数据"""
        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                setattr(self.metadata, key, value)
            else:
                self.metadata.custom_attributes[key] = value
    
    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        if self.prompt_manager:
            self.prompt_manager.set_system_prompt(prompt)
        # 同时更新元数据
        self.set_metadata(system_prompt=prompt)
        
        self.log_debug(f"System prompt set for agent {self.name}", {
            'prompt_length': len(prompt),
            'agent_role': self.role.value
        })
    
    def register_tool(self, tool_name: str, tool_func: Callable, description: str = "") -> None:
        """注册工具"""
        self.available_tools[tool_name] = tool_func
        self.metadata.capabilities.append(f"tool:{tool_name}")
        
        self.log_debug(f"Registered tool: {tool_name}", {
            'description': description,
            'total_tools': len(self.available_tools)
        })
    
    def add_other_agent(self, agent: 'Agent') -> None:
        """添加其他Agent的引用（用于群聊）"""
        self.other_agents[agent.component_id] = agent
        self.log_debug(f"Added reference to agent: {agent.name}")
    
    async def receive_message(self, message: AgentMessage) -> None:
        """接收消息"""
        self.message_queue.append(message)
        
        self.log_debug(f"Received message from {message.sender_id}", {
            'message_type': message.message_type,
            'content_length': len(message.content)
        })
        
        # 触发回调
        if self.on_message_received:
            await self.on_message_received(message)
    
    async def send_message(self, receiver_id: str, content: str, message_type: str = "text", metadata: Dict[str, Any] = None) -> None:
        """发送消息给其他Agent"""
        message = AgentMessage(
            sender_id=self.component_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        
        # 如果接收者在已知的Agent中，直接发送
        if receiver_id in self.other_agents:
            receiver = self.other_agents[receiver_id]
            await receiver.receive_message(message)
        else:
            # 否则，将消息放入输出中，由外部系统处理
            self.log_warning(f"Unknown receiver: {receiver_id}, message queued for external handling")
        
        # 记录到对话历史
        self.conversation_history.append({
            'role': 'assistant',
            'content': content,
            'receiver': receiver_id,
            'timestamp': message.timestamp
        })
    
    def _change_status(self, new_status: AgentStatus) -> None:
        """改变Agent状态"""
        old_status = self.status
        self.status = new_status
        
        self.log_debug(f"Status changed: {old_status.value} -> {new_status.value}")
        
        # 触发回调
        if self.on_status_changed:
            self.on_status_changed(old_status, new_status)
    
    async def think(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent思考过程
        
        Args:
            input_data: 输入数据，包含用户输入、上下文等
            
        Returns:
            思考结果，包含响应内容、需要调用的工具等
        """
        self._change_status(AgentStatus.THINKING)
        
        try:
            # 1. 构建上下文
            user_input = input_data.get('user_input', '')
            context = self.context_manager.build_structured_context(user_input)
            
            # 2. 获取适当的提示词
            prompt = self.prompt_manager.get_prompt(
                self.role.value,
                context=context,
                agent_metadata=self.metadata
            )
            
            # 3. 调用模型
            if self.model:
                response = await self.model.generate(prompt, context)
            else:
                response = f"[{self.name}] 收到输入: {user_input}"
            
            # 4. 解析响应
            result = self._parse_response(response)
            
            # 5. 更新对话历史
            self.conversation_history.append({
                'role': 'user',
                'content': user_input,
                'timestamp': time.time()
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response,
                'timestamp': time.time()
            })
            
            return result
            
        except Exception as e:
            self._change_status(AgentStatus.ERROR)
            self.log_error(f"Error during thinking", e)
            return {
                'success': False,
                'error': str(e),
                'response': f"抱歉，我在处理您的请求时遇到了错误: {str(e)}"
            }
        finally:
            if self.status != AgentStatus.ERROR:
                self._change_status(AgentStatus.IDLE)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析模型响应
        
        Args:
            response: 模型的原始响应
            
        Returns:
            解析后的结果，包含响应文本、工具调用等
        """
        # 基础实现，子类可以覆盖以实现更复杂的解析
        result = {
            'success': True,
            'response': response,
            'tool_calls': [],
            'metadata': {}
        }
        
        # 简单的工具调用检测
        if "调用工具" in response or "使用工具" in response:
            # 这里可以实现更复杂的工具调用解析逻辑
            pass
        
        return result
    
    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """执行工具"""
        self._change_status(AgentStatus.EXECUTING)
        
        try:
            if tool_name not in self.available_tools:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            tool_func = self.available_tools[tool_name]
            result = await tool_func(**tool_args) if asyncio.iscoroutinefunction(tool_func) else tool_func(**tool_args)
            
            # 将工具结果添加到上下文
            self.context_manager.add_tool_result(tool_name, result)
            
            return result
            
        except Exception as e:
            self._change_status(AgentStatus.ERROR)
            self.log_error(f"Error executing tool {tool_name}", e)
            raise
        finally:
            if self.status != AgentStatus.ERROR:
                self._change_status(AgentStatus.IDLE)
    
    def _execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        FlowNode执行核心方法
        
        Args:
            input_data: 输入数据
            
        Returns:
            执行结果
        """
        # 同步包装异步think方法
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.think(input_data))
            return result
        finally:
            loop.close()
    
    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        if not self.conversation_history:
            return "暂无对话历史"
        
        summary_lines = [f"Agent: {self.name} ({self.role.value})"]
        summary_lines.append(f"对话轮数: {len(self.conversation_history) // 2}")
        
        # 获取最近的几轮对话
        recent_turns = self.conversation_history[-6:]  # 最近3轮
        for entry in recent_turns:
            role = "用户" if entry['role'] == 'user' else self.name
            content_preview = entry['content'][:50] + "..." if len(entry['content']) > 50 else entry['content']
            summary_lines.append(f"{role}: {content_preview}")
        
        return "\n".join(summary_lines)
    
    def reset(self) -> None:
        """重置Agent状态"""
        self.status = AgentStatus.IDLE
        self.message_queue.clear()
        self.conversation_history.clear()
        self.context_manager.clear_session_data()
        
        self.log_info(f"Agent {self.name} reset")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            'id': self.component_id,
            'name': self.name,
            'role': self.role.value,
            'status': self.status.value,
            'metadata': {
                'description': self.metadata.description,
                'capabilities': self.metadata.capabilities,
                'constraints': self.metadata.constraints,
                'custom_attributes': self.metadata.custom_attributes
            },
            'tools': list(self.available_tools.keys()),
            'conversation_turns': len(self.conversation_history) // 2,
            'connected_agents': list(self.other_agents.keys())
        }
    
    def __repr__(self) -> str:
        return f"Agent(id={self.component_id}, name={self.name}, role={self.role.value}, status={self.status.value})"
