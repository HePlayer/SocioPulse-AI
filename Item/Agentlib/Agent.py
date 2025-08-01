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

        # 重要状态变化使用INFO级别，确保可见
        if new_status == AgentStatus.THINKING:
            self.log_info(f"🔄 Agent {self.name} 状态: {old_status.value} -> {new_status.value}")
        elif new_status == AgentStatus.ERROR:
            self.log_error(f"🚨 Agent {self.name} 状态: {old_status.value} -> {new_status.value}")
        else:
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
        # 记录思考开始 - 使用INFO级别确保可见
        user_input = input_data.get('user_input', '')
        room_context = input_data.get('room_context', {})
        is_discussion_mode = room_context.get('discussion_mode', False)

        self.log_info(f"🧠 Agent {self.name} 开始思考")
        self.log_info(f"  输入内容: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")
        self.log_info(f"  讨论模式: {is_discussion_mode}")

        self._change_status(AgentStatus.THINKING)

        try:
            # 1. 获取用户输入
            self.log_debug(f"Processing user input: {len(user_input)} characters")

            # 2. 简化的上下文构建 - 保留接口但简化实现
            context = None
            try:
                if self.context_manager:
                    # 设置用户输入到上下文管理器
                    self.context_manager.set_user_input(user_input)
                    # 构建简化的上下文
                    context = self.context_manager.build_structured_context(user_input)
                    self.log_debug("Context building successful")
            except Exception as ctx_error:
                self.log_warning(f"Context building failed, using simple context: {ctx_error}")
                # 如果上下文构建失败，使用简单的上下文
                context = None
            
            # 3. 检查是否为讨论模式并构建相应的提示词
            self.log_info(f"  构建提示词...")

            if is_discussion_mode:
                prompt = self._build_discussion_prompt(user_input, room_context)
                self.log_debug(f"Discussion prompt built, length: {len(prompt)}")
            else:
                # 传统模式的提示词构建
                prompt = user_input
                if self.prompt_manager:
                    try:
                        system_prompt = self.prompt_manager.get_system_prompt()
                        if system_prompt:
                            prompt = f"系统提示: {system_prompt}\n\n用户输入: {user_input}"
                    except Exception as prompt_error:
                        self.log_warning(f"Prompt building failed, using simple prompt: {prompt_error}")

            # 4. 调用模型
            self.log_info(f"  🤖 调用模型进行推理...")

            if self.model:
                # 添加重试机制和详细日志
                max_retries = 3
                retry_delay = 1.0

                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            self.log_info(f"  重试模型调用 (第{attempt + 1}次尝试)")
                            await asyncio.sleep(retry_delay * attempt)  # 递增延迟

                        response = await self.model.generate(prompt, context)

                        # 成功调用的日志
                        self.log_info(f"  ✅ 模型调用成功，响应长度: {len(response)} 字符")
                        break

                    except Exception as model_error:
                        error_msg = str(model_error)
                        self.log_error(f"  ❌ 模型调用失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")

                        if attempt == max_retries - 1:
                            # 最后一次尝试失败
                            self.log_error(f"  🚫 所有重试均失败，使用错误响应")
                            response = f"[{self.name}] 抱歉，我在处理您的请求时遇到了模型调用错误。请检查API配置。错误信息: {error_msg}"
                        else:
                            continue
            else:
                # 记录模型未配置的详细信息
                self.log_error(f"  🚫 Agent '{self.name}' 没有配置模型。请检查API密钥配置。")

                if is_discussion_mode:
                    response = f"[{self.name}] ⚠️ 模型连接失败：我没有配置有效的语言模型。请检查API密钥配置。作为临时措施，我可以提供一些基础观点供讨论。"
                else:
                    response = f"[{self.name}] ⚠️ 模型连接失败：没有配置有效的语言模型。\n\n收到输入: {user_input}\n\n请检查以下配置：\n1. API密钥是否正确配置\n2. 平台名称是否匹配\n3. 网络连接是否正常"
            
            # 5. 解析响应
            self.log_info(f"  📝 解析模型响应...")
            result = self._parse_response(response)

            # 6. 更新对话历史
            self.log_debug(f"Updating conversation history")
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

            # 7. 尝试更新上下文管理器（如果可用）
            try:
                if self.context_manager:
                    self.context_manager.add_conversation_turn(user_input, response)
                    self.log_debug("Context manager updated successfully")
            except Exception as ctx_update_error:
                self.log_warning(f"Context update failed: {ctx_update_error}")

            # 记录思考完成
            self.log_info(f"✅ Agent {self.name} 思考完成")
            self.log_info(f"  响应成功: {result.get('success', False)}")
            self.log_info(f"  响应预览: {response[:100]}{'...' if len(response) > 100 else ''}")

            return result
            
        except Exception as e:
            self._change_status(AgentStatus.ERROR)
            self.log_error(f"❌ Agent {self.name} 思考过程发生严重错误", e)
            self.log_error(f"  错误类型: {type(e).__name__}")
            self.log_error(f"  错误详情: {str(e)}")

            error_response = f"抱歉，我在处理您的请求时遇到了错误: {str(e)}"

            return {
                'success': False,
                'error': str(e),
                'response': error_response
            }
        finally:
            if self.status != AgentStatus.ERROR:
                self._change_status(AgentStatus.IDLE)
                self.log_info(f"🔄 Agent {self.name} 状态重置为空闲")
    
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
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取Agent元数据 - 标准接口方法"""
        base_metadata = {
            'name': self.name,
            'role': self.role.value,
            'status': self.status.value,
            'description': self.metadata.description,
            'capabilities': self.metadata.capabilities.copy(),
            'constraints': self.metadata.constraints.copy()
        }
        
        # 合并自定义属性
        base_metadata.update(self.metadata.custom_attributes)
        
        return base_metadata
    
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
    
    def _build_discussion_prompt(self, user_input: str, room_context: Dict[str, Any]) -> str:
        """构建多Agent讨论模式的提示词"""
        available_agents = room_context.get('available_agents', [])
        message_history = room_context.get('message_history', [])

        # 获取基础系统提示词
        base_prompt = ""
        if self.prompt_manager:
            try:
                base_prompt = self.prompt_manager.get_system_prompt() or ""
            except Exception:
                pass

        # 构建讨论上下文
        discussion_context = []
        if message_history:
            discussion_context.append("=== 对话历史 ===")
            for msg in message_history[-3:]:  # 最近3条消息
                sender = msg.get('sender_id', 'unknown')
                content = msg.get('content', '')
                discussion_context.append(f"{sender}: {content}")

        # 构建讨论提示词
        prompt_parts = []

        if base_prompt:
            prompt_parts.append(f"系统提示: {base_prompt}")

        prompt_parts.append(f"""
多Agent讨论模式：
- 当前参与讨论的Agent: {', '.join(available_agents)}
- 你的名字是: {self.name}
- 这是一个多Agent讨论，你需要：
  1. 基于用户问题和其他Agent的观点提供你的见解
  2. 可以同意、补充或礼貌地反驳其他Agent的观点
  3. 保持讨论的建设性和专业性
  4. 如果你认为问题已经得到充分讨论，可以总结观点
""")

        if discussion_context:
            prompt_parts.extend(discussion_context)

        prompt_parts.append(f"\n用户问题: {user_input}")
        prompt_parts.append(f"\n请以{self.name}的身份参与讨论:")

        return "\n".join(prompt_parts)

    def __repr__(self) -> str:
        return f"Agent(id={self.component_id}, name={self.name}, role={self.role.value}, status={self.status.value})"
