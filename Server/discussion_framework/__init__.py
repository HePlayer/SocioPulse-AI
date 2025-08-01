"""
多Agent讨论框架模块

提供连续循环架构的多Agent讨论系统，包括：
- 并行SVR计算引擎
- 连续讨论控制器
- 实时事件系统
- 前端兼容性接口
"""

from .continuous_controller import ContinuousDiscussionController
from .discussion_context import DiscussionContext
from .parallel_svr_engine import ParallelSVREngine, AgentSVRComputer
from .svr_handler import SVRHandler, SVRDecision, DiscussionAction
from .framework_manager import DiscussionFrameworkManager
from .event_interface import DiscussionEventInterface

__all__ = [
    'ContinuousDiscussionController',
    'DiscussionContext', 
    'ParallelSVREngine',
    'AgentSVRComputer',
    'SVRHandler',
    'SVRDecision',
    'DiscussionAction',
    'DiscussionFrameworkManager',
    'DiscussionEventInterface'
]

__version__ = '1.0.0'
