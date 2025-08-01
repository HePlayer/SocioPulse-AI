"""
广播通信策略
消息广播给所有Agent，但只有第一个响应的Agent会被处理
"""

import asyncio
from typing import List, Dict, Any
from .base_strategy import CommunicationStrategy, CommunicationContext, CommunicationResponse, CommunicationResult
from .message_types import ChatMessage, MessageType


class BroadcastCommunicationStrategy(CommunicationStrategy):
    """广播通信策略 - 消息广播给所有Agent"""
    
    def __init__(self):
        super().__init__("BroadcastCommunication")
    
    async def deliver_message(self, context: CommunicationContext) -> CommunicationResponse:
        """
        广播消息给所有Agent，但只处理第一个响应
        """
        target_agents = self.get_target_agents(context)
        
        if not target_agents:
            self.log_warning("No target agents found for broadcast communication")
            return CommunicationResponse(
                result=CommunicationResult.NO_RECIPIENTS,
                delivered_to=[],
                failed_deliveries=[],
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message="No target agents available"
            )
        
        self.log_info(f"Broadcasting message to {len(target_agents)} agents", {
            'target_agents': target_agents,
            'message_content': context.message.content[:100]
        })
        
        # 并发发送给所有Agent，但只取第一个成功的响应
        tasks = []
        for agent_id in target_agents:
            agent = context.available_agents.get(agent_id)
            if agent:
                task = self._process_agent(agent, context)
                tasks.append((agent_id, task))
        
        if not tasks:
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=target_agents,
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message="No valid agents to process"
            )
        
        try:
            # 等待第一个成功的响应
            delivered_to = []
            failed_deliveries = []
            responses = []
            
            # 使用as_completed来获取第一个完成的任务
            for agent_id, task in tasks:
                try:
                    result = await task
                    if result.get('success', True):
                        # 第一个成功的响应
                        agent = context.available_agents[agent_id]
                        response_message = ChatMessage(
                            sender_id=agent.component_id,
                            receiver_id=context.sender_id,
                            content=result.get('response', ''),
                            message_type=MessageType.TEXT,
                            metadata={
                                'agent_name': agent.name,
                                'agent_role': agent.role.value,
                                'communication_strategy': self.strategy_name,
                                'processing_time': result.get('processing_time', 0)
                            }
                        )
                        
                        delivered_to.append(agent_id)
                        responses.append(response_message)
                        
                        self.log_info(f"Agent {agent.name} responded successfully in broadcast mode")
                        
                        # 取消其他任务（如果需要的话）
                        for other_agent_id, other_task in tasks:
                            if other_agent_id != agent_id and not other_task.done():
                                other_task.cancel()
                        
                        return CommunicationResponse(
                            result=CommunicationResult.SUCCESS,
                            delivered_to=delivered_to,
                            failed_deliveries=failed_deliveries,
                            responses=responses,
                            metadata={
                                'strategy': self.strategy_name,
                                'responding_agent': agent.name,
                                'total_agents_contacted': len(target_agents)
                            }
                        )
                    else:
                        failed_deliveries.append(agent_id)
                        self.log_warning(f"Agent {agent_id} processing failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    failed_deliveries.append(agent_id)
                    self.log_error(f"Error processing agent {agent_id}", e)
            
            # 如果所有Agent都失败了
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=failed_deliveries,
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message="All agents failed to process the message"
            )
            
        except Exception as e:
            self.log_error("Error in broadcast communication", e)
            return CommunicationResponse(
                result=CommunicationResult.FAILURE,
                delivered_to=[],
                failed_deliveries=target_agents,
                responses=[],
                metadata={'strategy': self.strategy_name},
                error_message=str(e)
            )
    
    async def _process_agent(self, agent, context: CommunicationContext) -> Dict[str, Any]:
        """处理单个Agent"""
        input_data = {
            'user_input': context.message.content,
            'room_context': {
                'room_id': context.room_id,
                'room_name': context.room_name,
                'message_history': [msg.to_dict() for msg in context.message_history[-5:]],
                'communication_mode': 'broadcast'
            }
        }
        
        return await agent.think(input_data)
    
    def get_target_agents(self, context: CommunicationContext) -> List[str]:
        """
        获取目标Agent - 广播模式返回所有可用Agent
        """
        return list(context.available_agents.keys())
    
    def should_process_response(self, context: CommunicationContext) -> bool:
        """
        广播通信模式处理第一个响应
        """
        return True
