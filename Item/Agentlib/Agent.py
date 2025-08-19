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
from .Prompt import PromptManager, PromptAssembler


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

    async def set_system_prompt_with_costar_priority(self, prompt: str) -> str:
        """设置系统提示词并确保COSTAR优先（异步优化版本）"""

        # 1. 立即设置原始prompt（确保Agent可用）
        self.set_system_prompt(prompt)

        # 2. 检查是否需要COSTAR优化
        if not self._is_costar_format(prompt):
            try:
                # 3. 尝试异步优化为COSTAR格式
                if self.prompt_manager:
                    costar_template = self.prompt_manager.get_template("prompt_optimizer_costar")
                    if costar_template:
                        optimization_prompt = costar_template.format(
                            original_prompt=prompt,
                            agent_name=self.name
                        )

                        # 使用模型优化（如果有配置）
                        if self.model:
                            optimized_prompt = await self.model.generate(optimization_prompt)

                            # 提取优化后的内容
                            if "===" in optimized_prompt:
                                costar_content = self._extract_costar_content(optimized_prompt)
                                if costar_content and len(costar_content) > len(prompt) * 0.8:
                                    self.set_system_prompt(costar_content)
                                    self.log_info(f"Agent {self.name} prompt optimized to COSTAR format")
                                    return "costar_optimized"

                self.log_info(f"Agent {self.name} using original prompt (COSTAR optimization not available)")
                return "original_format"

            except Exception as e:
                self.log_warning(f"COSTAR optimization failed, using original prompt: {e}")
                return "optimization_failed"
        else:
            self.log_info(f"Agent {self.name} prompt already in COSTAR format")
            return "already_costar"
    
    def register_tool(self, tool_name: str, tool_func: Callable, description: str = "") -> None:
        """注册工具"""
        self.available_tools[tool_name] = tool_func
        self.metadata.capabilities.append(f"tool:{tool_name}")
        
        self.log_debug(f"Registered tool: {tool_name}", {
            'description': description,
            'total_tools': len(self.available_tools)
        })
    
    def add_other_agent(self, agent: 'Agent') -> None:
        """🚀 优化：保持接口兼容性，但不再存储引用（对话内容通过上下文系统展示）"""
        # 不再实际存储引用，减少内存使用和维护复杂度
        pass

    def _is_costar_format(self, prompt: str) -> bool:
        """检测提示词是否已经是COSTAR格式"""
        if not prompt:
            return False

        costar_elements = ["Context", "Objective", "Style", "Tone", "Audience", "Response"]
        found_elements = sum(1 for element in costar_elements if element in prompt)

        # 如果包含4个或以上COSTAR元素，认为是COSTAR格式
        return found_elements >= 4

    def _is_debate_scenario(self, user_input: str, discussion_topic: str = "") -> bool:
        """检测是否为辩论场景"""
        if not user_input and not discussion_topic:
            return False

        debate_indicators = [
            "辩论", "争论", "对比", "相反", "反对", "支持vs反对",
            "正方vs反方", "赞成vs反对", "不同观点", "立场", "辩护",
            "反驳", "质疑", "挑战", "批评", "驳斥", "我认为", "你怎么看",
            "应该", "不应该", "放慢", "加快", "支持", "不支持",
            "同意", "不同意", "赞成", "反对", "观点", "看法", "vs",
            "对比", "比较", "哪个更", "更重要", "优劣", "利弊",
            "但我", "然而", "不过", "可是", "但是"
        ]

        content_to_check = f"{user_input} {discussion_topic}".lower()
        return any(indicator in content_to_check for indicator in debate_indicators)

    def _extract_costar_content(self, optimized_prompt: str) -> str:
        """从优化结果中提取COSTAR格式的内容"""
        try:
            # 寻找COSTAR格式的开始标记
            if "===" in optimized_prompt and "Context" in optimized_prompt:
                # 提取从第一个===开始的内容
                lines = optimized_prompt.split('\n')
                start_idx = -1

                for i, line in enumerate(lines):
                    if "===" in line and any(element in line for element in ["Context", "Agent", "身份"]):
                        start_idx = i
                        break

                if start_idx >= 0:
                    return '\n'.join(lines[start_idx:]).strip()

            return optimized_prompt.strip()

        except Exception as e:
            self.log_warning(f"Failed to extract COSTAR content: {e}")
            return optimized_prompt
    
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
        
        # 🚀 优化：消息通过ChatRoom的通信策略处理，不再使用直接引用
        self.log_info(f"Message to {receiver_id} will be handled by ChatRoom communication strategy")
        
        # 记录到对话历史（包含发言者信息）
        self.conversation_history.append({
            'role': 'assistant',
            'content': content,
            'sender_id': self.component_id,
            'sender_name': self.name,
            'receiver_id': receiver_id,
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
    
    async def think(self, input_data: Dict[str, Any], shared_context_manager=None, connection_pool=None) -> Dict[str, Any]:
        """
        Agent思考过程 - 支持共享上下文和连接池的优化版本

        Args:
            input_data: 输入数据，包含用户输入、上下文等
            shared_context_manager: 共享的上下文管理器（房间级别）
            connection_pool: 连接池实例

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
        self.log_info(f"  房间上下文: room_name='{room_context.get('room_name', '')}', description='{room_context.get('description', '')}'")

        self._change_status(AgentStatus.THINKING)

        try:
            # 1. 获取用户输入
            self.log_debug(f"Processing user input: {len(user_input)} characters")

            # 🚀 2. 使用共享上下文管理器（优先）或自己的上下文管理器
            context_manager = shared_context_manager or self.context_manager
            context = None

            try:
                if context_manager:
                    # 设置用户输入到上下文管理器
                    context_manager.set_user_input(user_input)
                    # 构建结构化上下文
                    context = context_manager.build_structured_context(user_input)

                    # 使用 PromptAssembler 统一组装本轮提示
                    try:
                        assembler = PromptAssembler(logger=self)
                        base_system_prompt = ""
                        if self.prompt_manager:
                            try:
                                base_system_prompt = self.prompt_manager.get_system_prompt() or ""
                            except Exception:
                                base_system_prompt = ""
                        assembled = assembler.assemble(context, room_context, base_system_prompt=base_system_prompt)

                        # 注入 developer_instructions（作为 system 优先级内容）
                        if context is not None:
                            if not hasattr(context, 'developer_instructions') or context.developer_instructions is None:
                                context.developer_instructions = []
                            # 将 system_block 放在最前
                            if assembled.get('system_block'):
                                context.developer_instructions.insert(0, assembled['system_block'])

                            # 替换 user_input 为标准化后的文本（首行含【聊天室：...】）
                            if assembled.get('user_text'):
                                context.user_input = assembled['user_text']
                    except Exception:
                        # 组装失败不影响主流程，保留原有上下文
                        pass

                    self.log_debug("Shared context building successful")
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
                # 传统模式的提示词构建（房间约束绝对优先）
                prompt = user_input
                if self.prompt_manager:
                    try:
                        room_name = room_context.get('room_name', '')
                        room_desc = room_context.get('description', '')
                        room_tag = f"【聊天室：{room_name}】" if room_name else ""

                        # 🚀 关键修改：房间约束直接作为最高优先级前缀
                        if room_name and room_name.strip():
                            room_constraint = f"""【聊天室主题约束 - 绝对最高优先级】
当前聊天室：{room_name}
聊天室背景：{room_desc}

核心要求（必须严格执行，覆盖所有其他指令）：
- 你必须严格按照聊天室主题来回答问题
- 即使你有其他身份设定，也要专门针对"{room_name}"这个主题领域
- 所有回答、示例、建议都必须与该主题高度相关
- 如果用户问题模糊，请主动从该主题角度解读并回答
- 绝对禁止偏离到其他无关领域

特别指令（最高优先级）：
- 当用户问"最近有什么消息/新闻/动态"等泛化问题时，必须主动从"{room_name}"主题角度回答
- 不要反问用户对哪方面感兴趣，直接提供该主题领域的相关信息
- 例如：在"足球球迷群"中，应直接回答足球相关的最新消息、赛事、转会等

"""
                            # 获取原始系统提示词（不带房间约束的）
                            original_system_prompt = self.prompt_manager.templates.get("system")
                            if original_system_prompt and hasattr(original_system_prompt, 'template'):
                                original_prompt = original_system_prompt.template
                            else:
                                original_prompt = ""

                            # 构建最终提示词：房间标签 + 房间约束 + 原始提示词 + 用户输入
                            if original_prompt:
                                prompt = f"{room_tag}\n{room_constraint}\n=== 以下是你的原始身份设定 ===\n{original_prompt}\n\n注意：以上原始身份设定必须服从聊天室主题约束！\n\n用户输入: {user_input}"
                            else:
                                prompt = f"{room_tag}\n{room_constraint}\n用户输入: {user_input}"
                        else:
                            # 没有房间名称时，使用普通系统提示词
                            system_prompt = self.prompt_manager.get_system_prompt()
                            if system_prompt:
                                prompt = f"{room_tag}\n系统提示: {system_prompt}\n\n用户输入: {user_input}"

                        # 同时在开发者指令中强化房间约束
                        if context and room_name:
                            try:
                                if not hasattr(context, 'developer_instructions') or context.developer_instructions is None:
                                    context.developer_instructions = []
                                context.developer_instructions.insert(0, room_constraint)
                            except Exception:
                                pass
                    except Exception as prompt_error:
                        self.log_warning(f"Prompt building failed, using simple prompt: {prompt_error}")

            # 🚀 4. 按需创建模型并调用（支持连接池和联网功能）
            self.log_info(f"  🤖 调用模型进行推理...")

            # 🚀 延迟初始化模型（如果还没有）
            if not self.model and hasattr(self, '_model_config'):
                await self._create_model_on_demand(connection_pool)

            if self.model:
                # 🌐 智谱AI模型默认启用联网功能，无需额外配置
                model_kwargs = {}
                self.log_info(f"  📡 联网功能已在模型层面默认启用")

                # 添加重试机制和详细日志
                max_retries = 3
                retry_delay = 1.0

                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            self.log_info(f"  重试模型调用 (第{attempt + 1}次尝试)")
                            await asyncio.sleep(retry_delay * attempt)  # 递增延迟

                        # 🌐 使用联网参数调用模型
                        response = await self.model.generate(prompt, context, **model_kwargs)

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

            # 6. 更新对话历史（包含发言者信息）
            self.log_debug(f"Updating conversation history with speaker information")

            # 记录用户输入（带发言者信息）
            self.conversation_history.append({
                'role': 'user',
                'content': user_input,
                'sender_id': 'user',
                'sender_name': '用户',
                'timestamp': time.time()
            })

            # 记录Agent响应（带发言者信息，确保内容使用"我"自称）
            self.conversation_history.append({
                'role': 'assistant',
                'content': response,
                'sender_id': self.component_id,
                'sender_name': self.name,
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
        
        # 获取最近的几轮对话（使用发言者信息）
        recent_turns = self.conversation_history[-6:]  # 最近3轮
        for entry in recent_turns:
            # 优先使用sender_name，回退到role
            sender_name = entry.get('sender_name')
            if not sender_name:
                sender_name = "用户" if entry['role'] == 'user' else self.name

            content_preview = entry['content'][:50] + "..." if len(entry['content']) > 50 else entry['content']
            summary_lines.append(f"[{sender_name}]：{content_preview}")
        
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
            'connected_agents': []  # 🚀 优化：不再显示连接关系，Agent信息通过房间API获取
        }
    
    def _build_discussion_prompt(self, user_input: str, room_context: Dict[str, Any]) -> str:
        """构建多Agent讨论模式的提示词 - 增强约束版本"""
        available_agents = room_context.get('available_agents', [])
        message_history = room_context.get('message_history', [])

        # 🚀 新增：获取讨论主题
        discussion_topic = room_context.get('topic', user_input[:50] + "..." if len(user_input) > 50 else user_input)

        # 🚀 新增：获取房间名称（用于上下文）
        room_name = room_context.get('room_name', '未知聊天室')
        room_desc = room_context.get('description', '')

        # 获取基础系统提示词
        base_prompt = ""
        if self.prompt_manager:
            try:
                base_prompt = self.prompt_manager.get_system_prompt() or ""
            except Exception:
                pass

        # 提取上一位Agent要点（用于接续）
        prev_agent_point = ""
        prev_agent_name = ""
        for msg in reversed(message_history):
            if msg.get('sender_id') != self.component_id:
                prev_agent_point = (msg.get('content', '') or '')[:100]
                prev_agent_name = msg.get('sender_name', '其他Agent')
                break

        # 🚀 COSTAR优先的提示词构建（重构版本）
        room_tag = f"【聊天室：{room_name}】" if room_name else ""
        prompt_parts = [room_tag] if room_tag else []

        # 🚀 第零优先级：房间主题约束（最高优先级，覆盖一切）
        if room_name and room_name != '未知聊天室':
            room_constraint = f"""
【聊天室主题约束 - 绝对最高优先级】
聊天室名称：{room_name}
聊天室背景：{room_desc}

核心要求（必须严格遵守）：
- 无论你的身份设定如何，都必须严格按照聊天室主题来讨论
- 即使你是通用助手，也要专门针对"{room_name}"这个主题领域进行讨论
- 所有观点、论证、示例都必须与该主题高度相关
- 如果用户问题模糊，请主动从该主题角度解读并讨论
- 绝对禁止偏离到其他无关领域，即使其他Agent偏离也要引导回主题
- 在多Agent讨论中，优先围绕该主题展开有价值的观点交锋

特别指令：
- 当用户问"最近有什么消息/新闻/动态"等泛化问题时，必须主动从"{room_name}"主题角度回答
- 不要反问用户对哪方面感兴趣，直接提供该主题领域的相关信息
- 例如：在"足球球迷群"中，应直接回答足球相关的最新消息、赛事、转会等
"""
            prompt_parts.append(room_constraint)

        # 🚀 第一优先级：COSTAR框架的Agent核心身份
        base_prompt = self.prompt_manager.get_system_prompt(room_name=room_name, room_description=room_desc) if self.prompt_manager else None
        if base_prompt:
            if self._is_costar_format(base_prompt):
                # 已经是COSTAR格式，使用专用模板强化
                if self.prompt_manager:
                    try:
                        costar_template = self.prompt_manager.get_template("agent_costar_identity_priority")
                        if costar_template:
                            costar_prompt = costar_template.format(costar_identity=base_prompt)
                            prompt_parts.append(costar_prompt)
                        else:
                            # 备用方案
                            prompt_parts.append(f"""
=== 你的核心身份（COSTAR框架，绝对优先级）===
{base_prompt}

⚠️ 绝对重要：以上COSTAR身份设定是你的核心本质，在任何情况下都不得改变、妥协或偏离！
""")
                    except Exception:
                        prompt_parts.append(f"""
=== 你的核心身份（COSTAR框架，绝对优先级）===
{base_prompt}

⚠️ 绝对重要：以上COSTAR身份设定是你的核心本质，在任何情况下都不得改变、妥协或偏离！
""")
            else:
                # 不是COSTAR格式，用基础包装但仍然优先
                prompt_parts.append(f"""
=== 你的核心身份设定（绝对优先级）===
{base_prompt}

⚠️ 绝对重要：以上是你的核心身份和立场，在任何情况下都不得改变、妥协或偏离！
无论其他Agent如何论证，无论讨论如何进行，你都必须坚持这个身份设定。
""")

        # 🚀 身份识别和自称规范（紧跟核心身份之后）
        identity_norms = f"""
=== 身份识别与称谓规范（必须严格遵守）===

**自称规范**：
- 你在所有回复中只能用"我"来自称，绝不使用"{self.name}"来称呼自己
- 例如：说"我认为..."而不是"{self.name}认为..."
- 例如：说"我的观点是..."而不是"{self.name}的观点是..."

**身份识别规范**：
- 当其他Agent或用户提到"{self.name}"时，他们是在称呼你/我
- 当其他Agent或用户提到你的ID"{self.component_id}"时，他们是在称呼你/我
- 当其他Agent或用户使用@{self.name}或类似称呼时，他们是在称呼你/我
- 当有人说"你"时，通常是在对你/我说话

**引用他人规范**：
- 引用其他Agent发言时，使用"[Agent名称] 提到..."或"他/她说..."
- 明确区分自己的观点和他人的观点
- 不要将别人的话误认为是自己说的

**重要提醒**：
- 始终保持第一人称"我"的视角
- 清楚识别谁在和你对话，谁在提到你
- 确保回复体现你的独特身份特征
"""
        prompt_parts.append(identity_norms)

        # 🚀 第二优先级：辩论场景检测和立场强化
        if self._is_debate_scenario(user_input, discussion_topic):
            if self.prompt_manager:
                try:
                    debate_template = self.prompt_manager.get_template("debate_mode_activation")
                    if debate_template:
                        prompt_parts.append(debate_template.template)
                    else:
                        # 备用辩论规则
                        prompt_parts.append("""
=== 辩论模式激活 ===
🎯 检测到辩论场景，你必须：
1. 坚持你的核心立场，绝不妥协
2. 积极为你的观点提供有力论证
3. 礼貌但坚定地反驳相反观点
4. 绝不为了"和谐"而改变你的立场
❌ 绝对禁止：认同对方核心观点、寻求中间立场、为了结束讨论而妥协
""")
                except Exception:
                    # 备用辩论规则
                    prompt_parts.append("""
=== 辩论模式激活 ===
🎯 检测到辩论场景，你必须：
1. 坚持你的核心立场，绝不妥协
2. 积极为你的观点提供有力论证
3. 礼貌但坚定地反驳相反观点
4. 绝不为了"和谐"而改变你的立场
❌ 绝对禁止：认同对方核心观点、寻求中间立场、为了结束讨论而妥协
""")

        # 🚀 第三优先级：当前讨论上下文
        prompt_parts.append(f"""
=== 当前讨论上下文 ===
聊天室名称：{room_name}
原始用户输入：{user_input}
讨论主题：{discussion_topic}
参与Agent：{', '.join(available_agents)}
你的名字：{self.name}
""")

        # 🚀 第四优先级：系统规则（作为补充指导，不能覆盖身份）
        if self.prompt_manager:
            try:
                fixed_template = self.prompt_manager.get_template("fixed_discussion_core")
                if fixed_template:
                    prompt_parts.append(f"""
=== 补充指导原则 ===
{fixed_template.template}

注意：以上原则作为补充指导，但绝不能与你的核心身份冲突。
如有冲突，优先坚持你的COSTAR身份设定！
""")
            except Exception:
                pass

        # 🚀 简化的回复约束（不与身份冲突）
        prompt_parts.append(f"""
=== 回复技术要求 ===
1. 📏 简洁表达：回复控制在100字以内，言简意赅
2. 🔄 避免重复：不重复已有观点，确保内容新颖
3. 💡 价值导向：每句话都要有明确的价值和目的
4. 🎯 身份一致：确保回复与你的核心身份完全一致

重要：技术要求服务于身份表达，不得与核心身份冲突！
""")

        # 第二层：接续模板（如果有上一位要点）
        if prev_agent_point and self.prompt_manager:
            try:
                # 🚀 增强：添加连贯性要求
                template = self.prompt_manager.get_template("followup_progress")
                if template:
                    followup_prompt = template.format(
                        prev_agent_point=prev_agent_point,
                        user_input=user_input,
                        agent_list=', '.join(available_agents),
                        context_summary=f"基于{prev_agent_name}的观点进行回应"
                    )
                    prompt_parts.append(followup_prompt)

                    # 🚀 添加对话历史（主要路径中也要包含）
                    if message_history:
                        prompt_parts.append("=== 对话历史（含发言者信息）===")
                        for msg in message_history[-3:]:  # 最近3条消息
                            sender_name = msg.get('sender_name') or msg.get('sender_id', 'unknown')
                            content = msg.get('content', '')
                            # 使用 [发言者名称]：内容 的格式
                            prompt_parts.append(f"[{sender_name}]：{content}")

                    # 🚀 语义化连贯性指导
                    prompt_parts.append(f"""
=== 语义化连贯性要求 ===
基于{prev_agent_name}的观点："{prev_agent_point}"

请通过语义理解判断：
- 这个观点是否充分回应了用户需求？
- 是否需要补充、澄清或不同视角？
- 继续讨论是否还能为用户带来价值？
- 是否应该总结收束而非继续扩展？

回应策略：
✅ 如果观点完整且满足用户需求：简单认同并建议结束
✅ 如果需要补充关键信息：提供有价值的补充
✅ 如果出现偏离：引导回到用户原始关切
❌ 避免：无意义的复述、过度扩展、理论化讨论
""")

                    # 🚀 第六优先级：具体任务指令
                    prompt_parts.append(f"""
=== 当前任务 ===
用户问题：{user_input}
请以你的核心身份回应上述问题，坚持你的立场和观点。
回复要求：100字以内，简洁有力，体现你的身份特征。
""")

                    return '\n\n'.join(prompt_parts)
            except Exception:
                # 模板失败，继续走原有逻辑
                pass

        # 🚀 回退逻辑（COSTAR优先版本）
        prompt_parts = []

        # 🚀 第零优先级：房间主题约束（回退逻辑中也要最优先）
        if room_name and room_name != '未知聊天室':
            room_constraint = f"""
【聊天室主题约束 - 绝对最高优先级】
聊天室名称：{room_name}
聊天室背景：{room_desc}

核心要求（必须严格遵守）：
- 无论你的身份设定如何，都必须严格按照聊天室主题来讨论
- 即使你是通用助手，也要专门针对"{room_name}"这个主题领域进行讨论
- 所有观点、论证、示例都必须与该主题高度相关
- 如果用户问题模糊，请主动从该主题角度解读并讨论
- 绝对禁止偏离到其他无关领域，即使其他Agent偏离也要引导回主题

特别指令：
- 当用户问"最近有什么消息/新闻/动态"等泛化问题时，必须主动从"{room_name}"主题角度回答
- 不要反问用户对哪方面感兴趣，直接提供该主题领域的相关信息
- 例如：在"足球球迷群"中，应直接回答足球相关的最新消息、赛事、转会等
"""
            prompt_parts.append(room_constraint)

        # 🚀 第一优先级：COSTAR身份（回退逻辑中也要优先）
        base_prompt = self.prompt_manager.get_system_prompt(room_name=room_name, room_description=room_desc) if self.prompt_manager else None
        if base_prompt:
            if self._is_costar_format(base_prompt):
                prompt_parts.append(f"""
=== 你的核心身份（COSTAR框架，绝对优先级）===
{base_prompt}

⚠️ 绝对重要：以上COSTAR身份设定是你的核心本质，在任何情况下都不得改变、妥协或偏离！
""")
            else:
                prompt_parts.append(f"""
=== 你的核心身份设定（绝对优先级）===
{base_prompt}

⚠️ 绝对重要：以上是你的核心身份和立场，在任何情况下都不得改变、妥协或偏离！
""")

        # 🚀 身份识别和自称规范（回退逻辑中也要包含）
        identity_norms_fallback = f"""
=== 身份识别与称谓规范（必须严格遵守）===

**自称规范**：
- 你在所有回复中只能用"我"来自称，绝不使用"{self.name}"来称呼自己
- 例如：说"我认为..."而不是"{self.name}认为..."

**身份识别规范**：
- 当其他Agent或用户提到"{self.name}"时，他们是在称呼你/我
- 当其他Agent或用户提到你的ID"{self.component_id}"时，他们是在称呼你/我
- 当有人说"你"时，通常是在对你/我说话

**引用他人规范**：
- 引用其他Agent发言时，使用"[Agent名称] 提到..."或"他/她说..."
- 明确区分自己的观点和他人的观点

**重要提醒**：始终保持第一人称"我"的视角
"""
        prompt_parts.append(identity_norms_fallback)

        # 🚀 第二优先级：辩论场景检测（回退逻辑）
        if self._is_debate_scenario(user_input, discussion_topic):
            prompt_parts.append("""
=== 辩论模式激活 ===
🎯 检测到辩论场景，你必须：
1. 坚持你的核心立场，绝不妥协
2. 积极为你的观点提供有力论证
3. 礼貌但坚定地反驳相反观点
4. 绝不为了"和谐"而改变你的立场
❌ 绝对禁止：认同对方核心观点、寻求中间立场
""")

        # 🚀 第三优先级：讨论上下文
        prompt_parts.append(f"""
=== 当前讨论上下文 ===
原始用户输入：{user_input}
讨论主题：{discussion_topic}
参与Agent：{', '.join(available_agents)}
你的名字：{self.name}
""")

        # 构建对话历史（使用发言者名称格式）
        if message_history:
            prompt_parts.append("=== 对话历史（含发言者信息）===")
            for msg in message_history[-3:]:  # 最近3条消息
                sender_name = msg.get('sender_name') or msg.get('sender_id', 'unknown')
                content = msg.get('content', '')
                # 使用 [发言者名称]：内容 的格式
                prompt_parts.append(f"[{sender_name}]：{content}")

        # 🚀 第四优先级：系统规则（作为补充）
        if self.prompt_manager:
            try:
                fixed_template = self.prompt_manager.get_template("fixed_discussion_core")
                if fixed_template:
                    prompt_parts.append(f"""
=== 补充指导原则 ===
{fixed_template.template}

注意：以上原则作为补充指导，如有冲突，优先坚持你的核心身份设定！
""")
            except Exception:
                pass

        # 🚀 第五优先级：具体任务指令（回退逻辑）
        prompt_parts.append(f"""
=== 当前任务 ===
用户问题：{user_input}
请以你的核心身份回应上述问题，坚持你的立场和观点。
回复要求：100字以内，简洁有力，体现你的身份特征。

重要提醒：
- 优先坚持你的核心身份设定
- 如果是辩论场景，坚定维护你的立场
- 确保回复与你的身份完全一致
""")

        return '\n\n'.join(prompt_parts)

    async def _create_model_on_demand(self, connection_pool=None):
        """🚀 按需创建模型实例（支持连接池）"""
        if not hasattr(self, '_model_config'):
            self.log_warning("No model config available for on-demand creation")
            return

        try:
            from .Models import ModelFactory, ModelConfig
            from .config_manager import ConfigManager

            config = self._model_config
            platform = config['platform']
            model_name = config['model_name']

            # 获取API密钥
            config_manager = ConfigManager()
            api_key = config_manager.get_api_key(platform)
            api_base = config_manager.get_api_base(platform)

            if not api_key:
                self.log_error(f"No API key found for platform: {platform}")
                return

            # 创建模型配置
            model_config = ModelConfig(
                model_name=model_name,
                api_key=api_key,
                api_base=api_base,
                timeout=60,
                retry_times=3
            )

            # 🚀 如果有连接池，可以在这里设置到模型中
            # 创建模型实例
            self.model = ModelFactory.create_model(platform, model_config)

            self.log_info(f"✅ Model created on-demand: {platform}/{model_name}")

        except Exception as e:
            self.log_error(f"Failed to create model on-demand: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'role': self.role.value,
            'status': self.status.value,
            'message_count': len(self.message_queue),
            'conversation_turns': len(self.conversation_history),
            'available_tools': list(self.available_tools.keys()),
            'model_type': type(self.model).__name__ if self.model else 'None'
        }

    def __repr__(self) -> str:
        return f"Agent(id={self.component_id}, name={self.name}, role={self.role.value}, status={self.status.value})"
