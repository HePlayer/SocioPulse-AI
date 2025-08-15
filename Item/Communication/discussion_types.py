"""
讨论相关的数据类型定义
支持多Agent讨论模式的增强消息历史结构
"""

import uuid
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .message_types import ChatMessage, MessageType


class DiscussionPhase(Enum):
    """讨论阶段"""
    STARTING = "starting"        # 讨论开始
    ONGOING = "ongoing"          # 讨论进行中
    CONVERGING = "converging"    # 趋向一致
    ENDING = "ending"            # 讨论结束
    COMPLETED = "completed"      # 讨论完成


class TurnType(Enum):
    """发言类型"""
    INITIAL = "initial"          # 初始发言
    RESPONSE = "response"        # 回应发言
    SUPPLEMENT = "supplement"    # 补充发言
    CHALLENGE = "challenge"      # 质疑发言
    SUMMARY = "summary"          # 总结发言
    CLARIFICATION = "clarification"  # 澄清发言


@dataclass
class DiscussionTurn:
    """讨论轮次中的单次发言"""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    round_number: int = 0                    # 轮次编号
    turn_number: int = 0                     # 轮次内发言编号
    agent_id: str = ""                       # 发言Agent ID
    agent_name: str = ""                     # 发言Agent名称
    message: ChatMessage = None              # 消息内容
    turn_type: TurnType = TurnType.INITIAL   # 发言类型
    
    # 发言关系
    responding_to: Optional[str] = None      # 回应的发言ID
    triggered_by: Optional[List[str]] = None # 触发此发言的消息ID列表
    
    # 讨论上下文
    discussion_context: Dict[str, Any] = field(default_factory=dict)
    
    # SVR相关数据
    svr_values: Dict[str, float] = field(default_factory=lambda: {
        'stop_value': 0.0,
        'value_score': 50.0,
        'repeat_risk': 0.0
    })
    
    # 内容分析
    content_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # 时间戳
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'turn_id': self.turn_id,
            'round_number': self.round_number,
            'turn_number': self.turn_number,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'message': self.message.to_dict() if self.message else None,
            'turn_type': self.turn_type.value,
            'responding_to': self.responding_to,
            'triggered_by': self.triggered_by or [],
            'discussion_context': self.discussion_context,
            'svr_values': self.svr_values,
            'content_analysis': self.content_analysis,
            'timestamp': self.timestamp
        }


@dataclass
class DiscussionRound:
    """讨论轮次"""
    round_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    round_number: int = 0                    # 轮次编号
    topic: str = ""                          # 讨论主题
    phase: DiscussionPhase = DiscussionPhase.STARTING
    
    # 轮次内的发言
    turns: List[DiscussionTurn] = field(default_factory=list)
    
    # 参与者信息
    participants: List[str] = field(default_factory=list)  # Agent ID列表
    active_participants: List[str] = field(default_factory=list)  # 活跃参与者
    
    # 轮次统计
    total_turns: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # 轮次分析
    round_analysis: Dict[str, Any] = field(default_factory=dict)
    consensus_level: float = 0.0             # 共识程度 (0-1)
    content_coverage: float = 0.0            # 内容覆盖度 (0-1)
    
    def add_turn(self, turn: DiscussionTurn):
        """添加发言"""
        turn.round_number = self.round_number
        turn.turn_number = len(self.turns) + 1
        self.turns.append(turn)
        self.total_turns += 1
        
        # 更新活跃参与者
        if turn.agent_id not in self.active_participants:
            self.active_participants.append(turn.agent_id)
    
    def end_round(self):
        """结束轮次"""
        self.end_time = time.time()
        self.phase = DiscussionPhase.COMPLETED
    
    def get_duration(self) -> float:
        """获取轮次持续时间"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'round_id': self.round_id,
            'round_number': self.round_number,
            'topic': self.topic,
            'phase': self.phase.value,
            'turns': [turn.to_dict() for turn in self.turns],
            'participants': self.participants,
            'active_participants': self.active_participants,
            'total_turns': self.total_turns,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.get_duration(),
            'round_analysis': self.round_analysis,
            'consensus_level': self.consensus_level,
            'content_coverage': self.content_coverage
        }


@dataclass
class DiscussionSession:
    """完整的讨论会话"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    room_id: str = ""
    topic: str = ""
    
    # 讨论轮次
    rounds: List[DiscussionRound] = field(default_factory=list)
    current_round: Optional[DiscussionRound] = None
    
    # 会话状态
    phase: DiscussionPhase = DiscussionPhase.STARTING
    is_active: bool = True
    
    # 参与者管理
    all_participants: List[str] = field(default_factory=list)  # 所有参与过的Agent
    current_participants: List[str] = field(default_factory=list)  # 当前参与的Agent
    
    # 会话统计
    total_rounds: int = 0
    total_turns: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # 会话分析
    session_analysis: Dict[str, Any] = field(default_factory=dict)
    final_consensus: Optional[str] = None
    
    # SVR全局状态
    global_svr_state: Dict[str, Any] = field(default_factory=dict)
    
    def start_new_round(self, topic: str = "") -> DiscussionRound:
        """开始新轮次"""
        if self.current_round and self.current_round.phase != DiscussionPhase.COMPLETED:
            self.current_round.end_round()
        
        new_round = DiscussionRound(
            round_number=len(self.rounds) + 1,
            topic=topic or self.topic,
            participants=self.current_participants.copy()
        )
        
        self.rounds.append(new_round)
        self.current_round = new_round
        self.total_rounds += 1
        
        return new_round
    
    def add_turn(self, turn: DiscussionTurn):
        """添加发言到当前轮次"""
        if not self.current_round:
            self.start_new_round()
        
        self.current_round.add_turn(turn)
        self.total_turns += 1
        
        # 更新参与者列表
        if turn.agent_id not in self.all_participants:
            self.all_participants.append(turn.agent_id)
    
    def end_session(self):
        """结束讨论会话"""
        if self.current_round:
            self.current_round.end_round()
        
        self.end_time = time.time()
        self.phase = DiscussionPhase.COMPLETED
        self.is_active = False
    
    def get_duration(self) -> float:
        """获取会话持续时间"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def get_all_turns(self) -> List[DiscussionTurn]:
        """获取所有发言"""
        all_turns = []
        for round_obj in self.rounds:
            all_turns.extend(round_obj.turns)
        return all_turns
    
    def get_agent_turns(self, agent_id: str) -> List[DiscussionTurn]:
        """获取指定Agent的所有发言"""
        return [turn for turn in self.get_all_turns() if turn.agent_id == agent_id]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'room_id': self.room_id,
            'topic': self.topic,
            'rounds': [round_obj.to_dict() for round_obj in self.rounds],
            'current_round_id': self.current_round.round_id if self.current_round else None,
            'phase': self.phase.value,
            'is_active': self.is_active,
            'all_participants': self.all_participants,
            'current_participants': self.current_participants,
            'total_rounds': self.total_rounds,
            'total_turns': self.total_turns,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.get_duration(),
            'session_analysis': self.session_analysis,
            'final_consensus': self.final_consensus,
            'global_svr_state': self.global_svr_state
        }


class EnhancedMessageHistory:
    """增强的消息历史管理器"""
    
    def __init__(self):
        # 保持向后兼容的线性消息历史
        self.linear_history: List[ChatMessage] = []
        
        # 讨论会话管理
        self.discussion_sessions: Dict[str, DiscussionSession] = {}
        self.current_discussion: Optional[DiscussionSession] = None
        
        # 消息索引
        self.message_index: Dict[str, ChatMessage] = {}  # message_id -> ChatMessage
        self.turn_index: Dict[str, DiscussionTurn] = {}   # turn_id -> DiscussionTurn
    
    def add_message(self, message: ChatMessage, discussion_context: Optional[Dict[str, Any]] = None):
        """添加消息（兼容原有接口）"""
        # 添加到线性历史（保持向后兼容）
        self.linear_history.append(message)
        self.message_index[message.id] = message
        
        # 如果有讨论上下文，添加到讨论结构
        if discussion_context and self.current_discussion:
            turn = DiscussionTurn(
                agent_id=message.sender_id,
                agent_name=discussion_context.get('agent_name', ''),
                message=message,
                turn_type=TurnType(discussion_context.get('turn_type', 'response')),
                responding_to=discussion_context.get('responding_to'),
                triggered_by=discussion_context.get('triggered_by'),
                discussion_context=discussion_context,
                svr_values=discussion_context.get('svr_values', {}),
                content_analysis=discussion_context.get('content_analysis', {})
            )
            
            self.current_discussion.add_turn(turn)
            self.turn_index[turn.turn_id] = turn
    
    def start_discussion(self, room_id: str, topic: str, participants: List[str]) -> DiscussionSession:
        """开始新的讨论会话"""
        session = DiscussionSession(
            room_id=room_id,
            topic=topic,
            current_participants=participants.copy(),
            all_participants=participants.copy()
        )
        
        self.discussion_sessions[session.session_id] = session
        self.current_discussion = session
        
        return session
    
    def end_discussion(self) -> Optional[DiscussionSession]:
        """结束当前讨论"""
        if self.current_discussion:
            self.current_discussion.end_session()
            ended_session = self.current_discussion
            self.current_discussion = None
            return ended_session
        return None
    
    def get_linear_history(self, limit: int = 50) -> List[ChatMessage]:
        """获取线性消息历史（向后兼容）"""
        return self.linear_history[-limit:]
    
    def get_discussion_history(self, session_id: Optional[str] = None) -> Optional[DiscussionSession]:
        """获取讨论历史"""
        if session_id:
            return self.discussion_sessions.get(session_id)
        return self.current_discussion
    
    def get_svr_context(self, agent_id: str) -> Dict[str, Any]:
        """获取SVR算法所需的上下文信息"""
        if not self.current_discussion:
            return {}
        
        agent_turns = self.current_discussion.get_agent_turns(agent_id)
        all_turns = self.current_discussion.get_all_turns()
        
        return {
            'agent_turns': [turn.to_dict() for turn in agent_turns],
            'all_turns': [turn.to_dict() for turn in all_turns[-10:]],  # 最近10轮
            'current_round': self.current_discussion.current_round.to_dict() if self.current_discussion.current_round else None,
            'session_stats': {
                'total_rounds': self.current_discussion.total_rounds,
                'total_turns': self.current_discussion.total_turns,
                'duration': self.current_discussion.get_duration(),
                'participants': self.current_discussion.current_participants
            }
        }
    
    def clear(self):
        """清空历史记录"""
        self.linear_history.clear()
        self.discussion_sessions.clear()
        self.current_discussion = None
        self.message_index.clear()
        self.turn_index.clear()
