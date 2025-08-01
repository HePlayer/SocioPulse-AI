"""
网络通信策略
支持Agent间的网络式通信，为多Agent协作提供基础
"""

import asyncio
from typing import List, Dict, Any
from .base_strategy import CommunicationStrategy, CommunicationContext, CommunicationResponse, CommunicationResult
from .message_types import ChatMessage, MessageType


class NetworkCommunicationStrategy(CommunicationStrategy):
    """网络通信策略 - 支持Agent间的复杂交互"""
    
    def __init__(self):
        super().__init__("NetworkCommunication")
    
    async def deliver_message(self, context: CommunicationContext) -> CommunicationResponse:
        """
        网络式投递消息，支持多Agent响应
        """
        target_agents = self.get_target_agents(context)
        
        if not target_agents:
            self.log_warning("No target agents found for network communication")
            return CommunicationResponse(
                result=CommunicationResult.NO_RECIPIENTS,
                delivered_to=[],
                failed_deliveries=[],
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message="No target agents available"
            )
        
        self.log_info(f"Network communication to {len(target_agents)} agents", {
            'target_agents': target_agents,
            'message_content': context.message.content[:100]
        })
        
        # 并发处理所有Agent
        tasks = []
        for agent_id in target_agents:
            agent = context.available_agents.get(agent_id)
            if agent:
                task = self._process_agent_with_context(agent, context)
                tasks.append((agent_id, agent, task))
        
        if not tasks:
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=target_agents,
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message="No valid agents to process"
            )
        
        # 等待所有任务完成
        delivered_to = []
        failed_deliveries = []
        responses = []
        
        try:
            # 使用gather等待所有任务，但允许部分失败
            results = await asyncio.gather(
                *[task for _, _, task in tasks],
                return_exceptions=True
            )
            
            for i, (agent_id, agent, _) in enumerate(tasks):
                result = results[i]
                
                if isinstance(result, Exception):
                    failed_deliveries.append(agent_id)
                    self.log_error(f"Agent {agent.name} processing failed with exception", result)
                elif result.get('success', True):
                    # 成功处理
                    response_message = ChatMessage(
                        sender_id=agent.component_id,
                        receiver_id=context.sender_id,
                        content=result.get('response', ''),
                        message_type=MessageType.TEXT,
                        metadata={
                            'agent_name': agent.name,
                            'agent_role': agent.role.value,
                            'communication_strategy': self.strategy_name,
                            'processing_time': result.get('processing_time', 0),
                            'network_position': i  # Agent在网络中的位置
                        }
                    )
                    
                    delivered_to.append(agent_id)
                    responses.append(response_message)
                    
                    self.log_info(f"Agent {agent.name} responded successfully in network mode")
                else:
                    failed_deliveries.append(agent_id)
                    self.log_warning(f"Agent {agent.name} processing failed: {result.get('error', 'Unknown error')}")
            
            # 确定整体结果
            if delivered_to:
                if failed_deliveries:
                    result_status = CommunicationResult.PARTIAL_SUCCESS
                else:
                    result_status = CommunicationResult.SUCCESS
            else:
                result_status = CommunicationResult.FAILURE
            
            return CommunicationResponse(
                result=result_status,
                delivered_to=delivered_to,
                failed_deliveries=failed_deliveries,
                responses=responses,
                metadata={
                    'strategy': self.strategy_name,
                    'total_agents': len(target_agents),
                    'successful_agents': len(delivered_to),
                    'failed_agents': len(failed_deliveries)
                }
            )
            
        except Exception as e:
            self.log_error("Error in network communication", e)
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=target_agents,
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message=str(e)
            )
    
    async def _process_agent_with_context(self, agent, context: CommunicationContext) -> Dict[str, Any]:
        """处理单个Agent，提供网络上下文"""
        # 为网络通信提供更丰富的上下文
        input_data = {
            'user_input': context.message.content,
            'room_context': {
                'room_id': context.room_id,
                'room_name': context.room_name,
                'message_history': [msg.to_dict() for msg in context.message_history[-10:]],  # 更多历史
                'communication_mode': 'network',
                'available_agents': [aid for aid in context.available_agents.keys() if aid != agent.component_id],
                'network_context': {
                    'total_agents': len(context.available_agents),
                    'agent_roles': {aid: ag.role.value for aid, ag in context.available_agents.items()},
                    'collaboration_mode': True
                }
            }
        }
        
        return await agent.think(input_data)
    
    def get_target_agents(self, context: CommunicationContext) -> List[str]:
        """
        获取目标Agent - 网络模式
        如果指定了接收者，只发送给指定Agent；否则发送给所有Agent
        """
        if context.message.receiver_id and context.message.receiver_id in context.available_agents:
            return [context.message.receiver_id]
        
        # 网络模式默认发送给所有Agent
        return list(context.available_agents.keys())
    
    def should_process_response(self, context: CommunicationContext) -> bool:
        """
        网络通信模式处理所有响应
        """
        return True
