"""
Agent工厂类
统一的Agent创建入口，解决多个创建入口的冗余问题
"""

import uuid
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .Agent import Agent, AgentRole
from .Models import ModelFactory, ModelConfig, ModelBase
from .Prompt import PromptManager
from ..ContextEngineer.context_manager import ContextManager


class AgentCreationMode(Enum):
    """Agent创建模式"""
    BASIC = "basic"          # 基础模式：最小配置
    STANDARD = "standard"    # 标准模式：完整配置
    WORKFLOW = "workflow"    # 工作流模式：包含工具注册
    DISCUSSION = "discussion" # 讨论模式：多Agent讨论优化


@dataclass
class AgentCreationConfig:
    """Agent创建配置"""
    # 基本信息
    agent_id: Optional[str] = None
    name: str = ""
    role: AgentRole = AgentRole.CHAT
    
    # 模型配置
    model_type: str = "openai"
    model_name: Optional[str] = None
    model_config: Optional[ModelConfig] = None
    
    # 提示词配置
    system_prompt: Optional[str] = None
    custom_prompt: Optional[str] = None
    
    # 创建模式
    creation_mode: AgentCreationMode = AgentCreationMode.STANDARD
    
    # 工具配置（工作流模式使用）
    enable_tools: bool = False
    tool_list: Optional[List[str]] = None
    
    # 讨论模式配置
    specialty_domains: Optional[List[str]] = None
    discussion_enabled: bool = False
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = None


class AgentFactory:
    """统一的Agent工厂类"""
    
    def __init__(self, config_manager=None):
        """
        初始化Agent工厂
        
        Args:
            config_manager: 配置管理器，用于读取API密钥等配置
        """
        self.config_manager = config_manager
        self._registered_tools: Dict[str, Any] = {}
        self._creation_stats = {
            'total_created': 0,
            'by_mode': {},
            'by_role': {},
            'failures': 0
        }
        
        # 注册默认工具
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        try:
            from ..Agentlib.Tools.calculator import CalculatorTool
            from ..Agentlib.Tools.file_tool import FileTool
            from ..Agentlib.Tools.web_search import WebSearchTool
            from ..Agentlib.Tools.code_executor import CodeExecutorTool
            
            self._registered_tools = {
                'calculator': CalculatorTool(),
                'file_tool': FileTool(),
                'web_search': WebSearchTool(),
                'code_executor': CodeExecutorTool()
            }
        except ImportError:
            # 如果工具模块不存在，跳过注册
            pass
    
    def create_agent(self, config: AgentCreationConfig) -> Agent:
        """
        创建Agent的统一入口
        
        Args:
            config: Agent创建配置
            
        Returns:
            Agent: 创建的Agent实例
            
        Raises:
            ValueError: 配置无效
            Exception: 创建失败
        """
        try:
            # 验证配置
            self._validate_config(config)
            
            # 生成Agent ID（如果未提供）
            if not config.agent_id:
                config.agent_id = str(uuid.uuid4())
            
            # 根据创建模式选择创建策略
            if config.creation_mode == AgentCreationMode.BASIC:
                agent = self._create_basic_agent(config)
            elif config.creation_mode == AgentCreationMode.STANDARD:
                agent = self._create_standard_agent(config)
            elif config.creation_mode == AgentCreationMode.WORKFLOW:
                agent = self._create_workflow_agent(config)
            elif config.creation_mode == AgentCreationMode.DISCUSSION:
                agent = self._create_discussion_agent(config)
            else:
                raise ValueError(f"Unknown creation mode: {config.creation_mode}")
            
            # 设置元数据
            self._set_agent_metadata(agent, config)
            
            # 更新统计信息
            self._update_creation_stats(config, success=True)
            
            return agent
            
        except Exception as e:
            self._update_creation_stats(config, success=False)
            raise Exception(f"Failed to create agent '{config.name}': {str(e)}")
    
    def _validate_config(self, config: AgentCreationConfig):
        """验证Agent创建配置"""
        if not config.name:
            raise ValueError("Agent name is required")
        
        if not isinstance(config.role, AgentRole):
            raise ValueError("Invalid agent role")
        
        if config.creation_mode == AgentCreationMode.WORKFLOW and config.role != AgentRole.TOOLS:
            if not config.enable_tools:
                # 工作流模式但不是工具Agent且未启用工具，给出警告
                pass
    
    def _create_basic_agent(self, config: AgentCreationConfig) -> Agent:
        """创建基础Agent（最小配置）"""
        return Agent(
            agent_id=config.agent_id,
            name=config.name,
            role=config.role
        )
    
    def _create_standard_agent(self, config: AgentCreationConfig) -> Agent:
        """创建标准Agent（完整配置）"""
        import logging
        logger = logging.getLogger(f"{__name__}.AgentFactory")

        logger.info(f"Creating standard agent '{config.name}' with role '{config.role.value}'")

        # 创建模型
        model = self._create_model(config)
        if model:
            logger.info(f"Agent '{config.name}' successfully connected to model: {type(model).__name__}")
        else:
            logger.warning(f"Agent '{config.name}' created without model connection - will use fallback responses")

        # 创建上下文管理器
        context_manager = ContextManager(f"{config.agent_id}_context")
        logger.debug(f"Created context manager for agent '{config.name}'")

        # 创建提示词管理器
        prompt_manager = PromptManager(f"{config.agent_id}_prompt")
        logger.debug(f"Created prompt manager for agent '{config.name}'")

        # 设置系统提示词
        if config.system_prompt:
            prompt_manager.set_system_prompt(config.system_prompt)
            logger.debug(f"Set system prompt for agent '{config.name}': {config.system_prompt[:50]}...")
        elif config.custom_prompt:
            prompt_manager.set_system_prompt(config.custom_prompt)
            logger.debug(f"Set custom prompt for agent '{config.name}': {config.custom_prompt[:50]}...")

        # 创建Agent
        agent = Agent(
            agent_id=config.agent_id,
            name=config.name,
            role=config.role,
            model=model,
            context_manager=context_manager,
            prompt_manager=prompt_manager
        )

        logger.info(f"Successfully created standard agent '{config.name}' (ID: {config.agent_id})")
        return agent
    
    def _create_workflow_agent(self, config: AgentCreationConfig) -> Agent:
        """创建工作流Agent（包含工具注册）"""
        # 先创建标准Agent
        agent = self._create_standard_agent(config)
        
        # 注册工具
        if config.role == AgentRole.TOOLS or config.enable_tools:
            self._register_tools_to_agent(agent, config.tool_list)
        
        return agent
    
    def _create_discussion_agent(self, config: AgentCreationConfig) -> Agent:
        """创建讨论Agent（多Agent讨论优化）"""
        # 先创建标准Agent
        agent = self._create_standard_agent(config)
        
        # 设置讨论模式特定配置
        if config.specialty_domains:
            agent.set_metadata(specialty_domains=config.specialty_domains)
        
        # 为讨论模式优化提示词
        if config.discussion_enabled:
            self._optimize_for_discussion(agent, config)
        
        return agent
    
    def _create_model(self, config: AgentCreationConfig) -> Optional[ModelBase]:
        """创建模型实例"""
        import logging
        logger = logging.getLogger(f"{__name__}.AgentFactory")

        logger.info(f"Creating model for agent '{config.name}' with platform '{config.model_type}' and model '{config.model_name}'")

        if config.model_config:
            # 使用提供的模型配置
            logger.info(f"Using provided model config for agent '{config.name}'")
            try:
                model = ModelFactory.create_model(config.model_type, config.model_config)
                logger.info(f"Successfully created model using provided config for agent '{config.name}'")
                return model
            except Exception as e:
                logger.error(f"Failed to create model using provided config for agent '{config.name}': {e}")
                return None

        # 从配置管理器获取API密钥
        api_key = self._get_api_key(config.model_type)
        logger.info(f"API key lookup for platform '{config.model_type}': {'Found' if api_key else 'Not found'}")

        if not api_key:
            logger.warning(f"No API key found for platform '{config.model_type}' for agent '{config.name}'. Agent will work in fallback mode.")
            logger.info(f"Available platforms with API keys: {self._get_available_platforms()}")
            return None  # 无API密钥时返回None，Agent将在基础模式下工作

        # 创建默认模型配置
        try:
            model_config = self._create_default_model_config(config.model_type, config.model_name, api_key)
            logger.info(f"Created model config for agent '{config.name}': model={model_config.model_name}, api_base={model_config.api_base}")

            model = ModelFactory.create_model(config.model_type, model_config)
            logger.info(f"Successfully created model for agent '{config.name}' using platform '{config.model_type}'")
            return model

        except Exception as e:
            logger.error(f"Failed to create model for agent '{config.name}' with platform '{config.model_type}': {e}")
            return None
    
    def _create_default_model_config(self, model_type: str, model_name: Optional[str], api_key: str) -> ModelConfig:
        """创建默认模型配置"""
        # 默认模型选择
        if not model_name:
            default_models = {
                'openai': 'gpt-3.5-turbo',
                'aihubmix': 'gpt-4o-mini',
                'zhipu': 'glm-4-flash-250414',  # 标准标识符
                'zhipuai': 'glm-4-flash-250414'  # 兼容性别名
            }
            model_name = default_models.get(model_type, 'gpt-3.5-turbo')

        # 默认API base
        api_bases = {
            'openai': 'https://api.openai.com/v1',
            'aihubmix': 'https://aihubmix.com/v1',
            'zhipu': 'https://open.bigmodel.cn/api/paas/v4',  # 标准标识符
            'zhipuai': 'https://open.bigmodel.cn/api/paas/v4'  # 兼容性别名
        }
        api_base = api_bases.get(model_type, 'https://api.openai.com/v1')
        
        return ModelConfig(
            model_name=model_name,
            api_key=api_key,
            api_base=api_base
        )
    
    def _get_api_key(self, model_type: str) -> Optional[str]:
        """获取API密钥"""
        import logging
        logger = logging.getLogger(f"{__name__}.AgentFactory")

        if self.config_manager:
            logger.debug(f"Using config manager to get API key for platform '{model_type}'")
            api_key = self.config_manager.get_api_key(model_type)
            if api_key:
                logger.debug(f"Found API key for platform '{model_type}' via config manager")
                return api_key
            else:
                logger.debug(f"No API key found for platform '{model_type}' via config manager")
        else:
            logger.warning("No config manager available for API key lookup")

        # 如果没有配置管理器，尝试从环境变量读取
        import os
        env_var_names = [
            f"{model_type.upper()}_API_KEY",
            f"API_KEY_{model_type.upper()}",
            f"{model_type.upper()}_KEY"
        ]

        for env_var in env_var_names:
            api_key = os.getenv(env_var)
            if api_key:
                logger.info(f"Found API key for platform '{model_type}' in environment variable '{env_var}'")
                return api_key

        logger.debug(f"No API key found for platform '{model_type}' in environment variables: {env_var_names}")
        return None

    def _get_available_platforms(self) -> List[str]:
        """获取有API密钥的可用平台列表"""
        available_platforms = []
        test_platforms = ['zhipu', 'aihubmix', 'openai']  # 移除zhipuai别名，避免重复

        for platform in test_platforms:
            if self._get_api_key(platform):
                available_platforms.append(platform)

        return available_platforms
    
    def _register_tools_to_agent(self, agent: Agent, tool_list: Optional[List[str]] = None):
        """为Agent注册工具"""
        tools_to_register = tool_list or list(self._registered_tools.keys())
        
        for tool_name in tools_to_register:
            if tool_name in self._registered_tools:
                tool = self._registered_tools[tool_name]
                agent.register_tool(tool_name, tool.execute, tool.description)
    
    def _optimize_for_discussion(self, agent: Agent, config: AgentCreationConfig):
        """为讨论模式优化Agent"""
        # 添加讨论模式的特殊元数据
        agent.set_metadata(
            discussion_enabled=True,
            discussion_role=config.role.value,
            creation_mode=config.creation_mode.value
        )
    
    def _set_agent_metadata(self, agent: Agent, config: AgentCreationConfig):
        """设置Agent元数据"""
        metadata = {
            'creation_mode': config.creation_mode.value,
            'model_type': config.model_type,
            'model_name': config.model_name,
            'creation_timestamp': time.time(),
            'factory_created': True
        }
        
        # 合并用户提供的元数据
        if config.metadata:
            metadata.update(config.metadata)
        
        agent.set_metadata(**metadata)
    
    def _update_creation_stats(self, config: AgentCreationConfig, success: bool):
        """更新创建统计信息"""
        if success:
            self._creation_stats['total_created'] += 1
            
            mode = config.creation_mode.value
            self._creation_stats['by_mode'][mode] = self._creation_stats['by_mode'].get(mode, 0) + 1
            
            role = config.role.value
            self._creation_stats['by_role'][role] = self._creation_stats['by_role'].get(role, 0) + 1
        else:
            self._creation_stats['failures'] += 1
    
    def get_creation_stats(self) -> Dict[str, Any]:
        """获取创建统计信息"""
        return self._creation_stats.copy()
    
    def register_tool(self, name: str, tool: Any):
        """注册新工具"""
        self._registered_tools[name] = tool
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self._registered_tools.keys())
