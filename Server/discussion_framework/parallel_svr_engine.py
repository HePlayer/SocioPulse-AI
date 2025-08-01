"""
并行SVR计算引擎
同时为所有Agent计算SVR值，使用异步/等待和线程池
"""

import asyncio
import time
import logging
import concurrent.futures
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from .discussion_context import DiscussionContext, ContextSnapshot
from Item.Communication.discussion_types import DiscussionTurn, DiscussionSession
from Item.Agentlib import Agent


@dataclass
class AgentSVRResult:
    """单个Agent的SVR计算结果"""
    agent_id: str
    agent_name: str
    svr_values: Dict[str, float]
    computation_time: float
    analysis: Dict[str, Any]
    confidence: float
    recommendations: List[str]


@dataclass
class ParallelSVRResult:
    """所有Agent的并行SVR结果"""
    timestamp: float
    agent_results: Dict[str, AgentSVRResult]
    global_svr_metrics: Dict[str, float]
    computation_stats: Dict[str, Any]
    next_action_recommendation: str
    selected_agent_candidates: List[str]


class AgentSVRComputer:
    """单个Agent的SVR计算器 - 设计用于并行执行"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.computation_history = []
        
    async def compute_svr(self, context: Dict[str, Any]) -> AgentSVRResult:
        """为此Agent计算SVR值 - 基于增量的版本"""
        start_time = time.time()

        try:
            # 提取上下文数据
            agent_turns = context['agent_turns']
            other_turns = context['other_turns']
            session_state = context['session_state']
            global_metrics = context['global_metrics']

            # 计算原始SVR值
            computed_stop_value = await self._compute_stop_value(
                agent_turns, other_turns, session_state, global_metrics
            )
            computed_value_score = await self._compute_value_score(
                agent_turns, other_turns, session_state
            )
            computed_repeat_risk = await self._compute_repeat_risk(
                agent_turns, session_state
            )

            # 获取历史SVR值
            previous_svr = self._get_previous_svr_values()

            # 计算实际S值（应用增量限制）
            actual_stop_value = self._calculate_actual_s_value(computed_stop_value, previous_svr)

            # 计算增量（用于调试和Agent选择）
            stop_delta, value_delta, repeat_delta = self._calculate_svr_deltas(
                actual_stop_value, computed_value_score, computed_repeat_risk, previous_svr
            )

            # 基于数据质量计算置信度
            confidence = self._calculate_confidence(agent_turns, other_turns)

            # 生成建议
            recommendations = self._generate_recommendations_delta(
                stop_delta, value_delta, repeat_delta, confidence
            )

            # 构建SVR值 - 简化版本
            svr_values = {
                # 核心值：实际S值（应用了增量限制）
                'stop_value': actual_stop_value,

                # 个体值：V/R值保持原样（用于Agent选择）
                'value_score': computed_value_score,
                'repeat_risk': computed_repeat_risk,

                # 增量信息（用于调试）
                'stop_delta': stop_delta,
                'value_delta': value_delta,
                'repeat_delta': repeat_delta,

                # 综合分数（基于个体值）
                'composite_score': self._calculate_composite_score(
                    actual_stop_value, computed_value_score, computed_repeat_risk
                ),

                # 调试信息
                'delta_limited': True,
                'computed_stop': computed_stop_value,  # 原始计算值
                'actual_stop': actual_stop_value,     # 限制后的实际值
                'has_history': len(self.computation_history) > 0
            }
            
            computation_time = time.time() - start_time
            
            result = AgentSVRResult(
                agent_id=self.agent_id,
                agent_name=context['agent_info'].get('name', 'Unknown'),
                svr_values=svr_values,
                computation_time=computation_time,
                analysis={
                    'stop_factors': await self._analyze_stop_factors(agent_turns, other_turns, session_state),
                    'value_factors': await self._analyze_value_factors(agent_turns, session_state),
                    'repeat_factors': await self._analyze_repeat_factors(agent_turns),
                    'delta_analysis': {
                        'stop_trend': 'increasing' if stop_delta > 0.1 else 'decreasing' if stop_delta < -0.1 else 'stable',
                        'value_trend': 'increasing' if value_delta > 5 else 'decreasing' if value_delta < -5 else 'stable',
                        'repeat_trend': 'increasing' if repeat_delta > 0.1 else 'decreasing' if repeat_delta < -0.1 else 'stable'
                    }
                },
                confidence=confidence,
                recommendations=recommendations
            )
            
            # 缓存结果
            self.computation_history.append(result)
            if len(self.computation_history) > 50:  # 保留最近50次计算
                self.computation_history = self.computation_history[-50:]
            
            return result
            
        except Exception as e:
            # 错误时返回安全的默认值
            return AgentSVRResult(
                agent_id=self.agent_id,
                agent_name=context.get('agent_info', {}).get('name', 'Unknown'),
                svr_values={
                    'stop_value': 0.1,
                    'value_score': 45.0,
                    'repeat_risk': 0.1,
                    'stop_delta': 0.0,      # 增量为0表示无变化
                    'value_delta': 0.0,
                    'repeat_delta': 0.0,
                    'composite_score': 50.0,
                    'delta_based': True,
                    'has_history': False
                },
                computation_time=time.time() - start_time,
                analysis={'error': str(e), 'fallback_values': True},
                confidence=0.1,
                recommendations=['SVR计算出错，使用安全默认值']
            )
    
    async def _compute_stop_value(self, agent_turns, other_turns, session_state, global_metrics) -> float:
        """计算此Agent的停止值"""
        stop_factors = []
        
        # 因子1：Agent对共识的贡献（0.3权重）
        if len(other_turns) > 0:
            consensus_contribution = await self._calculate_consensus_contribution(
                agent_turns, other_turns
            )
            stop_factors.append(consensus_contribution * 0.3)
        
        # 因子2：从Agent角度看讨论饱和度（0.25权重）
        saturation = await self._calculate_discussion_saturation(agent_turns, other_turns)
        stop_factors.append(saturation * 0.25)
        
        # 因子3：Agent疲劳指标（0.2权重）
        fatigue = await self._calculate_agent_fatigue(agent_turns)
        stop_factors.append(fatigue * 0.2)
        
        # 因子4：全局讨论状态（0.15权重）
        global_stop_signal = global_metrics.get('avg_stop_value', 0.0)
        stop_factors.append(global_stop_signal * 0.15)
        
        # 因子5：基于时间的因子（0.1权重）
        time_factor = min(session_state.get('duration', 0) / 3600, 1.0)
        stop_factors.append(time_factor * 0.1)
        
        return min(sum(stop_factors), 1.0)
    
    async def _compute_value_score(self, agent_turns, other_turns, session_state) -> float:
        """计算此Agent的价值分数"""
        if not agent_turns:
            return 75.0  # 对于尚未发言的Agent给予默认高价值
        
        value_factors = []
        
        # 最近轮次质量（0.4权重）
        if agent_turns:
            latest_turn = agent_turns[-1]
            turn_quality = await self._assess_turn_quality(latest_turn, other_turns)
            value_factors.append(turn_quality * 0.4)
        
        # 历史表现（0.3权重）
        historical_value = await self._calculate_historical_value(agent_turns)
        value_factors.append(historical_value * 0.3)
        
        # 互动潜力（0.2权重）
        interaction_potential = await self._calculate_interaction_potential(
            agent_turns, other_turns
        )
        value_factors.append(interaction_potential * 0.2)
        
        # 专业相关性（0.1权重）
        expertise_relevance = await self._calculate_expertise_relevance(
            agent_turns, session_state
        )
        value_factors.append(expertise_relevance * 0.1)
        
        return min(sum(value_factors), 100.0)
    
    async def _compute_repeat_risk(self, agent_turns, session_state) -> float:
        """计算此Agent的重复风险"""
        if len(agent_turns) < 2:
            return 0.0  # 如果Agent发言不多则无风险
        
        repeat_factors = []
        
        # 与自己之前轮次的内容相似性（0.4权重）
        self_similarity = await self._calculate_self_similarity(agent_turns)
        repeat_factors.append(self_similarity * 0.4)
        
        # 模式重复（0.3权重）
        pattern_repetition = await self._calculate_pattern_repetition(agent_turns)
        repeat_factors.append(pattern_repetition * 0.3)
        
        # 论点回收（0.2权重）
        argument_recycling = await self._calculate_argument_recycling(agent_turns)
        repeat_factors.append(argument_recycling * 0.2)
        
        # 基于频率的重复风险（0.1权重）
        frequency_risk = await self._calculate_frequency_risk(agent_turns, session_state)
        repeat_factors.append(frequency_risk * 0.1)
        
        return min(sum(repeat_factors), 1.0)

    def _get_previous_svr_values(self) -> Optional[Dict[str, float]]:
        """获取上一次的SVR值用于计算增量"""
        if len(self.computation_history) == 0:
            return None

        last_result = self.computation_history[-1]
        return {
            'stop_value': last_result.svr_values.get('stop_value', 0.0),
            'value_score': last_result.svr_values.get('value_score', 50.0),
            'repeat_risk': last_result.svr_values.get('repeat_risk', 0.0)
        }

    def _calculate_svr_deltas(self, current_stop: float, current_value: float,
                             current_repeat: float, previous_svr: Optional[Dict[str, float]]) -> Tuple[float, float, float]:
        """计算SVR增量/变化率 - 增强S值增量限制"""

        # 配置增量限制
        max_stop_delta_limit = 0.2  # S值增量限制
        max_value_delta_limit = 25.0  # V值增量限制（保留用于Agent选择）
        max_repeat_delta_limit = 0.3  # R值增量限制（保留用于Agent选择）

        if previous_svr is None:
            # 首次计算，使用相对于中性值的偏移作为"增量"
            stop_delta = current_stop - 0.5      # 中性停止值为0.5
            value_delta = current_value - 50.0   # 中性价值分数为50
            repeat_delta = current_repeat - 0.3  # 中性重复风险为0.3
        else:
            # 计算相对于上次的变化
            stop_delta = current_stop - previous_svr['stop_value']
            value_delta = current_value - previous_svr['value_score']
            repeat_delta = current_repeat - previous_svr['repeat_risk']

        # 应用增量限制
        if abs(stop_delta) > max_stop_delta_limit:
            stop_delta = max_stop_delta_limit * (1 if stop_delta > 0 else -1)

        if abs(value_delta) > max_value_delta_limit:
            value_delta = max_value_delta_limit * (1 if value_delta > 0 else -1)

        if abs(repeat_delta) > max_repeat_delta_limit:
            repeat_delta = max_repeat_delta_limit * (1 if repeat_delta > 0 else -1)

        return stop_delta, value_delta, repeat_delta

    def _calculate_actual_s_value(self, computed_stop: float, previous_svr: Optional[Dict[str, float]]) -> float:
        """基于增量限制计算实际S值"""

        if previous_svr is None:
            # 首次计算，直接使用计算值
            return min(max(computed_stop, 0.0), 1.0)

        # 获取上次的S值
        previous_stop = previous_svr.get('stop_value', 0.5)

        # 计算增量
        stop_delta = computed_stop - previous_stop

        # 应用增量限制
        max_delta_limit = 0.2
        if abs(stop_delta) > max_delta_limit:
            stop_delta = max_delta_limit * (1 if stop_delta > 0 else -1)

        # 计算实际S值
        actual_stop = previous_stop + stop_delta

        # 确保在有效范围内
        return min(max(actual_stop, 0.0), 1.0)

    def _calculate_composite_score(self, stop_value: float, value_score: float, repeat_risk: float) -> float:
        """计算综合SVR分数"""
        # 综合分数：高价值、低停止、低重复 = 高分数
        composite = (value_score * 0.5) + ((1 - stop_value) * 30) + ((1 - repeat_risk) * 20)
        return min(max(composite, 0.0), 100.0)

    def _calculate_composite_score_delta(self, stop_delta: float, value_delta: float, repeat_delta: float) -> float:
        """基于增量计算综合分数"""
        # 基础分数从50开始（中性）
        base_score = 50.0

        # 增量调整：
        # - 停止值增加 = 分数降低
        # - 价值分数增加 = 分数提高
        # - 重复风险增加 = 分数降低

        stop_adjustment = -stop_delta * 30      # 停止增量的负向影响
        value_adjustment = value_delta * 0.5    # 价值增量的正向影响
        repeat_adjustment = -repeat_delta * 20  # 重复增量的负向影响

        composite = base_score + stop_adjustment + value_adjustment + repeat_adjustment

        return min(max(composite, 0.0), 100.0)
    
    def _calculate_confidence(self, agent_turns, other_turns) -> float:
        """计算SVR计算的置信度"""
        confidence_factors = []
        
        # 数据充分性
        total_data_points = len(agent_turns) + len(other_turns)
        data_sufficiency = min(total_data_points / 10, 1.0)  # 10轮 = 完全置信
        confidence_factors.append(data_sufficiency * 0.4)
        
        # 数据新鲜度
        if agent_turns:
            latest_turn_age = time.time() - agent_turns[-1].timestamp
            recency_score = max(0, 1 - (latest_turn_age / 3600))  # 1小时衰减
            confidence_factors.append(recency_score * 0.3)
        else:
            confidence_factors.append(0.5 * 0.3)  # 无数据时中性
        
        # 历史计算的一致性
        if len(self.computation_history) > 1:
            recent_scores = [r.svr_values.get('composite_score', 50) for r in self.computation_history[-5:]]
            if len(recent_scores) > 1:
                variance = sum((s - sum(recent_scores)/len(recent_scores))**2 for s in recent_scores) / len(recent_scores)
                consistency = max(0, 1 - variance / 1000)  # 标准化方差
                confidence_factors.append(consistency * 0.3)
            else:
                confidence_factors.append(0.7 * 0.3)
        else:
            confidence_factors.append(0.7 * 0.3)
        
        return sum(confidence_factors)
    
    def _generate_recommendations(self, stop_value: float, value_score: float, 
                                repeat_risk: float, confidence: float) -> List[str]:
        """生成可操作的建议"""
        recommendations = []
        
        if stop_value > 0.7:
            recommendations.append("考虑结束讨论 - 停止信号较高")
        
        if value_score < 40:
            recommendations.append("提高内容质量和相关性")
        
        if repeat_risk > 0.6:
            recommendations.append("避免重复之前的论点")
        
        if confidence < 0.5:
            recommendations.append("数据不足，SVR计算可靠性较低")
        
        if not recommendations:
            recommendations.append("继续当前讨论方式")
        
        return recommendations

    def _generate_recommendations_delta(self, stop_delta: float, value_delta: float,
                                      repeat_delta: float, confidence: float) -> List[str]:
        """基于增量生成可操作的建议"""
        recommendations = []

        if stop_delta > 0.2:
            recommendations.append("停止倾向增加 - 考虑结束发言")
        elif stop_delta < -0.2:
            recommendations.append("停止倾向降低 - 适合继续参与")

        if value_delta < -10:
            recommendations.append("价值贡献下降 - 需要提高内容质量")
        elif value_delta > 10:
            recommendations.append("价值贡献提升 - 保持当前水平")

        if repeat_delta > 0.3:
            recommendations.append("重复风险增加 - 避免重复之前的论点")
        elif repeat_delta < -0.3:
            recommendations.append("重复风险降低 - 内容多样性良好")

        if confidence < 0.5:
            recommendations.append("数据不足，增量计算可靠性较低")

        if not recommendations:
            recommendations.append("SVR增量稳定，继续当前讨论方式")

        return recommendations

    # 详细分析方法的占位符实现
    async def _calculate_consensus_contribution(self, agent_turns, other_turns) -> float:
        """计算此Agent对共识的贡献"""
        # 简化实现 - 可以用NLP增强
        if not agent_turns or not other_turns:
            return 0.3

        # 检查最近轮次中的同意指标
        recent_content = ' '.join(turn.message.content for turn in agent_turns[-3:])
        agreement_words = ['同意', '赞成', '支持', '认同', '正确']
        agreement_count = sum(1 for word in agreement_words if word in recent_content)

        return min(agreement_count / 5, 1.0)

    async def _calculate_discussion_saturation(self, agent_turns, other_turns) -> float:
        """从Agent角度计算讨论饱和度"""
        all_turns = agent_turns + other_turns
        if len(all_turns) < 5:
            return 0.0

        # 简单启发式：如果最近轮次变短，讨论可能饱和
        recent_lengths = [len(turn.message.content) for turn in all_turns[-5:]]
        early_lengths = [len(turn.message.content) for turn in all_turns[:5]]

        if not early_lengths or not recent_lengths:
            return 0.0

        avg_recent = sum(recent_lengths) / len(recent_lengths)
        avg_early = sum(early_lengths) / len(early_lengths)

        if avg_early > 0:
            decline_ratio = max(0, (avg_early - avg_recent) / avg_early)
            return min(decline_ratio * 2, 1.0)  # 放大信号

        return 0.0

    async def _calculate_agent_fatigue(self, agent_turns) -> float:
        """计算Agent疲劳指标"""
        if len(agent_turns) < 3:
            return 0.0

        # 检查参与度下降模式
        recent_turns = agent_turns[-3:]

        # 疲劳指标：消息变短，语言复杂度降低
        avg_length = sum(len(turn.message.content) for turn in recent_turns) / len(recent_turns)

        # 简单疲劳启发式：最近消息很短表示疲劳
        if avg_length < 50:  # 平均少于50字符
            return 0.7
        elif avg_length < 100:
            return 0.4
        else:
            return 0.1

    async def _assess_turn_quality(self, turn, other_turns) -> float:
        """评估特定轮次的质量"""
        content = turn.message.content

        quality_factors = []

        # 长度适当性（0.3权重）
        length_score = min(len(content) / 200, 1.0)  # 200字符 = 最佳
        if len(content) > 500:  # 过长的惩罚
            length_score *= 0.8
        quality_factors.append(length_score * 30)

        # 提问（鼓励互动）（0.2权重）
        question_count = content.count('?') + content.count('？')
        question_score = min(question_count / 2, 1.0)
        quality_factors.append(question_score * 20)

        # 引用他人（0.2权重）
        reference_indicators = ['你说', '刚才', '之前', '@']
        reference_score = min(sum(1 for ind in reference_indicators if ind in content) / 3, 1.0)
        quality_factors.append(reference_score * 20)

        # 建设性语言（0.3权重）
        constructive_words = ['建议', '认为', '可以', '应该', '或许', '可能']
        constructive_score = min(sum(1 for word in constructive_words if word in content) / 4, 1.0)
        quality_factors.append(constructive_score * 30)

        return sum(quality_factors)

    async def _calculate_historical_value(self, agent_turns) -> float:
        """计算历史价值贡献"""
        if not agent_turns:
            return 50.0

        # 最近轮次质量的简单平均
        recent_turns = agent_turns[-5:]
        total_quality = 0

        for turn in recent_turns:
            # 简化质量评估
            content_length = len(turn.message.content)
            if 50 <= content_length <= 300:  # 最佳范围
                total_quality += 70
            elif content_length < 50:
                total_quality += 30
            else:
                total_quality += 50

        return total_quality / len(recent_turns) if recent_turns else 50.0

    async def _calculate_interaction_potential(self, agent_turns, other_turns) -> float:
        """计算有意义互动的潜力"""
        if not other_turns:
            return 50.0

        # 检查Agent是否在回应他人
        responding_turns = [turn for turn in agent_turns if getattr(turn, 'responding_to', None)]
        response_ratio = len(responding_turns) / len(agent_turns) if agent_turns else 0

        # 检查他人是否在回应此Agent
        agent_turn_ids = {getattr(turn, 'turn_id', turn.message.id) for turn in agent_turns}
        others_responding = sum(1 for turn in other_turns if getattr(turn, 'responding_to', None) in agent_turn_ids)

        interaction_score = (response_ratio * 50) + min(others_responding * 10, 50)
        return min(interaction_score, 100.0)

    async def _calculate_expertise_relevance(self, agent_turns, session_state) -> float:
        """计算Agent专业知识与当前话题的相关性"""
        # 简化实现 - 可以用主题建模增强
        topic = session_state.get('topic', '')

        if not agent_turns or not topic:
            return 50.0

        # 检查Agent贡献中的话题相关关键词
        agent_content = ' '.join(turn.message.content for turn in agent_turns)
        topic_words = set(topic.lower().split())
        agent_words = set(agent_content.lower().split())

        overlap = len(topic_words.intersection(agent_words))
        relevance = min(overlap / max(len(topic_words), 1) * 100, 100.0)

        return max(relevance, 30.0)  # 最低基线相关性

    async def _calculate_self_similarity(self, agent_turns) -> float:
        """计算Agent自己轮次之间的相似性"""
        if len(agent_turns) < 2:
            return 0.0

        # 简单词汇重叠相似性
        recent_turn = agent_turns[-1]
        previous_turns = agent_turns[:-1]

        recent_words = set(recent_turn.message.content.lower().split())

        max_similarity = 0.0
        for prev_turn in previous_turns[-3:]:  # 检查最近3轮
            prev_words = set(prev_turn.message.content.lower().split())

            if recent_words and prev_words:
                overlap = len(recent_words.intersection(prev_words))
                union = len(recent_words.union(prev_words))
                similarity = overlap / union if union > 0 else 0
                max_similarity = max(max_similarity, similarity)

        return max_similarity

    async def _calculate_pattern_repetition(self, agent_turns) -> float:
        """计算交流模式的重复"""
        if len(agent_turns) < 3:
            return 0.0

        # 检查重复的句子开头
        starters = []
        for turn in agent_turns[-5:]:  # 最近5轮
            sentences = turn.message.content.split('。')
            for sentence in sentences:
                words = sentence.strip().split()
                if words:
                    starters.append(words[0])

        if len(starters) < 2:
            return 0.0

        # 计算重复比率
        unique_starters = len(set(starters))
        repetition_ratio = 1 - (unique_starters / len(starters))

        return repetition_ratio

    async def _calculate_argument_recycling(self, agent_turns) -> float:
        """计算论点回收"""
        if len(agent_turns) < 2:
            return 0.0

        # 简单启发式：检查重复的关键短语
        all_content = [turn.message.content for turn in agent_turns]

        # 提取潜在关键短语（3+字符的词）
        all_phrases = []
        for content in all_content:
            words = [w for w in content.split() if len(w) >= 3]
            all_phrases.extend(words)

        if len(all_phrases) < 2:
            return 0.0

        # 计算短语重复
        unique_phrases = len(set(all_phrases))
        repetition_ratio = 1 - (unique_phrases / len(all_phrases))

        return min(repetition_ratio * 2, 1.0)  # 放大信号

    async def _calculate_frequency_risk(self, agent_turns, session_state) -> float:
        """基于发言频率计算风险"""
        total_turns = session_state.get('total_turns', 1)
        agent_turn_count = len(agent_turns)

        # 如果Agent主导对话则风险增加
        participation_ratio = agent_turn_count / total_turns

        if participation_ratio > 0.5:  # 超过50%的轮次
            return 0.8
        elif participation_ratio > 0.3:  # 超过30%的轮次
            return 0.4
        else:
            return 0.1

    async def _analyze_stop_factors(self, agent_turns, other_turns, session_state) -> Dict[str, Any]:
        """停止因子的详细分析"""
        return {
            'consensus_contribution': await self._calculate_consensus_contribution(agent_turns, other_turns),
            'discussion_saturation': await self._calculate_discussion_saturation(agent_turns, other_turns),
            'agent_fatigue': await self._calculate_agent_fatigue(agent_turns),
            'session_duration': session_state.get('duration', 0),
            'total_turns': session_state.get('total_turns', 0)
        }

    async def _analyze_value_factors(self, agent_turns, session_state) -> Dict[str, Any]:
        """价值因子的详细分析"""
        return {
            'recent_quality': await self._assess_turn_quality(agent_turns[-1], []) if agent_turns else 0,
            'historical_value': await self._calculate_historical_value(agent_turns),
            'expertise_relevance': await self._calculate_expertise_relevance(agent_turns, session_state),
            'turn_count': len(agent_turns)
        }

    async def _analyze_repeat_factors(self, agent_turns) -> Dict[str, Any]:
        """重复因子的详细分析"""
        return {
            'self_similarity': await self._calculate_self_similarity(agent_turns),
            'pattern_repetition': await self._calculate_pattern_repetition(agent_turns),
            'argument_recycling': await self._calculate_argument_recycling(agent_turns),
            'recent_turn_count': len(agent_turns)
        }


class ParallelSVREngine:
    """主要的并行SVR计算引擎"""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers
        self.agent_computers: Dict[str, AgentSVRComputer] = {}
        self.computation_history: List[ParallelSVRResult] = []

        # 性能监控
        self.total_computations = 0
        self.total_computation_time = 0.0
        self.parallel_efficiency_stats = []

        # 设置日志
        self.logger = logging.getLogger(f"{__name__}.ParallelSVREngine")

    async def _validate_agent_ids(self, context: DiscussionContext, participants: Dict[str, Agent]) -> bool:
        """验证Agent ID的一致性，防止ID不匹配导致的SVR计算失败"""
        try:
            snapshot = await context.get_current_snapshot()
            recent_agent_ids = set(turn.agent_id for turn in snapshot.recent_turns)
            participant_ids = set(participants.keys())

            self.logger.debug(f"Agent ID验证: participants={participant_ids}, recent_turns={recent_agent_ids}")

            # 如果没有历史发言，这是正常的（首次计算）
            if not recent_agent_ids:
                self.logger.info("首次SVR计算，无历史发言记录")
                return True

            # 检查ID匹配情况
            unmatched_recent = recent_agent_ids - participant_ids
            unmatched_participants = participant_ids - recent_agent_ids

            if unmatched_recent:
                # 检查是否只是正常的system消息不匹配（冷启动情况）
                system_only_mismatch = unmatched_recent == {"system"}

                if system_only_mismatch:
                    self.logger.debug(f"冷启动情况：历史记录中只有system消息，这是正常的")
                    self.logger.debug(f"不匹配的ID: {unmatched_recent} (system消息不在participants中是正常的)")
                    # 继续SVR计算，这是正常的冷启动情况
                else:
                    # 真正的ID不匹配问题
                    self.logger.warning(f"发现不匹配的历史agent_id: {unmatched_recent}")
                    self.logger.warning(f"这些ID在participants中不存在，但将继续SVR计算")
                    # 即使有不匹配，也继续计算，除非是严重错误
                    if len(unmatched_recent) > len(participant_ids):
                        self.logger.error(f"严重错误：不匹配的ID数量({len(unmatched_recent)})超过participants数量({len(participant_ids)})")
                        return False

            if unmatched_participants:
                self.logger.info(f"参与者中有尚未发言的Agent: {unmatched_participants}")

            # 检查匹配的Agent数量
            matched_agents = recent_agent_ids.intersection(participant_ids)
            self.logger.info(f"ID匹配验证通过: {len(matched_agents)} 个Agent有历史记录")

            return True

        except Exception as e:
            self.logger.error(f"Agent ID验证失败: {e}")
            return False

    async def compute_parallel_svr(self,
                                  context: DiscussionContext,
                                  participants: Dict[str, Agent]) -> ParallelSVRResult:
        """
        为所有Agent并行计算SVR值

        Args:
            context: 讨论上下文
            participants: 所有参与的Agent

        Returns:
            ParallelSVRResult: 所有Agent的合并结果
        """
        start_time = time.time()

        # 验证Agent ID一致性（增强容错性）
        id_validation_passed = await self._validate_agent_ids(context, participants)
        if not id_validation_passed:
            self.logger.warning("Agent ID验证失败，但继续执行SVR计算")
            self.logger.info("SVR计算将为所有participants生成默认值以确保连续性")
        else:
            self.logger.debug("Agent ID验证通过，开始正常SVR计算")

        # 确保我们为所有Agent都有计算器
        for agent_id in participants.keys():
            if agent_id not in self.agent_computers:
                self.agent_computers[agent_id] = AgentSVRComputer(agent_id)
                self.logger.debug(f"为Agent {agent_id} 创建新的SVR计算器")

        # 为每个Agent准备上下文 - 增强ID匹配版本
        agent_contexts = {}

        # 首先获取历史记录中的所有agent_id
        snapshot = await context.get_current_snapshot()
        historical_agent_ids = set(turn.agent_id for turn in snapshot.recent_turns)
        participants_keys = set(participants.keys())

        self.logger.info(f"ID匹配分析:")
        self.logger.info(f"  历史记录agent_ids: {historical_agent_ids}")
        self.logger.info(f"  participants keys: {participants_keys}")

        # 检查直接匹配
        direct_matches = historical_agent_ids.intersection(participants_keys)
        self.logger.info(f"  直接匹配的IDs: {direct_matches}")

        for agent_id in participants.keys():
            agent_context = await context.get_agent_context(agent_id)
            agent_contexts[agent_id] = agent_context

            # 详细记录每个Agent的上下文获取情况
            debug_info = agent_context.get('debug_info', {})
            agent_turns_count = debug_info.get('agent_turns_count', 0)

            self.logger.debug(f"Agent {agent_id} 上下文获取:")
            self.logger.debug(f"  历史发言数: {agent_turns_count}")
            self.logger.debug(f"  在历史记录中: {agent_id in historical_agent_ids}")

            # 如果Agent没有历史发言，这是正常的（可能是首次发言）
            if agent_turns_count == 0 and agent_id not in historical_agent_ids:
                self.logger.debug(f"  Agent {agent_id} 尚未发言，将使用默认SVR值")

        # 创建并行计算任务
        tasks = []
        for agent_id, agent_context in agent_contexts.items():
            computer = self.agent_computers[agent_id]
            task = asyncio.create_task(
                computer.compute_svr(agent_context),
                name=f"svr_compute_{agent_id}"
            )
            tasks.append((agent_id, task))

        # 并行执行所有计算
        agent_results = {}
        computation_errors = {}

        try:
            # 等待所有任务完成，设置超时
            results = await asyncio.wait_for(
                asyncio.gather(*[task for _, task in tasks], return_exceptions=True),
                timeout=30.0  # 30秒超时
            )

            # 处理结果
            for i, (agent_id, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    computation_errors[agent_id] = str(result)
                    # 为失败的计算创建默认结果
                    agent_results[agent_id] = AgentSVRResult(
                        agent_id=agent_id,
                        agent_name=participants[agent_id].name,
                        svr_values={'stop_value': 0.0, 'value_score': 50.0, 'repeat_risk': 0.0, 'composite_score': 50.0},
                        computation_time=0.0,
                        analysis={'error': str(result)},
                        confidence=0.0,
                        recommendations=['计算失败']
                    )
                else:
                    agent_results[agent_id] = result

        except asyncio.TimeoutError:
            # 处理超时 - 取消剩余任务并使用部分结果
            for _, task in tasks:
                if not task.done():
                    task.cancel()

            # 收集已完成的结果
            for agent_id, task in tasks:
                if task.done() and not task.cancelled():
                    try:
                        result = task.result()
                        agent_results[agent_id] = result
                    except Exception as e:
                        computation_errors[agent_id] = str(e)

        # 详细记录agent_results的信息和ID匹配状态
        self.logger.info(f"SVR计算完成: 成功计算 {len(agent_results)} 个Agent")
        if computation_errors:
            self.logger.warning(f"SVR计算错误: {len(computation_errors)} 个Agent失败: {list(computation_errors.keys())}")

        # 关键调试：验证agent_results的key与participants的匹配
        agent_results_keys = set(agent_results.keys())
        participants_keys = set(participants.keys())

        self.logger.info(f"ID匹配验证:")
        self.logger.info(f"  agent_results keys: {agent_results_keys}")
        self.logger.info(f"  participants keys: {participants_keys}")

        # 检查匹配情况
        matched_keys = agent_results_keys.intersection(participants_keys)
        unmatched_agent_results = agent_results_keys - participants_keys
        unmatched_participants = participants_keys - agent_results_keys

        self.logger.info(f"  匹配的keys: {matched_keys} (数量: {len(matched_keys)})")
        if unmatched_agent_results:
            self.logger.warning(f"  agent_results中多余的keys: {unmatched_agent_results}")
        if unmatched_participants:
            self.logger.warning(f"  participants中缺失的keys: {unmatched_participants}")

        # 如果没有匹配的key，这是严重问题
        if not matched_keys:
            self.logger.error("严重错误：agent_results与participants完全不匹配！")
            self.logger.error("这将导致Agent选择失败，需要立即修复")

        # 记录每个Agent的SVR值（用于调试）
        for agent_id, result in agent_results.items():
            svr_values = result.svr_values
            in_participants = agent_id in participants_keys
            self.logger.debug(f"Agent {agent_id} SVR: S={svr_values.get('stop_value', 0):.3f}, "
                            f"V={svr_values.get('value_score', 0):.1f}, "
                            f"R={svr_values.get('repeat_risk', 0):.3f}, "
                            f"在participants中: {in_participants}")

        # 计算全局指标
        global_svr_metrics = self._calculate_global_metrics(agent_results)

        # 确定下一步行动和Agent选择
        next_action, selected_candidates = self._determine_next_action(
            agent_results, global_svr_metrics
        )

        # 创建计算统计
        computation_time = time.time() - start_time
        computation_stats = {
            'total_time': computation_time,
            'parallel_efficiency': len(agent_results) / computation_time if computation_time > 0 else 0,
            'successful_computations': len(agent_results),
            'failed_computations': len(computation_errors),
            'errors': computation_errors
        }

        # 创建最终结果
        parallel_result = ParallelSVRResult(
            timestamp=time.time(),
            agent_results=agent_results,
            global_svr_metrics=global_svr_metrics,
            computation_stats=computation_stats,
            next_action_recommendation=next_action,
            selected_agent_candidates=selected_candidates
        )

        # 更新统计
        self._update_performance_stats(computation_time, len(agent_results))

        # 缓存结果
        self.computation_history.append(parallel_result)
        if len(self.computation_history) > 100:  # 保留最近100个结果
            self.computation_history = self.computation_history[-100:]

        # 添加SVR计算完成确认日志
        self.logger.info(f"✅ SVR计算成功完成: 成功计算 {len(agent_results)} 个Agent")
        self.logger.info(f"   计算时间: {computation_time:.3f}秒")
        self.logger.info(f"   全局停止平均值: {global_svr_metrics.get('global_stop_average', 0.0):.3f}")

        # 记录每个Agent的V值用于调试
        if agent_results:
            self.logger.debug("Agent V值详情:")
            for agent_id, result in agent_results.items():
                agent_name = participants.get(agent_id, {}).name if hasattr(participants.get(agent_id, {}), 'name') else 'Unknown'
                v_value = result.svr_values.get('value_score', 0.0)
                self.logger.debug(f"  {agent_name} (ID: {agent_id}): V值={v_value:.1f}")

        return parallel_result

    def _calculate_global_metrics(self, agent_results: Dict[str, AgentSVRResult]) -> Dict[str, float]:
        """简化的全局SVR指标计算 - 只计算S值平均"""
        if not agent_results:
            return {
                'global_stop_average': 0.0,
                'agent_count': 0,
                'discussion_quality': 50.0,
                'simplified_calculation': True,
                'consensus_removed': True
            }

        # 只提取S值进行平均计算
        stop_values = [r.svr_values.get('stop_value', 0.0) for r in agent_results.values()]

        # 计算S值的简单平均
        global_stop_average = sum(stop_values) / len(stop_values) if stop_values else 0.0

        # 保留个体V/R值但不用于全局决策
        # 简化的讨论质量计算（可选）
        individual_qualities = []
        for result in agent_results.values():
            value_score = result.svr_values.get('value_score', 50.0)
            repeat_risk = result.svr_values.get('repeat_risk', 0.0)
            quality = (value_score * 0.7) + ((1 - repeat_risk) * 30)
            individual_qualities.append(quality)

        discussion_quality = sum(individual_qualities) / len(individual_qualities) if individual_qualities else 50.0

        return {
            # 核心指标：只有S值平均
            'global_stop_average': global_stop_average,

            # 辅助信息
            'agent_count': len(agent_results),
            'discussion_quality': min(discussion_quality, 100.0),
            'individual_stop_values': stop_values,  # 用于调试

            # 标识简化计算
            'simplified_calculation': True,
            'consensus_removed': True
        }

    def _determine_next_action(self,
                              agent_results: Dict[str, AgentSVRResult],
                              global_metrics: Dict[str, float]) -> Tuple[str, List[str]]:
        """确定下一步行动并选择候选Agent"""

        # 检查停止条件
        global_stop = global_metrics.get('global_stop_value', 0.0)
        consensus_level = global_metrics.get('consensus_level', 0.0)

        # 停止条件
        if global_stop > 0.8:
            return 'stop', []

        if consensus_level > 0.9:
            return 'stop', []

        # 继续并选择Agent
        # 按综合分数和其他因子排名Agent
        agent_scores = []
        for agent_id, result in agent_results.items():
            composite_score = result.svr_values.get('composite_score', 50.0)
            confidence = result.confidence
            repeat_risk = result.svr_values.get('repeat_risk', 0.0)

            # 计算选择分数
            selection_score = (composite_score * 0.6) + (confidence * 20) + ((1 - repeat_risk) * 20)

            agent_scores.append((agent_id, selection_score, result))

        # 按选择分数排序（降序）
        agent_scores.sort(key=lambda x: x[1], reverse=True)

        # 选择前几名候选（最多3个）
        selected_candidates = [agent_id for agent_id, _, _ in agent_scores[:3]]

        return 'continue', selected_candidates

    def _update_performance_stats(self, computation_time: float, successful_count: int):
        """更新性能统计"""
        self.total_computations += 1
        self.total_computation_time += computation_time

        efficiency = successful_count / computation_time if computation_time > 0 else 0
        self.parallel_efficiency_stats.append(efficiency)

        # 保留最近50次效率测量
        if len(self.parallel_efficiency_stats) > 50:
            self.parallel_efficiency_stats = self.parallel_efficiency_stats[-50:]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取用于监控的性能指标"""
        if not self.parallel_efficiency_stats:
            return {
                'total_computations': self.total_computations,
                'average_computation_time': 0.0,
                'average_efficiency': 0.0,
                'efficiency_trend': 'no_data'
            }

        avg_computation_time = self.total_computation_time / self.total_computations if self.total_computations > 0 else 0
        avg_efficiency = sum(self.parallel_efficiency_stats) / len(self.parallel_efficiency_stats)

        # 计算效率趋势
        if len(self.parallel_efficiency_stats) >= 10:
            recent_avg = sum(self.parallel_efficiency_stats[-5:]) / 5
            older_avg = sum(self.parallel_efficiency_stats[-10:-5]) / 5
            if recent_avg > older_avg * 1.1:
                trend = 'improving'
            elif recent_avg < older_avg * 0.9:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        return {
            'total_computations': self.total_computations,
            'average_computation_time': avg_computation_time,
            'average_efficiency': avg_efficiency,
            'efficiency_trend': trend,
            'recent_efficiency': self.parallel_efficiency_stats[-5:] if len(self.parallel_efficiency_stats) >= 5 else self.parallel_efficiency_stats
        }
