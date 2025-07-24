"""
MultiAI Item Package
核心功能模块集合
"""

# 导入主要组件
from .FlowTools import FlowEngine, FlowNode, NodeFactory
from .ContextEngineer import ContextManager, MemorySystem, RetrievalEngine
from .Agentlib import Agent, AgentRole, ModelFactory, PromptManager, ModelConfig
from .Workflow import WorkflowBuilder, WorkflowExecutor, WorkflowTemplates
from .ChatRoom import ChatRoom, ChatRoomConfig, CommunicationMode, ChatMessage

__version__ = "1.0.0"

__all__ = [
    # FlowTools
    'FlowEngine',
    'FlowNode', 
    'NodeFactory',
    
    # ContextEngineer
    'ContextManager',
    'MemorySystem',
    'RetrievalEngine',
    
    # Agentlib
    'Agent',
    'AgentRole',
    'ModelFactory',
    'ModelConfig',
    'PromptManager',
    
    # Workflow
    'WorkflowBuilder',
    'WorkflowExecutor',
    'WorkflowTemplates',
    
    # ChatRoom
    'ChatRoom',
    'ChatRoomConfig',
    'CommunicationMode',
    'ChatMessage'
]
