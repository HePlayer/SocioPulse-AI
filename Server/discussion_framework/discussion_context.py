"""
讨论上下文管理器
提供线程安全的讨论状态管理和实时数据访问
"""

import asyncio
import time
import threading
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from Item.Communication.discussion_types import (
    DiscussionSession, DiscussionTurn, DiscussionPhase, TurnType,
    EnhancedMessageHistory
)
from Item.Communication.message_types import ChatMessage, MessageType
from Item.Agentlib import Agent


@dataclass
class ContextSnapshot:
    """上下文快照，用于并行处理"""
    timestamp: float
    session_state: Dict[str, Any]
    recent_turns: List[DiscussionTurn]
    agent_states: Dict[str, Dict[str, Any]]
    global_metrics: Dict[str, float]


class DiscussionContext:
    """线程安全的讨论上下文管理器"""
    
    def __init__(self, session: DiscussionSession, participants: Dict[str, Agent]):
        self.session = session
        self.participants = participants.copy()

        # 设置日志
        self.logger = logging.getLogger(f"{__name__}.DiscussionContext")

        # 线程安全的数据结构
        self._lock = asyncio.Lock()
        self._context_history = deque(maxlen=100)  # 保留最近100个快照
        self._real_time_metrics = {}
        self._agent_performance_cache = {}

        # 状态跟踪
        self.is_active = True
        self.last_update_time = time.time()
        self.turn_counter = 0

        # 并行处理支持
        self.executor = ThreadPoolExecutor(max_workers=len(participants))

        # 记录初始化信息
        self.logger.info(f"DiscussionContext初始化: {len(participants)} 个参与者")
        self.logger.debug(f"参与者keys: {list(participants.keys())}")
        
    async def add_turn(self, turn: DiscussionTurn) -> None:
        """线程安全的轮次添加"""
        async with self._lock:
            self.session.add_turn(turn)
            self.turn_counter += 1
            self.last_update_time = time.time()
            
            # 更新实时指标
            await self._update_real_time_metrics(turn)
            
            # 创建上下文快照用于并行处理
            snapshot = await self._create_snapshot()
            self._context_history.append(snapshot)
    
    async def get_current_snapshot(self) -> ContextSnapshot:
        """获取当前上下文快照用于并行处理"""
        async with self._lock:
            return await self._create_snapshot()
    
    async def _create_snapshot(self) -> ContextSnapshot:
        """创建不可变的上下文快照"""
        recent_turns = self.session.get_all_turns()[-10:]  # 最近10轮
        
        agent_states = {}
        for agent_id, agent in self.participants.items():
            agent_states[agent_id] = {
                'name': agent.name,
                'role': agent.role.value,
                'status': getattr(agent, 'status', 'active'),
                'turn_count': len([t for t in recent_turns if t.agent_id == agent_id])
            }
        
        return ContextSnapshot(
            timestamp=time.time(),
            session_state={
                'session_id': self.session.session_id,
                'topic': self.session.topic,
                'phase': self.session.phase.value,
                'total_turns': self.session.total_turns,
                'total_rounds': self.session.total_rounds,
                'duration': self.session.get_duration()
            },
            recent_turns=recent_turns.copy(),
            agent_states=agent_states.copy(),
            global_metrics=self._real_time_metrics.copy()
        )
    
    async def _update_real_time_metrics(self, turn: DiscussionTurn):
        """更新实时讨论指标"""
        all_turns = self.session.get_all_turns()
        
        if len(all_turns) > 0:
            # 计算滚动平均值
            recent_svr_values = [t.svr_values for t in all_turns[-5:] if t.svr_values]
            
            if recent_svr_values:
                self._real_time_metrics.update({
                    'avg_stop_value': sum(svr.get('stop_value', 0) for svr in recent_svr_values) / len(recent_svr_values),
                    'avg_value_score': sum(svr.get('value_score', 0) for svr in recent_svr_values) / len(recent_svr_values),
                    'avg_repeat_risk': sum(svr.get('repeat_risk', 0) for svr in recent_svr_values) / len(recent_svr_values),
                    'participation_balance': self._calculate_participation_balance(),
                    'discussion_momentum': self._calculate_momentum()
                })
    
    def _calculate_participation_balance(self) -> float:
        """计算参与平衡度"""
        all_turns = self.session.get_all_turns()
        if not all_turns:
            return 1.0
        
        agent_turn_counts = {}
        for turn in all_turns:
            agent_turn_counts[turn.agent_id] = agent_turn_counts.get(turn.agent_id, 0) + 1
        
        if len(agent_turn_counts) <= 1:
            return 0.0
        
        # 计算变异系数（越低越平衡）
        counts = list(agent_turn_counts.values())
        mean_count = sum(counts) / len(counts)
        variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
        cv = (variance ** 0.5) / mean_count if mean_count > 0 else 0
        
        # 转换为平衡分数（1 = 完全平衡，0 = 完全不平衡）
        return max(0, 1 - cv)
    
    def _calculate_momentum(self) -> float:
        """基于最近活动计算讨论动量"""
        recent_turns = self.session.get_all_turns()[-5:]
        if len(recent_turns) < 2:
            return 0.5
        
        # 计算最近轮次之间的时间间隔
        intervals = []
        for i in range(1, len(recent_turns)):
            interval = recent_turns[i].timestamp - recent_turns[i-1].timestamp
            intervals.append(interval)
        
        if not intervals:
            return 0.5
        
        avg_interval = sum(intervals) / len(intervals)
        # 间隔越短动量越高（更活跃的讨论）
        # 标准化到0-1范围，假设60秒是"正常"节奏
        momentum = max(0, min(1, 1 - (avg_interval - 30) / 120))
        return momentum
    
    async def get_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """获取特定Agent的上下文用于SVR计算 - 增强调试版本"""
        async with self._lock:
            snapshot = await self._create_snapshot()

            agent_turns = [t for t in snapshot.recent_turns if t.agent_id == agent_id]
            other_turns = [t for t in snapshot.recent_turns if t.agent_id != agent_id]

            # 详细的调试日志
            self.logger.debug(f"获取Agent {agent_id} 上下文: 找到 {len(agent_turns)} 条历史发言")

            # 如果没有找到Agent的历史发言，提供详细的诊断信息
            if not agent_turns and snapshot.recent_turns:
                available_agent_ids = set(t.agent_id for t in snapshot.recent_turns)
                participants_keys = set(self.participants.keys())

                self.logger.warning(f"Agent {agent_id} 无历史发言记录")
                self.logger.warning(f"可用的agent_id: {available_agent_ids}")
                self.logger.warning(f"participants keys: {participants_keys}")

                # 检查ID不匹配情况（冷启动时这是正常的）
                if available_agent_ids and not available_agent_ids.intersection({agent_id}):
                    # 检查是否是正常的冷启动情况（只有system消息）
                    system_only_history = available_agent_ids == {"system"}

                    if system_only_history:
                        self.logger.debug(f"冷启动情况：Agent {agent_id} 尚未发言，历史记录只有system消息")
                        self.logger.debug(f"这是正常情况，将为Agent提供默认SVR上下文")
                    else:
                        self.logger.warning(f"Agent ID不匹配：请求的ID '{agent_id}' 不在历史记录中")
                        self.logger.warning(f"可用的agent_ids: {available_agent_ids}")
                        self.logger.warning(f"将为Agent提供默认上下文以继续SVR计算")

            # 记录成功的匹配情况
            elif agent_turns:
                self.logger.debug(f"成功匹配Agent {agent_id}: {len(agent_turns)} 条发言记录")

            return {
                'agent_id': agent_id,
                'agent_info': snapshot.agent_states.get(agent_id, {}),
                'agent_turns': agent_turns,
                'other_turns': other_turns,
                'session_state': snapshot.session_state,
                'global_metrics': snapshot.global_metrics,
                'context_snapshot': snapshot,
                # 新增：调试信息
                'debug_info': {
                    'agent_turns_count': len(agent_turns),
                    'other_turns_count': len(other_turns),
                    'total_recent_turns': len(snapshot.recent_turns),
                    'available_agent_ids': list(set(t.agent_id for t in snapshot.recent_turns)),
                    'participants_keys': list(self.participants.keys())
                }
            }
    
    async def cleanup(self):
        """清理资源"""
        self.is_active = False
        self.executor.shutdown(wait=True)
