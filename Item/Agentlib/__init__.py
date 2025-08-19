"""
Agentlib - Agent库模块
提供Agent基类、模型调用、提示词管理和工具集
"""

from .Agent import Agent, AgentRole, AgentStatus, AgentMessage
from .Models import ModelBase, OpenAIModel, AiHubMixModel, ZhipuAIModel, ModelFactory, ModelConfig
from .Prompt import PromptManager, PromptTemplate
from .agent_factory import AgentFactory, AgentCreationConfig, AgentCreationMode
from .connection_pool import ModelConnectionPool, get_connection_pool, cleanup_connection_pool

__all__ = [
    'Agent',
    'AgentRole',
    'AgentStatus',
    'AgentMessage',
    'ModelBase',
    'OpenAIModel',
    'AiHubMixModel',
    'ZhipuAIModel',
    'ModelFactory',
    'ModelConfig',
    'PromptManager',
    'PromptTemplate',
    'AgentFactory',
    'AgentCreationConfig',
    'AgentCreationMode',
    'ModelConnectionPool',
    'get_connection_pool',
    'cleanup_connection_pool'
]
