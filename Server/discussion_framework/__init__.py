"""
兼容层：Server.discussion_framework → comm.discussion_framework

为迁移后的讨论框架提供旧路径兼容，避免历史导入报错。
不要在新代码中继续使用 Server.discussion_framework，请改为：
    from comm.discussion_framework import ...
"""

from comm.discussion_framework import (
    ContinuousDiscussionController,
    DiscussionContext,
    ParallelSVREngine,
    AgentSVRComputer,
    SVRHandler,
    SVRDecision,
    DiscussionAction,
    DiscussionFrameworkManager,
    DiscussionEventInterface,
)

# 可选地转发 AgentIDManager（若有旧代码使用 Server.discussion_framework.agent_id_manager）
try:
    from comm.discussion_framework.agent_id_manager import AgentIDManager  # noqa: F401
    _has_agent_id_manager = True
except Exception:
    _has_agent_id_manager = False

__all__ = [
    'ContinuousDiscussionController',
    'DiscussionContext',
    'ParallelSVREngine',
    'AgentSVRComputer',
    'SVRHandler',
    'SVRDecision',
    'DiscussionAction',
    'DiscussionFrameworkManager',
    'DiscussionEventInterface',
]

if _has_agent_id_manager:
    __all__.append('AgentIDManager')

