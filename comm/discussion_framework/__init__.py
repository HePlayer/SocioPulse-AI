"""
讨论框架（迁移后位置）
从 Server.discussion_framework 迁移至 comm.discussion_framework
"""
from .discussion_framework.continuous_controller import ContinuousDiscussionController
from .discussion_framework.discussion_context import DiscussionContext
from .discussion_framework.parallel_svr_engine import ParallelSVREngine, AgentSVRComputer
from .discussion_framework.svr_handler import SVRHandler, SVRDecision, DiscussionAction
from .discussion_framework.framework_manager import DiscussionFrameworkManager
from .discussion_framework.event_interface import DiscussionEventInterface

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

