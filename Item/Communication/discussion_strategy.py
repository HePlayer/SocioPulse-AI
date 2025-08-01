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
        当前实现：选择第一个Agent开始讨论，为后续SVR算法预留接口
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
        
        self.log_info(f"Starting discussion with {len(target_agents)} agents", {
            'target_agents': target_agents,
            'message_content': context.message.content[:100]
        })
        
        # 当前实现：选择第一个Agent开始讨论
        # 后续将被SVR算法替换
        first_agent_id = target_agents[0]
        first_agent = context.available_agents.get(first_agent_id)
        
        if not first_agent:
            self.log_error(f"First agent {first_agent_id} not found in available agents")
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=[first_agent_id],
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message=f"Agent {first_agent_id} not available"
            )
        
        try:
            # 构建讨论上下文
            input_data = {
                'user_input': context.message.content,
                'room_context': {
                    'room_id': context.room_id,
                    'room_name': context.room_name,
                    'message_history': [msg.to_dict() for msg in context.message_history[-5:]],
                    'discussion_mode': True,
                    'available_agents': [agent.name for agent in context.available_agents.values()],
                    'discussion_context': {
                        'total_participants': len(target_agents),
                        'discussion_turn': 1,
                        'discussion_status': 'starting'
                    }
                }
            }
            
            # 调用Agent处理
            result = await first_agent.think(input_data)
            
            if result.get('success', True):
                # 创建讨论响应消息
                response_message = ChatMessage(
                    sender_id=first_agent.component_id,
                    receiver_id=context.sender_id,
                    content=result.get('response', ''),
                    message_type=MessageType.TEXT,
                    metadata={
                        'agent_name': first_agent.name,
                        'agent_role': first_agent.role.value,
                        'communication_strategy': self.strategy_name,
                        'discussion_mode': True,
                        'discussion_turn': 1,
                        'discussion_status': 'started',
                        'turn_type': TurnType.INITIAL.value,
                        'round_number': 1,
                        'processing_time': result.get('processing_time', 0),
                        # 为SVR算法预留字段
                        'svr_values': {
                            'stop_value': 0,
                            'value_score': 50,
                            'repeat_risk': 0
                        },
                        # 讨论上下文
                        'discussion_context': {
                            'total_participants': len(target_agents),
                            'is_first_turn': True,
                            'responding_to_user': True
                        }
                    }
                )
                
                self.log_info(f"Agent {first_agent.name} started discussion successfully")
                
                return CommunicationResponse(
                    result=CommunicationResult.SUCCESS,
                    delivered_to=[first_agent_id],
                    failed_deliveries=[],
                    responses=[response_message],
                    metadata={
                        'strategy': self.strategy_name,
                        'discussion_mode': True,
                        'discussion_status': 'started',
                        'starting_agent': first_agent.name,
                        'total_participants': len(target_agents),
                        # 为ContinuousDiscussionController预留字段
                        'next_turn_ready': True,
                        'discussion_session_id': f"{context.room_id}_{context.message.id}",
                        # 传递用户输入以供连续讨论框架使用
                        'user_input': context.message.content,
                        'room_context': {
                            'room_id': context.room_id,
                            'room_name': context.room_name,
                            'available_agents': list(context.available_agents.keys()),
                            'message_history_count': len(context.message_history)
                        },
                        # 连续讨论触发标志
                        'trigger_continuous_discussion': True
                    }
                )
            else:
                self.log_warning(f"Agent {first_agent.name} failed to start discussion: {result.get('error', 'Unknown error')}")
                return CommunicationResponse(
                    result=CommunicationResult.FAILURE,
                    delivered_to=[],
                    failed_deliveries=[first_agent_id],
                    responses=[],
                    metadata={'strategy': self.strategy_name},
                    error_message=result.get('error', 'Discussion start failed')
                )
                
        except Exception as e:
            self.log_error(f"Error starting discussion with agent {first_agent.name}", e)
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=[first_agent_id],
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message=str(e)
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
