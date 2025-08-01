"""
通信策略模块
提供不同的Agent间通信策略实现
"""

from .base_strategy import CommunicationStrategy
from .direct_strategy import DirectCommunicationStrategy
from .broadcast_strategy import BroadcastCommunicationStrategy
from .network_strategy import NetworkCommunicationStrategy
from .discussion_strategy import DiscussionCommunicationStrategy
from .strategy_factory import CommunicationStrategyFactory
from .message_types import ChatMessage, MessageType, CommunicationMode

__all__ = [
    'CommunicationStrategy',
    'DirectCommunicationStrategy',
    'BroadcastCommunicationStrategy',
    'NetworkCommunicationStrategy',
    'DiscussionCommunicationStrategy',
    'CommunicationStrategyFactory',
    'ChatMessage',
    'MessageType',
    'CommunicationMode'
]
