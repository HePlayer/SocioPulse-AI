"""
Workflow - 预定义的工作流程
基于FlowTools实现的标准流程模板
"""

from typing import Dict, List, Any, Optional
import asyncio

from .FlowTools import FlowEngine, NodeFactory
from .Agentlib import Agent, AgentRole, ModelFactory, ModelConfig
from .Agentlib.Tools import CalculatorTool, FileTool, WebSearchTool, CodeExecutorTool


class WorkflowBuilder:
    """工作流程构建器"""
    
    def __init__(self):
        self.node_factory = NodeFactory("workflow_factory")
        self.registered_agents: Dict[str, Agent] = {}
        self.registered_tools: Dict[str, Any] = {}
        
        # 注册默认工具
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        self.registered_tools['calculator'] = CalculatorTool()
        self.registered_tools['file_tool'] = FileTool()
        self.registered_tools['web_search'] = WebSearchTool()
        self.registered_tools['code_executor'] = CodeExecutorTool()
    
    def create_agent(self, 
                    agent_id: str,
                    name: str,
                    role: AgentRole,
                    model_type: str = "openai",
                    model_config: Optional[ModelConfig] = None,
                    model_name: Optional[str] = None) -> Agent:
        """创建Agent"""
        
        # 读取配置文件中的API密钥和配置
        api_key = self._get_api_key_from_config(model_type)
        platform_config = self._get_platform_config_from_config(model_type)
        
        # 创建模型配置
        if model_config is None:
            # 优先使用指定的model_name，确保用户选择被正确应用
            if model_name:
                selected_model = model_name
            else:
                # 从配置文件获取默认模型，优先使用免费模型
                if platform_config and 'default_model' in platform_config:
                    selected_model = platform_config['default_model']
                else:
                    # 优先使用免费模型作为默认选择
                    default_models = {
                        'openai': 'gpt-3.5-turbo',  # OpenAI最便宜的模型
                        'aihubmix': 'gpt-4o-mini', 
                        'zhipuai': 'glm-4-flash-250414',  # 智谱AI免费模型
                        'zhipu': 'glm-4-flash-250414'  # 智谱AI免费模型（兼容性别名）
                    }
                    selected_model = default_models.get(model_type, "glm-4-flash-250414")  # 默认使用免费模型
            
            # 从配置文件获取API base，如果没有则使用默认值
            if platform_config and 'api_base' in platform_config:
                api_base = platform_config['api_base']
            else:
                api_bases = {
                    'openai': 'https://api.openai.com/v1',
                    'aihubmix': 'https://aihubmix.com/v1',
                    'zhipuai': 'https://open.bigmodel.cn/api/paas/v4',
                    'zhipu': 'https://open.bigmodel.cn/api/paas/v4'
                }
                api_base = api_bases.get(model_type, "https://api.openai.com/v1")
            
            model_config = ModelConfig(
                model_name=selected_model,
                api_key=api_key,
                api_base=api_base
            )
        
        try:
            # 创建模型
            model = None
            if api_key:  # 只有在有API密钥时才创建模型
                model = ModelFactory.create_model(model_type, model_config)
            else:
                print(f"Warning: No API key found for {model_type}, Agent will work in basic mode")
            
            # 创建上下文管理器
            from .ContextEngineer.context_manager import ContextManager
            context_manager = ContextManager(f"{agent_id}_context")
            
            # 创建提示词管理器
            from .Agentlib.Prompt import PromptManager
            prompt_manager = PromptManager(f"{agent_id}_prompt")
            
            # 创建Agent
            agent = Agent(
                agent_id=agent_id,
                name=name,
                role=role,
                model=model,
                context_manager=context_manager,
                prompt_manager=prompt_manager
            )
            
            # 注册工具
            if role == AgentRole.TOOLS:
                for tool_name, tool in self.registered_tools.items():
                    agent.register_tool(tool_name, tool.execute, tool.description)
            
            self.registered_agents[agent_id] = agent
            return agent
            
        except Exception as e:
            # 提供更详细的错误信息
            raise Exception(f"Failed to create agent '{name}' with model type '{model_type}': {str(e)}")
    
    def _get_api_key_from_config(self, model_type: str) -> str:
        """从配置文件读取API密钥"""
        try:
            import yaml
            import os
            
            config_path = os.path.join(os.getcwd(), 'config.yaml')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                if 'models' in config and 'platforms' in config['models']:
                    platforms = config['models']['platforms']
                    platform_config = platforms.get(model_type, {})
                    return platform_config.get('api_key', '')
            
            # 如果没有配置文件，尝试从环境变量读取
            env_keys = {
                'openai': 'OPENAI_API_KEY',
                'aihubmix': 'AIHUBMIX_API_KEY',
                'zhipuai': 'ZHIPUAI_API_KEY',
                'zhipu': 'ZHIPUAI_API_KEY'
            }
            
            env_key = env_keys.get(model_type)
            if env_key:
                return os.getenv(env_key, '')
            
            return ''
            
        except Exception as e:
            print(f"Warning: Failed to read API key for {model_type}: {e}")
            return ''
    
    def _get_platform_config_from_config(self, model_type: str) -> Dict[str, Any]:
        """从配置文件读取平台配置"""
        try:
            import yaml
            import os
            
            config_path = os.path.join(os.getcwd(), 'config.yaml')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                if 'models' in config and 'platforms' in config['models']:
                    platforms = config['models']['platforms']
                    return platforms.get(model_type, {})
            
            return {}
            
        except Exception as e:
            print(f"Warning: Failed to read platform config for {model_type}: {e}")
            return {}
    
    def build_simple_chat_workflow(self) -> FlowEngine:
        """构建简单的聊天工作流程"""
        engine = FlowEngine("simple_chat_flow")
        
        # 创建聊天Agent
        chat_agent = self.create_agent(
            "chat_agent_1",
            "小助手",
            AgentRole.CHAT
        )
        
        # 添加到流程
        engine.add_node(chat_agent)
        
        return engine
    
    def build_standard_workflow(self) -> FlowEngine:
        """
        构建标准工作流程
        用户输入 -> Agent1 -> ToolsAgent -> Agent1 -> 输出
        """
        engine = FlowEngine("standard_workflow")
        
        # 创建Agent1（聊天Agent）
        agent1 = self.create_agent(
            "agent1",
            "Agent1",
            AgentRole.CHAT
        )
        
        # 创建ToolsAgent
        tools_agent = self.create_agent(
            "tools_agent",
            "ToolsAgent",
            AgentRole.TOOLS
        )
        
        # 创建条件节点：判断是否需要调用工具
        def needs_tools(data: Dict[str, Any]) -> bool:
            response = data.get('response', '')
            # 简单的判断逻辑
            tool_keywords = ['计算', '搜索', '文件', '代码', '工具']
            return any(keyword in response for keyword in tool_keywords)
        
        condition_node = self.node_factory.create_conditional_node(
            "check_tools_needed",
            needs_tools,
            true_path="tools_agent",
            false_path="final_output"
        )
        
        # 添加节点
        engine.add_node(agent1)
        engine.add_node(condition_node)
        engine.add_node(tools_agent)
        
        # 添加边
        engine.add_edge("agent1", "check_tools_needed")
        engine.add_edge("tools_agent", "agent1")  # 工具结果返回给Agent1
        
        return engine
    
    def build_multi_agent_workflow(self, agent_configs: List[Dict[str, Any]]) -> FlowEngine:
        """
        构建多Agent协作工作流程
        
        Args:
            agent_configs: Agent配置列表，每个配置包含：
                - id: Agent ID
                - name: Agent名称
                - role: Agent角色
                - specialty: 专业领域（可选）
        """
        engine = FlowEngine("multi_agent_workflow")
        
        # 创建协调Agent
        coordinator = self.create_agent(
            "coordinator",
            "协调者",
            AgentRole.COORDINATOR
        )
        
        # 创建专家Agents
        expert_agents = []
        for config in agent_configs:
            agent = self.create_agent(
                config['id'],
                config['name'],
                AgentRole.SPECIALIST
            )
            
            # 设置专业领域
            if 'specialty' in config:
                agent.set_metadata(
                    specialty=config['specialty'],
                    expertise_description=config.get('description', '')
                )
            
            expert_agents.append(agent)
            engine.add_node(agent)
        
        # 添加协调Agent
        engine.add_node(coordinator)
        
        # 创建并行节点来同时咨询多个专家
        parallel_node = self.node_factory.create_parallel_node(
            "parallel_consultation",
            expert_agents,
            wait_for_all=True
        )
        
        engine.add_node(parallel_node)
        
        # 添加边
        engine.add_edge("coordinator", "parallel_consultation")
        engine.add_edge("parallel_consultation", "coordinator")  # 结果返回给协调者
        
        return engine
    
    def build_task_processing_workflow(self) -> FlowEngine:
        """构建任务处理工作流程（带错误处理）"""
        engine = FlowEngine("task_processing_workflow")
        
        # 创建任务分析Agent
        analyzer = self.create_agent(
            "task_analyzer",
            "任务分析师",
            AgentRole.CHAT
        )
        
        # 创建执行Agent
        executor = self.create_agent(
            "task_executor",
            "任务执行者",
            AgentRole.TOOLS
        )
        
        # 创建错误处理Agent
        error_handler = self.create_agent(
            "error_handler",
            "错误处理专家",
            AgentRole.SPECIALIST
        )
        
        # 创建条件节点：检查执行结果
        def check_execution_result(data: Dict[str, Any]) -> bool:
            return data.get('success', False)
        
        result_checker = self.node_factory.create_conditional_node(
            "check_result",
            check_execution_result,
            true_path="success_output",
            false_path="error_handler"
        )
        
        # 添加节点
        engine.add_node(analyzer)
        engine.add_node(executor)
        engine.add_node(error_handler)
        engine.add_node(result_checker)
        
        # 添加边
        engine.add_edge("task_analyzer", "task_executor")
        engine.add_edge("task_executor", "check_result")
        engine.add_edge("error_handler", "task_executor")  # 错误处理后重试
        
        # 设置最大重试次数
        engine.metadata['max_retries'] = 3
        
        return engine


class WorkflowExecutor:
    """工作流程执行器"""
    
    def __init__(self, workflow_engine: FlowEngine):
        self.engine = workflow_engine
        self.execution_history: List[Dict[str, Any]] = []
    
    async def execute(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行工作流程
        
        Args:
            user_input: 用户输入
            context: 额外的上下文信息
            
        Returns:
            执行结果
        """
        # 准备输入数据
        input_data = {
            'user_input': user_input,
            'context': context or {},
            'timestamp': asyncio.get_event_loop().time()
        }
        
        try:
            # 执行流程
            execution = await self.engine.execute_flow(input_data)
            
            # 记录执行历史
            self.execution_history.append({
                'input': user_input,
                'execution_id': execution.execution_id,
                'status': execution.status.value,
                'duration': execution.end_time - execution.start_time,
                'result': execution.get_final_output()
            })
            
            # 返回最终结果
            return {
                'success': execution.status.value == 'completed',
                'result': execution.get_final_output(),
                'execution_path': execution.execution_path,
                'duration': execution.end_time - execution.start_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'result': None
            }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        if not self.execution_history:
            return {'total_executions': 0}
        
        successful_executions = sum(1 for h in self.execution_history if h.get('status') == 'completed')
        total_duration = sum(h.get('duration', 0) for h in self.execution_history)
        
        return {
            'total_executions': len(self.execution_history),
            'successful_executions': successful_executions,
            'success_rate': successful_executions / len(self.execution_history),
            'average_duration': total_duration / len(self.execution_history),
            'recent_executions': self.execution_history[-5:]  # 最近5次执行
        }


# 预定义的工作流程模板
class WorkflowTemplates:
    """预定义的工作流程模板"""
    
    @staticmethod
    def get_simple_qa_workflow() -> Dict[str, Any]:
        """简单问答流程"""
        return {
            'name': 'simple_qa',
            'description': '简单的问答流程，适用于基础对话',
            'nodes': [
                {'id': 'qa_agent', 'type': 'agent', 'role': 'chat'}
            ],
            'edges': []
        }
    
    @staticmethod
    def get_research_workflow() -> Dict[str, Any]:
        """研究流程"""
        return {
            'name': 'research',
            'description': '研究流程，包含搜索、分析和总结',
            'nodes': [
                {'id': 'researcher', 'type': 'agent', 'role': 'specialist', 'specialty': 'research'},
                {'id': 'search_tool', 'type': 'tool', 'tool': 'web_search'},
                {'id': 'analyzer', 'type': 'agent', 'role': 'specialist', 'specialty': 'analysis'},
                {'id': 'summarizer', 'type': 'agent', 'role': 'specialist', 'specialty': 'summary'}
            ],
            'edges': [
                {'from': 'researcher', 'to': 'search_tool'},
                {'from': 'search_tool', 'to': 'analyzer'},
                {'from': 'analyzer', 'to': 'summarizer'}
            ]
        }
    
    @staticmethod
    def get_coding_workflow() -> Dict[str, Any]:
        """编程流程"""
        return {
            'name': 'coding',
            'description': '编程流程，包含代码生成、执行和调试',
            'nodes': [
                {'id': 'code_designer', 'type': 'agent', 'role': 'specialist', 'specialty': 'software_design'},
                {'id': 'code_generator', 'type': 'agent', 'role': 'specialist', 'specialty': 'coding'},
                {'id': 'code_executor', 'type': 'tool', 'tool': 'code_executor'},
                {'id': 'debugger', 'type': 'agent', 'role': 'specialist', 'specialty': 'debugging'}
            ],
            'edges': [
                {'from': 'code_designer', 'to': 'code_generator'},
                {'from': 'code_generator', 'to': 'code_executor'},
                {'from': 'code_executor', 'to': 'debugger', 'condition': 'has_error'}
            ]
        }
