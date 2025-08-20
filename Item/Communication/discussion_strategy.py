"""
讨论通信策略
专门为多Agent群聊讨论模式设计的通信策略
"""

from typing import List, Dict, Any
from .base_strategy import CommunicationStrategy, CommunicationContext, CommunicationResponse, CommunicationResult
from .message_types import ChatMessage, MessageType
from .discussion_types import TurnType


class DiscussionCommunicationStrategy(CommunicationStrategy):
    """讨论通信策略 - 专为多Agent讨论模式设计"""
    
    def __init__(self):
        super().__init__("DiscussionCommunication")
    
    async def deliver_message(self, context: CommunicationContext) -> CommunicationResponse:
        """
        讨论模式的消息投递
        新逻辑：取消"首发"，不立即调用任何Agent。直接启动连续讨论框架，由SVR在每轮动态选择最合适的Agent发言。
        """
        target_agents = self.get_target_agents(context)

        if not target_agents:
            self.log_warning("No target agents found for discussion communication")
            return CommunicationResponse(
                result=CommunicationResult.NO_RECIPIENTS,
                delivered_to=[],
                failed_deliveries=[],
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message="No target agents available for discussion"
            )

        self.log_info(f"Preparing continuous discussion with {len(target_agents)} agents (no immediate first reply)", {
            'target_agents': target_agents,
            'message_content': context.message.content[:100]
        })

        # 准备启动连续讨论所需的元数据
        discussion_metadata = {
            'strategy': self.strategy_name,
            'discussion_mode': True,
            'discussion_status': 'started',
            'total_participants': len(target_agents),
            'next_turn_ready': True,
            'discussion_session_id': f"{context.room_id}_{context.message.id}",
            'user_input': context.message.content,
            'room_context': {
                'room_id': context.room_id,
                'room_name': context.room_name,
                'available_agents': list(context.available_agents.keys()),
                'message_history_count': len(context.message_history)
            },
            'trigger_continuous_discussion': True
        }

        # 不返回任何同步响应，由上层基于元数据触发连续讨论框架
        return CommunicationResponse(
            result=CommunicationResult.SUCCESS,
            delivered_to=[],
            failed_deliveries=[],
            responses=[],
            metadata=discussion_metadata
        )
    
    def get_target_agents(self, context: CommunicationContext) -> List[str]:
        """
        获取讨论参与者 - 所有可用Agent
        """
        return list(context.available_agents.keys())
    
    def should_process_response(self, context: CommunicationContext) -> bool:
        """
        讨论模式需要特殊的响应处理
        """
        return True
    
    def get_next_speaker_candidates(self, context: CommunicationContext) -> List[str]:
        """
        获取下一轮发言候选者
        为SVR算法预留的接口
        """
        # 当前简单实现：返回所有Agent
        # 后续将被SVR算法的Agent选择逻辑替换
        return self.get_target_agents(context)
    
    def should_continue_discussion(self, context: CommunicationContext, current_turn: int) -> bool:
        """
        判断是否应该继续讨论
        为SVR算法预留的接口
        """
        # 当前简单实现：基于轮次数量
        # 后续将被SVR算法的停止条件替换
        max_turns = context.metadata.get('max_discussion_turns', 10)
        return current_turn < max_turns
