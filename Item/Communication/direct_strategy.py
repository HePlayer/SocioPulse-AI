"""
直接通信策略
用于单Agent对话模式，消息直接发送给指定的Agent
"""

from typing import List, Dict, Any
from .base_strategy import CommunicationStrategy, CommunicationContext, CommunicationResponse, CommunicationResult
from .message_types import ChatMessage, MessageType


class DirectCommunicationStrategy(CommunicationStrategy):
    """直接通信策略 - 用于单Agent模式"""
    
    def __init__(self):
        super().__init__("DirectCommunication")
    
    async def deliver_message(self, context: CommunicationContext) -> CommunicationResponse:
        """
        直接投递消息给目标Agent
        """
        target_agents = self.get_target_agents(context)
        
        if not target_agents:
            self.log_warning("No target agents found for direct communication")
            return CommunicationResponse(
                result=CommunicationResult.NO_RECIPIENTS,
                delivered_to=[],
                failed_deliveries=[],
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message="No target agents available"
            )
        
        # 直接通信只处理第一个目标Agent
        target_agent_id = target_agents[0]
        target_agent = context.available_agents.get(target_agent_id)
        
        if not target_agent:
            self.log_error(f"Target agent {target_agent_id} not found in available agents")
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=[target_agent_id],
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message=f"Agent {target_agent_id} not available"
            )
        
        try:
            self.log_info(f"Delivering message to agent {target_agent.name}", {
                'target_agent_id': target_agent_id,
                'message_content': context.message.content[:100]
            })
            
            # 构建Agent输入数据
            input_data = {
                'user_input': context.message.content,
                'room_context': {
                    'room_id': context.room_id,
                    'room_name': context.room_name,
                    'message_history': [msg.to_dict() for msg in context.message_history[-5:]],
                    'communication_mode': 'direct'
                }
            }
            
            # 调用Agent处理
            result = await target_agent.think(input_data)
            
            if result.get('success', True):
                # 创建响应消息
                response_message = ChatMessage(
                    sender_id=target_agent.component_id,
                    receiver_id=context.sender_id,
                    content=result.get('response', ''),
                    message_type=MessageType.TEXT,
                    metadata={
                        'agent_name': target_agent.name,
                        'agent_role': target_agent.role.value,
                        'communication_strategy': self.strategy_name,
                        'processing_time': result.get('processing_time', 0)
                    }
                )
                
                self.log_info(f"Agent {target_agent.name} responded successfully")
                
                return CommunicationResponse(
                    result=CommunicationResult.SUCCESS,
                    delivered_to=[target_agent_id],
                    failed_deliveries=[],
                    responses=[response_message],
                    metadata={
                        'strategy': self.strategy_name,
                        'agent_name': target_agent.name,
                        'processing_time': result.get('processing_time', 0)
                    }
                )
            else:
                self.log_warning(f"Agent {target_agent.name} processing failed: {result.get('error', 'Unknown error')}")
                return CommunicationResponse(
                    result=CommunicationResult.FAILURE,
                    delivered_to=[],
                    failed_deliveries=[target_agent_id],
                    responses=[],
                    metadata={'strategy': self.strategy_name},
                    error_message=result.get('error', 'Agent processing failed')
                )
                
        except Exception as e:
            self.log_error(f"Error delivering message to agent {target_agent.name}", e)
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=[target_agent_id],
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message=str(e)
            )
    
    def get_target_agents(self, context: CommunicationContext) -> List[str]:
        """
        获取目标Agent - 直接通信模式
        优先使用消息指定的接收者，否则选择第一个可用Agent
        """
        # 如果消息指定了接收者
        if context.message.receiver_id and context.message.receiver_id in context.available_agents:
            return [context.message.receiver_id]
        
        # 否则选择第一个可用的Agent
        if context.available_agents:
            return [list(context.available_agents.keys())[0]]
        
        return []
    
    def should_process_response(self, context: CommunicationContext) -> bool:
        """
        直接通信模式总是处理响应
        """
        return True
