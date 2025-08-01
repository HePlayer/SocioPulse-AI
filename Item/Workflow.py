"""
Workflow - 预定义的工作流程
基于FlowTools实现的标准流程模板
"""

from typing import Dict, List, Any, Optional
import asyncio

from .FlowTools import FlowEngine, NodeFactory
from .Agentlib import Agent, AgentRole, ModelFactory, ModelConfig
from .Agentlib.agent_factory import AgentFactory, AgentCreationConfig, AgentCreationMode
from .Agentlib.config_manager import ConfigManager
from .Agentlib.Tools import CalculatorTool, FileTool, WebSearchTool, CodeExecutorTool


class WorkflowBuilder:
    """工作流程构建器 - 使用统一的AgentFactory"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        import logging
        self.logger = logging.getLogger(f"{__name__}.WorkflowBuilder")

        self.node_factory = NodeFactory("workflow_factory")
        self.registered_agents: Dict[str, Agent] = {}

        # 初始化配置管理器和Agent工厂
        self.config_manager = config_manager or ConfigManager()
        self.agent_factory = AgentFactory(self.config_manager)

        self.logger.info("WorkflowBuilder initialized with ConfigManager")
        self.logger.debug(f"ConfigManager config file path: {self.config_manager.config_file_path}")

        # 注册默认工具到Agent工厂
        self._register_default_tools_to_factory()
    
    def _register_default_tools_to_factory(self):
        """注册默认工具到Agent工厂"""
        try:
            self.agent_factory.register_tool('calculator', CalculatorTool())
            self.agent_factory.register_tool('file_tool', FileTool())
            self.agent_factory.register_tool('web_search', WebSearchTool())
            self.agent_factory.register_tool('code_executor', CodeExecutorTool())
        except ImportError:
            # 如果工具模块不存在，跳过注册
            pass
    
    def create_agent(self,
                    agent_id: str,
                    name: str,
                    role: AgentRole,
                    model_type: str = "zhipu",  # 改为默认使用zhipu（有API密钥）
                    model_config: Optional[ModelConfig] = None,
                    model_name: Optional[str] = None,
                    system_prompt: Optional[str] = None) -> Agent:
        """创建Agent - 使用统一的AgentFactory"""

        self.logger.info(f"Creating agent '{name}' (ID: {agent_id}) with platform '{model_type}' and model '{model_name}'")

        # 验证平台是否有API密钥
        available_platforms = self._get_available_platforms()
        if model_type not in available_platforms:
            self.logger.warning(f"Platform '{model_type}' not in available platforms: {available_platforms}")
            if available_platforms:
                # 使用第一个可用平台（已按优先级排序）
                original_model_type = model_type
                model_type = available_platforms[0]

                # 同时切换到兼容的模型名称
                if not model_name or not self._validate_model_platform_compatibility(model_type, model_name):
                    model_name = self._get_default_model_for_platform(model_type)

                self.logger.info(f"Switched from '{original_model_type}' to '{model_type}' with model '{model_name}'")
            else:
                self.logger.error("No platforms with API keys available!")

        # 创建Agent配置
        config = AgentCreationConfig(
            agent_id=agent_id,
            name=name,
            role=role,
            model_type=model_type,
            model_config=model_config,
            model_name=model_name,
            system_prompt=system_prompt,
            creation_mode=AgentCreationMode.WORKFLOW,
            enable_tools=(role == AgentRole.TOOLS)
        )

        # 使用AgentFactory创建Agent
        try:
            agent = self.agent_factory.create_agent(config)
            self.registered_agents[agent_id] = agent
            self.logger.info(f"Successfully created agent '{name}' with model connection: {agent.model is not None}")
            return agent
        except Exception as e:
            self.logger.error(f"Failed to create agent '{name}' with model type '{model_type}': {str(e)}")
            raise Exception(f"Failed to create agent '{name}' with model type '{model_type}': {str(e)}")

    def _get_available_platforms(self) -> List[str]:
        """获取有API密钥的可用平台列表，按优先级排序"""
        # 读取默认平台配置
        default_platform = self.config_manager.get_config('models.default_platform', 'zhipu')

        available_platforms = []
        test_platforms = ['zhipu', 'aihubmix', 'openai']  # 移除zhipuai别名，避免重复

        # 首先检查默认平台
        if default_platform in test_platforms:
            api_key = self.config_manager.get_api_key(default_platform)
            if api_key and api_key.strip():
                available_platforms.append(default_platform)
                self.logger.debug(f"Default platform '{default_platform}' is available")

        # 然后检查其他平台
        for platform in test_platforms:
            if platform != default_platform:
                api_key = self.config_manager.get_api_key(platform)
                if api_key and api_key.strip():
                    available_platforms.append(platform)

        self.logger.debug(f"Available platforms with API keys (prioritized): {available_platforms}")
        return available_platforms

    def _validate_model_platform_compatibility(self, platform: str, model_name: str) -> bool:
        """验证模型与平台的兼容性"""
        platform_models = {
            'zhipu': ['glm-4', 'glm-4-plus', 'glm-3-turbo', 'glm-4-flash-250414'],
            'aihubmix': ['gpt-4o-mini', 'gpt-4o-search-preview', 'gpt-4o-mini-search-preview'],
            'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo']
        }

        compatible_models = platform_models.get(platform, [])
        is_compatible = model_name in compatible_models

        if not is_compatible:
            self.logger.warning(f"Model '{model_name}' is not compatible with platform '{platform}'. Compatible models: {compatible_models}")

        return is_compatible

    def _get_default_model_for_platform(self, platform: str) -> str:
        """获取平台的默认模型"""
        default_models = {
            'zhipu': 'glm-4-flash-250414',  # 免费模型
            'aihubmix': 'gpt-4o-mini',
            'openai': 'gpt-3.5-turbo'
        }

        default_model = default_models.get(platform, 'gpt-3.5-turbo')
        self.logger.debug(f"Using default model '{default_model}' for platform '{platform}'")
        return default_model



    
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
