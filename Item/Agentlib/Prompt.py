"""
Prompt - 提示词管理模块
管理和组织各种Agent的提示词模板
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from string import Template

from ..FlowTools.base_component import BaseComponent
from ..ContextEngineer.context_manager import StructuredContext


@dataclass
class PromptTemplate:
    """提示词模板"""
    name: str
    template: str
    description: str = ""
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def format(self, **kwargs) -> str:
        """格式化模板"""
        # 使用Template进行安全的字符串替换
        template_obj = Template(self.template)
        return template_obj.safe_substitute(**kwargs)


class PromptManager(BaseComponent):
    """提示词管理器"""
    
    def __init__(self, manager_id: str = "prompt_manager"):
        super().__init__(manager_id, "prompt_manager")
        
        # 存储提示词模板
        self.templates: Dict[str, PromptTemplate] = {}
        
        # 初始化默认模板
        self._init_default_templates()
        
        self.log_debug("PromptManager initialized", {
            'template_count': len(self.templates)
        })
    
    def _init_default_templates(self):
        """初始化默认提示词模板"""
        
        # 聊天Agent模板
        self.add_template(
            "chat",
            PromptTemplate(
                name="chat_agent",
                template="""你是$agent_name，一个友好的聊天助手。

你的角色：$role_description

当前对话上下文：
$context_summary

用户输入：$user_input

请根据上述信息，以友好、专业的方式回应用户。""",
                description="基础聊天Agent提示词模板",
                variables=["agent_name", "role_description", "context_summary", "user_input"]
            )
        )
        
        # 工具调用Agent模板
        self.add_template(
            "tools",
            PromptTemplate(
                name="tools_agent",
                template="""你是$agent_name，一个专门负责工具调用的Agent。

可用工具：
$available_tools

任务描述：
$task_description

上下文信息：
$context_info

请分析任务需求，选择合适的工具并生成调用参数。如果需要多个工具配合，请说明调用顺序。

输出格式：
1. 需要调用的工具：[工具名称]
2. 调用参数：[参数详情]
3. 预期结果：[描述预期的结果]""",
                description="工具调用Agent提示词模板",
                variables=["agent_name", "available_tools", "task_description", "context_info"]
            )
        )
        
        # 协调Agent模板
        self.add_template(
            "coordinator",
            PromptTemplate(
                name="coordinator_agent",
                template="""你是$agent_name，一个协调多个Agent协作的协调者。

当前群聊中的Agent：
$agent_list

任务目标：
$task_goal

对话历史：
$conversation_history

请分析当前任务进展，决定：
1. 下一步应该由哪个Agent处理
2. 需要传递什么信息给该Agent
3. 是否需要多个Agent并行工作

输出你的协调决策。""",
                description="协调Agent提示词模板",
                variables=["agent_name", "agent_list", "task_goal", "conversation_history"]
            )
        )
        
        # 专家Agent模板
        self.add_template(
            "specialist",
            PromptTemplate(
                name="specialist_agent",
                template="""你是$agent_name，一位$specialty领域的专家。

你的专业背景：
$expertise_description

当前问题：
$question

相关上下文：
$context

请运用你的专业知识，为用户提供准确、深入的解答。如果问题超出你的专业范围，请诚实说明。""",
                description="专家Agent提示词模板",
                variables=["agent_name", "specialty", "expertise_description", "question", "context"]
            )
        )
        
        # 任务转换模板（Agent1到ToolsAgent）
        self.add_template(
            "task_transform",
            PromptTemplate(
                name="task_transform",
                template="""将用户需求转换为结构化的任务描述。

用户原始输入：$user_input

历史对话摘要：
$conversation_summary

请将用户需求转换为以下格式：
用户想要：[明确的目标]
要求是：[具体的要求和约束]
根据用户之前说过的话：[相关的历史信息]
我现在需要：[需要执行的具体操作]
具体需求：
a. $requirement_1
b. $requirement_2
...""",
                description="任务转换提示词模板",
                variables=["user_input", "conversation_summary", "requirement_1", "requirement_2"]
            )
        )
    
    def add_template(self, template_type: str, template: PromptTemplate) -> None:
        """添加提示词模板"""
        self.templates[template_type] = template
        
        self.log_debug(f"Added template: {template_type}", {
            'template_name': template.name,
            'variables': template.variables
        })
    
    def set_system_prompt(self, prompt: str) -> None:
        """
        设置系统提示词
        
        Args:
            prompt: 系统提示词内容
        """
        # 创建自定义系统提示词模板
        system_template = PromptTemplate(
            name="custom_system_prompt",
            template=prompt,
            description="Custom system prompt set by user",
            variables=[]
        )
        
        # 存储为系统模板
        self.templates["system"] = system_template
        
        self.log_debug("System prompt set", {
            'prompt_length': len(prompt)
        })
    
    def get_system_prompt(self) -> Optional[str]:
        """获取系统提示词"""
        system_template = self.templates.get("system")
        if system_template:
            return system_template.template
        return None
    
    def get_template(self, template_type: str) -> Optional[PromptTemplate]:
        """获取提示词模板"""
        return self.templates.get(template_type)
    
    def get_prompt(self, 
                   template_type: str,
                   context: Optional[StructuredContext] = None,
                   agent_metadata: Optional[Any] = None,
                   **kwargs) -> str:
        """
        获取格式化后的提示词
        
        Args:
            template_type: 模板类型
            context: 结构化上下文
            agent_metadata: Agent元数据
            **kwargs: 额外的模板变量
            
        Returns:
            格式化后的提示词
        """
        template = self.get_template(template_type)
        if not template:
            self.log_warning(f"Template not found: {template_type}")
            return f"[未找到模板: {template_type}]"
        
        # 准备模板变量
        template_vars = kwargs.copy()
        
        # 从上下文提取信息
        if context:
            template_vars['user_input'] = context.user_input
            template_vars['context_summary'] = self._generate_context_summary(context)
            template_vars['context_info'] = self._format_context_info(context)
            
            # 对话历史
            if context.conversation_history:
                template_vars['conversation_history'] = self._format_conversation_history(context.conversation_history)
                template_vars['conversation_summary'] = self._summarize_conversation(context.conversation_history)
        
        # 从Agent元数据提取信息
        if agent_metadata:
            template_vars['agent_name'] = getattr(agent_metadata, 'name', 'Agent')
            template_vars['role_description'] = getattr(agent_metadata, 'description', '')
            
            # 能力列表
            capabilities = getattr(agent_metadata, 'capabilities', [])
            if capabilities:
                template_vars['available_tools'] = '\n'.join(f"- {cap}" for cap in capabilities)
            
            # 自定义属性
            custom_attrs = getattr(agent_metadata, 'custom_attributes', {})
            template_vars.update(custom_attrs)
        
        # 格式化模板
        try:
            prompt = template.format(**template_vars)
            
            self.log_debug(f"Generated prompt for template: {template_type}", {
                'prompt_length': len(prompt),
                'variables_used': list(template_vars.keys())
            })
            
            return prompt
            
        except Exception as e:
            self.log_error(f"Error formatting template: {template_type}", e)
            return f"[模板格式化错误: {str(e)}]"
    
    def _generate_context_summary(self, context: StructuredContext) -> str:
        """生成上下文摘要"""
        summary_parts = []
        
        if context.conversation_history:
            summary_parts.append(f"已进行{len(context.conversation_history)}轮对话")
        
        if context.tool_results:
            summary_parts.append(f"调用了{len(context.tool_results)}个工具")
        
        if context.external_data:
            summary_parts.append(f"检索到{len(context.external_data)}条相关信息")
        
        return "；".join(summary_parts) if summary_parts else "无历史上下文"
    
    def _format_context_info(self, context: StructuredContext) -> str:
        """格式化上下文信息"""
        info_parts = []
        
        # 开发者指令
        if context.developer_instructions:
            info_parts.append("开发者指令：")
            info_parts.extend(f"  - {instruction}" for instruction in context.developer_instructions)
        
        # 工具结果
        if context.tool_results:
            info_parts.append("\n工具调用结果：")
            for result in context.tool_results:
                tool_name = result.get('metadata', {}).get('tool_name', 'unknown')
                info_parts.append(f"  - {tool_name}: {result['content'][:100]}...")
        
        # 外部数据
        if context.external_data:
            info_parts.append("\n相关信息：")
            for data in context.external_data[:3]:  # 只显示前3条
                info_parts.append(f"  - {data['content'][:100]}...")
        
        return "\n".join(info_parts) if info_parts else "无额外上下文信息"
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        formatted_turns = []
        
        for turn in history[-5:]:  # 只显示最近5轮
            if 'user' in turn:
                formatted_turns.append(f"用户：{turn['user']}")
            if 'assistant' in turn:
                formatted_turns.append(f"助手：{turn['assistant']}")
        
        return "\n".join(formatted_turns) if formatted_turns else "无对话历史"
    
    def _summarize_conversation(self, history: List[Dict[str, Any]]) -> str:
        """总结对话历史"""
        if not history:
            return "无对话历史"
        
        # 简单的总结逻辑
        topics = []
        for turn in history:
            if 'user' in turn:
                # 提取可能的主题词（简化实现）
                words = turn['user'].split()
                important_words = [w for w in words if len(w) > 4][:3]
                topics.extend(important_words)
        
        unique_topics = list(set(topics))[:5]
        
        if unique_topics:
            return f"讨论了关于{', '.join(unique_topics)}等话题"
        else:
            return f"进行了{len(history)}轮对话"
    
    def create_custom_template(self, 
                              name: str,
                              template_str: str,
                              description: str = "",
                              variables: List[str] = None) -> PromptTemplate:
        """创建自定义模板"""
        # 自动检测模板中的变量
        if variables is None:
            import re
            # 查找所有$variable格式的变量
            variables = re.findall(r'\$(\w+)', template_str)
            variables = list(set(variables))  # 去重
        
        template = PromptTemplate(
            name=name,
            template=template_str,
            description=description,
            variables=variables
        )
        
        self.log_info(f"Created custom template: {name}", {
            'variables': variables
        })
        
        return template
    
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """列出所有模板"""
        return {
            template_type: {
                'name': template.name,
                'description': template.description,
                'variables': template.variables,
                'preview': template.template[:200] + '...' if len(template.template) > 200 else template.template
            }
            for template_type, template in self.templates.items()
        }
    
    def export_templates(self) -> Dict[str, Any]:
        """导出所有模板"""
        return {
            template_type: {
                'name': template.name,
                'template': template.template,
                'description': template.description,
                'variables': template.variables,
                'metadata': template.metadata
            }
            for template_type, template in self.templates.items()
        }
    
    def import_templates(self, templates_data: Dict[str, Any]) -> None:
        """导入模板"""
        for template_type, template_info in templates_data.items():
            template = PromptTemplate(
                name=template_info['name'],
                template=template_info['template'],
                description=template_info.get('description', ''),
                variables=template_info.get('variables', []),
                metadata=template_info.get('metadata', {})
            )
            self.add_template(template_type, template)
        
        self.log_info(f"Imported {len(templates_data)} templates")
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')
            
            if action == 'get_prompt':
                return self.get_prompt(
                    input_data['template_type'],
                    input_data.get('context'),
                    input_data.get('agent_metadata'),
                    **input_data.get('variables', {})
                )
            
            elif action == 'list_templates':
                return self.list_templates()
            
            elif action == 'create_custom':
                template = self.create_custom_template(
                    input_data['name'],
                    input_data['template'],
                    input_data.get('description', ''),
                    input_data.get('variables')
                )
                return {'template': template.name, 'success': True}
            
            else:
                raise ValueError(f"Unknown action: {action}")
        
        else:
            raise ValueError("PromptManager requires dict input with 'action' field")
