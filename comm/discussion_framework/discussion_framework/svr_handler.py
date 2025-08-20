"""
SVR处理器
处理并行SVR结果并做出讨论流程决策
"""

import asyncio
import logging
import random
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
                 stop_threshold: float = 0.5,  # 🚀 降低停止阈值，使讨论更容易停止
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
        """简化的决策逻辑 - 只基于S值平均，支持动态阈值"""

        reasoning = []
        confidence = 0.8

        # 获取上下文快照计算动态阈值
        snapshot = await context.get_current_snapshot()
        total_turns = snapshot.session_state.get('total_turns', 0)

        # 基础阈值
        base_threshold = self.adaptive_thresholds['stop_threshold']
        effective_threshold = base_threshold

        # 早期轮次的简单/复杂启发式调整
        if total_turns <= 1 and snapshot.recent_turns:
            first_content = snapshot.recent_turns[0].message.content
            first_question_count = first_content.count('?') + first_content.count('？')
            first_length = len(first_content)

            # 🚀 语义化阈值调整：基于内容语义而非简单长度判断

            # 🚀 优化的语义化阈值调整：优先级从高到低

            # 最高优先级：检测明确提问（即使包含问候语）
            if first_question_count > 0 or "什么" in first_content or "如何" in first_content or "为什么" in first_content:
                # 明确提问：提高阈值，需要充分回答
                effective_threshold = min(0.8, base_threshold + 0.20)
                reasoning.append(f"检测到明确提问，提高停止阈值至: {effective_threshold:.3f}")
            elif first_length > 50:
                # 长文本：适度提高阈值
                effective_threshold = min(0.75, base_threshold + 0.10)
                reasoning.append(f"检测到长文本输入，适度提高停止阈值至: {effective_threshold:.3f}")
            else:
                # 检测简单问候类内容（仅在非提问情况下）
                greeting_patterns = ["你好", "您好", "大家好", "谢谢", "感谢", "再见", "早上好", "晚上好", "辛苦了"]
                is_simple_greeting = any(pattern in first_content for pattern in greeting_patterns)

                # 检测纯粹的感谢或礼貌用语
                thanks_patterns = ["谢谢", "感谢", "辛苦", "麻烦"]
                is_simple_thanks = any(pattern in first_content for pattern in thanks_patterns) and first_length <= 15

                if is_simple_greeting or is_simple_thanks:
                    # 简单问候/感谢：极低阈值，几乎立即停止
                    effective_threshold = 0.15
                    reasoning.append(f"检测到简单问候/感谢，设置极低停止阈值: {effective_threshold:.3f}")
                elif first_length <= 8 and first_question_count == 0:
                    # 极短无问号：很低阈值
                    effective_threshold = 0.25
                    reasoning.append(f"检测到极短交互，设置很低停止阈值: {effective_threshold:.3f}")
                elif first_length <= 20 and first_question_count == 0:
                    # 短无问号：较低阈值
                    effective_threshold = max(0.35, base_threshold - 0.15)
                    reasoning.append(f"检测到短交互，设置较低停止阈值: {effective_threshold:.3f}")
                else:
                    # 🚀 单Agent模式：降低阈值，更容易停止
                    if len(agent_results) <= 1:
                        effective_threshold = max(0.3, base_threshold - 0.2)
                        reasoning.append(f"单Agent模式，降低停止阈值至: {effective_threshold:.3f}")
                    else:
                        # 🚀 多Agent模式：也适度降低阈值，避免过度讨论
                        effective_threshold = max(0.4, base_threshold - 0.1)
                        reasoning.append(f"多Agent模式，适度降低停止阈值至: {effective_threshold:.3f}")

        # 基于停止趋势的调整
        global_metrics = getattr(context, '_real_time_metrics', {})
        global_stop_trend = global_metrics.get('global_stop_trend', 0.0)
        if global_stop_trend > 0.05:  # 停止趋势上升
            effective_threshold = max(0.4, effective_threshold - 0.05)
            reasoning.append(f"停止趋势上升，降低阈值至 {effective_threshold:.3f}")

        # 停止条件判断：任意Agent的S值超过阈值 或 全局平均超过动态阈值
        any_agent_exceeds = False
        exceeded_agent_id = None
        exceeded_agent_name = None
        exceeded_value = 0.0
        for aid, res in (agent_results or {}).items():
            s_val = res.svr_values.get('stop_value', 0.0)
            if s_val >= effective_threshold:
                any_agent_exceeds = True
                exceeded_agent_id = aid
                exceeded_agent_name = res.agent_name
                exceeded_value = s_val
                break

        if any_agent_exceeds or global_stop_average >= effective_threshold:
            if any_agent_exceeds:
                reasoning.append(f"Agent {exceeded_agent_name} 的S值 ({exceeded_value:.3f}) 超过动态阈值 ({effective_threshold:.3f})")
                stop_basis = 'any_agent_s_exceeded'
            else:
                reasoning.append(f"全局停止平均值 ({global_stop_average:.3f}) 超过动态阈值 ({effective_threshold:.3f})")
                stop_basis = 'global_average_exceeded'

            return SVRDecision(
                action=DiscussionAction.SUMMARIZE,
                selected_agent_id=exceeded_agent_id,
                selected_agent_name=exceeded_agent_name,
                confidence=0.9,
                reasoning=reasoning,
                metadata={
                    'global_stop_average': global_stop_average,
                    'stop_threshold': effective_threshold,
                    'base_threshold': base_threshold,
                    'stop_reason': 's_value_threshold_exceeded',
                    'decision_basis': stop_basis
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
        """优化的Agent选择机制：防止连续发言 + 智能随机选择"""

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

        # 收集所有Agent的V值，并应用@加权（最小侵入）
        # mentions 从最近一轮用户文本里获取
        mentions = []
        try:
            snap = await context.get_current_snapshot()
            # 找最近一条来自"user"的turn
            last_user_content = None
            for t in reversed(snap.recent_turns):
                if t.agent_id == 'user':
                    last_user_content = t
                    break
            if last_user_content and last_user_content.message and last_user_content.message.metadata:
                mentions = last_user_content.message.metadata.get('mentions', []) or []
        except Exception as _e:
            self.logger.debug(f"mentions获取失败: {_e}")

        # 构建 @ 奖励映射（agent_id -> bonus）
        BONUS_FORMAT = 20.0
        BONUS_SEMANTIC = 30.0
        mention_bonus: Dict[str, float] = {}
        for m in mentions:
            try:
                mid = m.get('agent_id')
                mtype = m.get('type')
                if not mid:
                    continue
                bonus = BONUS_SEMANTIC if mtype == 'semantic' else BONUS_FORMAT
                mention_bonus[mid] = max(mention_bonus.get(mid, 0.0), bonus)  # 语义优先表现为更高加权
            except Exception:
                continue

        agent_v_values = []
        for agent_id, result in agent_results.items():
            if agent_id in participants:
                base_v = float(result.svr_values.get('value_score', 0.0))
                bonus = mention_bonus.get(agent_id, 0.0)
                v_value = min(base_v + bonus, 100.0)
                agent_name = participants[agent_id].name
                agent_v_values.append((agent_id, agent_name, v_value))
                if bonus > 0:
                    self.logger.info(f"  @加权: {agent_name} +{bonus} => V={v_value:.1f}")
                else:
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

        # 🚀 新增：获取最近发言者，实现轮换机制
        last_speaker_id = None  # 确保在整个方法内可用
        try:
            snapshot = await context.get_current_snapshot()
            if snapshot.recent_turns:
                # 获取最后一个非用户发言者
                for turn in reversed(snapshot.recent_turns):
                    if turn.agent_id != "user" and turn.agent_id != "system":
                        last_speaker_id = turn.agent_id
                        break

            self.logger.info(f"最近发言者: {last_speaker_id}")

            # 过滤掉最近发言的Agent（除非只有一个Agent）
            filtered_candidates = []
            for agent_id, agent_name, v_value in agent_v_values:
                if agent_id != last_speaker_id or len(agent_v_values) == 1:
                    filtered_candidates.append((agent_id, agent_name, v_value))

            # 如果过滤后还有候选者，使用过滤后的列表
            if filtered_candidates:
                agent_v_values = filtered_candidates
                self.logger.info(f"轮换过滤后剩余候选者: {len(agent_v_values)}")
            else:
                self.logger.warning("轮换过滤后无候选者，使用原始列表")

        except Exception as e:
            self.logger.warning(f"轮换机制执行失败，使用原始选择逻辑: {e}")

        # 按V值排序（降序）
        agent_v_values.sort(key=lambda x: x[2], reverse=True)

        # 记录排序结果
        self.logger.info(f"V值排序结果:")
        for i, (agent_id, agent_name, v_value) in enumerate(agent_v_values[:3]):  # 显示前3名
            self.logger.info(f"  {i+1}. {agent_name}: V值={v_value:.1f}")

        # 🚀 新增：若存在@提及，则优先从被@集合内按V值最高选择
        mentioned_ids = set(mention_bonus.keys()) if mention_bonus else set()
        if mentioned_ids:
            mentioned_candidates = [t for t in agent_v_values if t[0] in mentioned_ids]
            if mentioned_candidates:
                mentioned_candidates.sort(key=lambda x: x[2], reverse=True)
                selected_agent_id, selected_agent_name, highest_v_value = mentioned_candidates[0]
                self.logger.info(f"✓ 存在@提及，优先选择: {selected_agent_name} (V值: {highest_v_value:.1f})")
            else:
                # 回退至全量候选逻辑
                if len(agent_v_values) <= 3:
                    selected_agent_id, selected_agent_name, highest_v_value = agent_v_values[0]
                    self.logger.info(f"✓ 候选数≤3，选择V值最高: {selected_agent_name} (V值: {highest_v_value:.1f})")
                else:
                    top_60_percent_count = max(1, int(len(agent_v_values) * 0.6))
                    top_candidates = agent_v_values[:top_60_percent_count]
                    selected_agent_id, selected_agent_name, selected_v_value = random.choice(top_candidates)
                    self.logger.info(f"✓ 候选数>3，从前{top_60_percent_count}名中随机选择: {selected_agent_name} (V值: {selected_v_value:.1f})")
        else:
            # 原有全量候选逻辑
            if len(agent_v_values) <= 3:
                selected_agent_id, selected_agent_name, highest_v_value = agent_v_values[0]
                self.logger.info(f"✓ 候选数≤3，选择V值最高: {selected_agent_name} (V值: {highest_v_value:.1f})")
            else:
                top_60_percent_count = max(1, int(len(agent_v_values) * 0.6))
                top_candidates = agent_v_values[:top_60_percent_count]
                selected_agent_id, selected_agent_name, selected_v_value = random.choice(top_candidates)
                self.logger.info(f"✓ 候选数>3，从前{top_60_percent_count}名中随机选择: {selected_agent_name} (V值: {selected_v_value:.1f})")

        # ✅ 轮换兜底：若仍选中最近发言者且参与者>1，强制选择不同Agent
        try:
            if len(participants) > 1 and last_speaker_id and selected_agent_id == last_speaker_id:
                self.logger.info("⚖️ 轮换兜底触发：避免连续同一Agent发言")
                # 优先从候选中找不同的
                alternative_found = False
                for cand_id, cand_name, _ in agent_v_values:
                    if cand_id != last_speaker_id:
                        selected_agent_id, selected_agent_name = cand_id, cand_name
                        alternative_found = True
                        self.logger.info(f"  → 改选候选Agent: {cand_name} (ID: {cand_id})")
                        break
                # 若候选中没有不同的，则从participants中找一个不同的
                if not alternative_found:
                    for pid, p in participants.items():
                        if pid != last_speaker_id:
                            selected_agent_id, selected_agent_name = pid, p.name
                            self.logger.info(f"  → 改选参与者Agent: {p.name} (ID: {pid})")
                            break
        except Exception as e:
            self.logger.warning(f"轮换兜底发生异常：{e}")

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
