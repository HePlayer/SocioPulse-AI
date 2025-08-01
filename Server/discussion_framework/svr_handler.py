"""
SVR处理器
处理并行SVR结果并做出讨论流程决策
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .parallel_svr_engine import ParallelSVRResult, AgentSVRResult
from .discussion_context import DiscussionContext
from Item.Agentlib import Agent


class DiscussionAction(Enum):
    """可能的讨论行动"""
    CONTINUE = "continue"
    STOP = "stop"
    PAUSE = "pause"
    REDIRECT = "redirect"
    SUMMARIZE = "summarize"


@dataclass
class SVRDecision:
    """SVR处理器做出的决策"""
    action: DiscussionAction
    selected_agent_id: Optional[str]
    selected_agent_name: Optional[str]
    confidence: float
    reasoning: List[str]
    metadata: Dict[str, Any]


class SVRHandler:
    """处理SVR结果并做出讨论流程决策"""
    
    def __init__(self,
                 stop_threshold: float = 0.8,
                 quality_threshold: float = 30.0):
        self.stop_threshold = stop_threshold
        self.quality_threshold = quality_threshold

        # 🔧 关键修复：添加logger初始化，解决AttributeError
        self.logger = logging.getLogger(f"{__name__}.SVRHandler")

        # 决策历史
        self.decision_history: List[SVRDecision] = []

        # 简化的自适应阈值 - 移除consensus相关
        self.adaptive_thresholds = {
            'stop_threshold': stop_threshold,
            'quality_threshold': quality_threshold
        }
        
        # 性能跟踪
        self.decision_accuracy_history = []
    
    async def process_svr_results(self, 
                                 svr_result: ParallelSVRResult,
                                 context: DiscussionContext,
                                 participants: Dict[str, Agent]) -> SVRDecision:
        """
        处理SVR结果并决定下一步行动
        
        Args:
            svr_result: 并行SVR计算的结果
            context: 当前讨论上下文
            participants: 可用的Agent
            
        Returns:
            SVRDecision: 关于下一步行动的决策
        """
        
        # 提取关键指标
        global_metrics = svr_result.global_svr_metrics
        agent_results = svr_result.agent_results

        # 只使用S值平均进行决策
        global_stop_average = global_metrics.get('global_stop_average', 0.0)
        discussion_quality = global_metrics.get('discussion_quality', 50.0)

        # 简化的决策逻辑
        decision = await self._make_decision_simplified(
            global_stop_average, discussion_quality, agent_results, context, participants
        )
        
        # 记录决策
        self.decision_history.append(decision)
        if len(self.decision_history) > 100:  # 保留最近100个决策
            self.decision_history = self.decision_history[-100:]
        
        # 更新自适应阈值
        await self._update_adaptive_thresholds(decision, svr_result)
        
        return decision
    
    async def _make_decision(self, 
                           global_stop: float,
                           consensus_level: float,
                           discussion_quality: float,
                           agent_results: Dict[str, AgentSVRResult],
                           context: DiscussionContext,
                           participants: Dict[str, Agent]) -> SVRDecision:
        """核心决策逻辑"""
        
        reasoning = []
        confidence = 0.8  # 基础置信度
        
        # 检查停止条件 - 移除共识检查
        if global_stop >= self.adaptive_thresholds['stop_threshold']:
            reasoning.append(f"全局停止值 ({global_stop:.2f}) 超过阈值 ({self.adaptive_thresholds['stop_threshold']:.2f})")

            return SVRDecision(
                action=DiscussionAction.STOP,
                selected_agent_id=None,
                selected_agent_name=None,
                confidence=0.9,
                reasoning=reasoning,
                metadata={
                    'global_stop': global_stop,
                    'stop_reason': 'threshold_exceeded',
                    'decision_basis': 'legacy_stop_value'
                }
            )
        
        # 移除基于质量的干预机制 - 使用简化的V值选择
        # 注意：这个方法已被_make_decision_simplified替代，但保持兼容性
        
        # 继续讨论 - 选择最佳Agent
        selected_agent = await self._select_next_speaker(agent_results, context, participants)
        
        if selected_agent:
            reasoning.append(f"基于SVR分析选择 {selected_agent[1]}")
            reasoning.append(f"Agent综合分数: {agent_results[selected_agent[0]].svr_values.get('composite_score', 0):.1f}")
            
            return SVRDecision(
                action=DiscussionAction.CONTINUE,
                selected_agent_id=selected_agent[0],
                selected_agent_name=selected_agent[1],
                confidence=0.8,
                reasoning=reasoning,
                metadata={
                    'selection_method': 'svr_based',
                    'agent_svr_values': agent_results[selected_agent[0]].svr_values
                }
            )
        else:
            # 后备 - 暂停讨论
            reasoning.append("未找到合适的Agent继续")
            
            return SVRDecision(
                action=DiscussionAction.PAUSE,
                selected_agent_id=None,
                selected_agent_name=None,
                confidence=0.5,
                reasoning=reasoning,
                metadata={'pause_reason': 'no_suitable_agent'}
            )

    async def _make_decision_simplified(self,
                                      global_stop_average: float,
                                      discussion_quality: float,
                                      agent_results: Dict[str, AgentSVRResult],
                                      context: DiscussionContext,
                                      participants: Dict[str, Agent]) -> SVRDecision:
        """简化的决策逻辑 - 只基于S值平均"""

        reasoning = []
        confidence = 0.8

        # 唯一的停止条件：S值平均超过阈值
        if global_stop_average >= self.adaptive_thresholds['stop_threshold']:
            reasoning.append(f"全局停止平均值 ({global_stop_average:.3f}) 超过阈值 ({self.adaptive_thresholds['stop_threshold']:.3f})")

            return SVRDecision(
                action=DiscussionAction.STOP,
                selected_agent_id=None,
                selected_agent_name=None,
                confidence=0.9,
                reasoning=reasoning,
                metadata={
                    'global_stop_average': global_stop_average,
                    'stop_reason': 's_value_threshold_exceeded',
                    'decision_basis': 's_value_only'
                }
            )

        # 移除质量干预机制 - 不再基于discussion_quality进行干预
        # 直接基于V值选择Agent
        selected_agent = await self._select_next_speaker(agent_results, context, participants)

        if selected_agent:
            reasoning.append(f"基于V值选择 {selected_agent[1]}")
            reasoning.append(f"全局停止平均值: {global_stop_average:.3f} (低于阈值 {self.adaptive_thresholds['stop_threshold']:.3f})")

            # 获取选择的Agent的V值用于记录
            selected_v_value = 0.0
            if agent_results and selected_agent[0] in agent_results:
                selected_v_value = agent_results[selected_agent[0]].svr_values.get('value_score', 0.0)

            return SVRDecision(
                action=DiscussionAction.CONTINUE,
                selected_agent_id=selected_agent[0],
                selected_agent_name=selected_agent[1],
                confidence=0.8,
                reasoning=reasoning,
                metadata={
                    'selection_method': 'highest_v_value',
                    'selected_v_value': selected_v_value,
                    'global_stop_average': global_stop_average,
                    'decision_basis': 'v_value_only'
                }
            )
        else:
            # 后备 - 暂停讨论
            reasoning.append("未找到合适的Agent继续")

            return SVRDecision(
                action=DiscussionAction.PAUSE,
                selected_agent_id=None,
                selected_agent_name=None,
                confidence=0.5,
                reasoning=reasoning,
                metadata={
                    'pause_reason': 'no_suitable_agent',
                    'global_stop_average': global_stop_average,
                    'decision_basis': 'v_value_selection_failed'
                }
            )

    async def _select_next_speaker(self,
                                  agent_results: Dict[str, AgentSVRResult],
                                  context: DiscussionContext,
                                  participants: Dict[str, Agent]) -> Optional[Tuple[str, str]]:
        """纯V值选择机制：选择V值最高的Agent"""

        self.logger.info(f"开始基于V值的Agent选择:")
        self.logger.info(f"  agent_results数量: {len(agent_results) if agent_results else 0}")
        self.logger.info(f"  participants数量: {len(participants)}")

        # 如果没有agent_results，从所有participants中选择（冷启动处理）
        if not agent_results:
            self.logger.info("agent_results为空，从所有participants中选择第一个Agent")
            if participants:
                first_agent_id = list(participants.keys())[0]
                first_agent_name = participants[first_agent_id].name
                self.logger.info(f"✓ 冷启动选择: {first_agent_name} (ID: {first_agent_id})")
                return (first_agent_id, first_agent_name)
            else:
                self.logger.error("participants也为空，无法选择Agent")
                return None

        # 收集所有Agent的V值
        agent_v_values = []

        for agent_id, result in agent_results.items():
            if agent_id in participants:
                v_value = result.svr_values.get('value_score', 0.0)
                agent_name = participants[agent_id].name
                agent_v_values.append((agent_id, agent_name, v_value))
                self.logger.debug(f"  Agent {agent_name} (ID: {agent_id}): V值={v_value:.1f}")
            else:
                self.logger.warning(f"  跳过Agent {agent_id}: 不在participants中")

        # 如果没有匹配的Agent，从participants中选择
        if not agent_v_values:
            self.logger.warning("没有匹配的Agent，从participants中选择第一个")
            if participants:
                first_agent_id = list(participants.keys())[0]
                first_agent_name = participants[first_agent_id].name
                self.logger.info(f"✓ 后备选择: {first_agent_name} (ID: {first_agent_id})")
                return (first_agent_id, first_agent_name)
            else:
                self.logger.error("participants为空，无法选择Agent")
                return None

        # 按V值排序（降序）
        agent_v_values.sort(key=lambda x: x[2], reverse=True)

        # 记录排序结果
        self.logger.info(f"V值排序结果:")
        for i, (agent_id, agent_name, v_value) in enumerate(agent_v_values[:3]):  # 显示前3名
            self.logger.info(f"  {i+1}. {agent_name}: V值={v_value:.1f}")

        # 选择V值最高的Agent
        selected_agent_id, selected_agent_name, highest_v_value = agent_v_values[0]

        self.logger.info(f"✓ 选择V值最高的Agent: {selected_agent_name} (V值: {highest_v_value:.1f})")

        # 验证选择的Agent在participants中
        if selected_agent_id in participants:
            self.logger.debug(f"  验证通过: Agent {selected_agent_id} 在participants中")
            return (selected_agent_id, selected_agent_name)
        else:
            self.logger.error(f"  验证失败: Agent {selected_agent_id} 不在participants中")
            return None
    
    # 🚫 移除质量干预机制 - 不再需要_select_quality_improver方法
    # async def _select_quality_improver(self, agent_results, participants):
    #     """不再需要质量干预机制"""
    #     pass

    # 🚫 移除增量选择机制 - 不再需要_select_next_speaker_delta方法
    # async def _select_next_speaker_delta(self, agent_results, context, participants):
    #     """不再需要增量选择机制"""
    #     pass

    # 🚫 移除多样性检查机制 - 不再需要_get_recent_speakers方法
    # async def _get_recent_speakers(self, context, count):
    #     """不再需要多样性检查"""
    #     pass
    
    async def _update_adaptive_thresholds(self, decision: SVRDecision, svr_result: ParallelSVRResult):
        """基于决策结果更新自适应阈值"""
        
        # 简单自适应机制 - 可以用机器学习增强
        global_metrics = svr_result.global_svr_metrics
        
        # 如果我们一直停止得太早或太晚，调整阈值
        if len(self.decision_history) >= 10:
            recent_decisions = self.decision_history[-10:]
            stop_decisions = [d for d in recent_decisions if d.action == DiscussionAction.STOP]
            
            # 如果停止太频繁，增加停止阈值
            if len(stop_decisions) > 7:  # 超过70%的停止决策
                self.adaptive_thresholds['stop_threshold'] = min(0.95, self.adaptive_thresholds['stop_threshold'] + 0.05)
            
            # 如果停止不够，降低停止阈值
            elif len(stop_decisions) < 2:  # 少于20%的停止决策
                self.adaptive_thresholds['stop_threshold'] = max(0.6, self.adaptive_thresholds['stop_threshold'] - 0.05)
        
        # 基于讨论结果调整质量阈值
        discussion_quality = global_metrics.get('discussion_quality', 50.0)
        if discussion_quality < 20:  # 质量很低
            self.adaptive_thresholds['quality_threshold'] = min(40, self.adaptive_thresholds['quality_threshold'] + 5)
        elif discussion_quality > 80:  # 质量高
            self.adaptive_thresholds['quality_threshold'] = max(20, self.adaptive_thresholds['quality_threshold'] - 2)
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """获取决策制定的统计信息"""
        if not self.decision_history:
            return {'total_decisions': 0}
        
        action_counts = {}
        for decision in self.decision_history:
            action = decision.action.value
            action_counts[action] = action_counts.get(action, 0) + 1
        
        avg_confidence = sum(d.confidence for d in self.decision_history) / len(self.decision_history)
        
        return {
            'total_decisions': len(self.decision_history),
            'action_distribution': action_counts,
            'average_confidence': avg_confidence,
            'current_thresholds': self.adaptive_thresholds.copy(),
            'recent_decisions': [
                {
                    'action': d.action.value,
                    'confidence': d.confidence,
                    'selected_agent': d.selected_agent_name
                }
                for d in self.decision_history[-5:]
            ]
        }
