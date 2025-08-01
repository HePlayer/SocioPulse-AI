"""
连续讨论控制器
实现连续循环架构和并行SVR计算的主控制器
"""

import asyncio
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json

from .discussion_context import DiscussionContext
from .parallel_svr_engine import ParallelSVREngine, ParallelSVRResult
from .svr_handler import SVRHandler, SVRDecision, DiscussionAction
from Item.Communication.discussion_types import DiscussionSession, DiscussionTurn, TurnType
from Item.Communication.message_types import ChatMessage, MessageType
# 注意：这些导入在实际使用时可能需要，但为了避免循环导入，我们暂时注释掉
# from Item.Communication.strategy_factory import CommunicationStrategyFactory
# from Item.Communication.base_strategy import CommunicationContext
from Item.Agentlib import Agent
from Server.config import WS_MESSAGE_TYPES


class DiscussionState(Enum):
    """讨论控制器状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class DiscussionMetrics:
    """实时讨论指标"""
    total_turns: int = 0
    total_svr_computations: int = 0
    average_svr_computation_time: float = 0.0
    discussion_quality_trend: List[float] = field(default_factory=list)
    participant_engagement: Dict[str, float] = field(default_factory=dict)
    last_update_time: float = field(default_factory=time.time)


@dataclass
class DiscussionEvent:
    """用于实时更新的讨论事件"""
    event_type: str
    timestamp: float
    data: Dict[str, Any]
    session_id: str


class ContinuousDiscussionController:
    """
    完整的连续讨论控制器，具有并行SVR和实时监控
    """
    
    def __init__(self, 
                 svr_engine: Optional[ParallelSVREngine] = None,
                 svr_handler: Optional[SVRHandler] = None,
                 max_turns: int = 50,
                 max_duration: int = 3600,
                 svr_computation_interval: float = 5.0,
                 enable_real_time_updates: bool = True):
        
        # 核心组件
        self.svr_engine = svr_engine or ParallelSVREngine()
        self.svr_handler = svr_handler or SVRHandler()
        
        # 配置
        self.max_turns = max_turns
        self.max_duration = max_duration
        self.svr_computation_interval = svr_computation_interval
        self.enable_real_time_updates = enable_real_time_updates
        
        # 状态管理
        self.state = DiscussionState.IDLE
        self.context: Optional[DiscussionContext] = None
        self.participants: Dict[str, Agent] = {}
        
        # 控制流
        self.is_running = False
        self.should_stop = False
        self.should_pause = False
        self.main_loop_task: Optional[asyncio.Task] = None
        self.svr_monitor_task: Optional[asyncio.Task] = None
        
        # 实时监控
        self.metrics = DiscussionMetrics()
        self.last_svr_result: Optional[ParallelSVRResult] = None
        self.last_decision: Optional[SVRDecision] = None
        
        # 实时更新的事件系统
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_subscribers: List[Callable] = []
        
        # 与现有系统集成
        self.communication_strategy = None
        self.enhanced_history = None
        
        # 事件回调
        self.on_discussion_start: Optional[Callable] = None
        self.on_discussion_end: Optional[Callable] = None
        self.on_turn_complete: Optional[Callable] = None
        self.on_svr_update: Optional[Callable] = None
        self.on_decision_made: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # WebSocket广播支持
        self.websocket_handler = None
        self.room_id = None
        
        # 错误处理
        self.error_count = 0
        self.max_errors = 5
        
        # 日志记录
        self.logger = logging.getLogger(self.__class__.__name__)

        # 添加Agent ID管理器
        from .agent_id_manager import AgentIDManager
        self.agent_id_manager = AgentIDManager()
    
    async def start_discussion(self, 
                             room_id: str,
                             topic: str,
                             participants: Dict[str, Agent],
                             initial_message: ChatMessage,
                             enhanced_history=None,
                             communication_strategy=None) -> Dict[str, Any]:
        """
        启动连续讨论循环
        """
        
        if self.state != DiscussionState.IDLE:
            return {
                'success': False,
                'error': f'控制器不是空闲状态 (当前状态: {self.state.value})'
            }
        
        try:
            self.state = DiscussionState.INITIALIZING
            self.logger.info(f"启动讨论: {topic}")

            # 🔧 CRITICAL FIX: 标准化participants ID
            self.logger.info("🔧 开始Agent ID标准化...")
            original_count = len(participants)

            # 诊断原始participants状态
            self.agent_id_manager.log_diagnosis(participants)

            # 验证原始ID一致性
            is_consistent = self.agent_id_manager.validate_participants_consistency(participants)
            if not is_consistent:
                self.logger.warning("检测到Agent ID不一致，开始标准化...")

            # 标准化participants
            normalized_participants = self.agent_id_manager.normalize_participants(participants)

            self.logger.info(f"✅ Agent ID标准化完成: {original_count} → {len(normalized_participants)} 个Agent")

            # 详细记录标准化后的participants信息
            self.logger.info(f"标准化后的参与者: 共 {len(normalized_participants)} 个Agent")
            for key, agent in normalized_participants.items():
                self.logger.debug(f"  标准化参与者: key='{key}' → Agent名称='{agent.name}', component_id='{agent.component_id}'")

                # 验证标准化结果
                if key == agent.component_id:
                    self.logger.debug(f"    ✓ ID一致性验证通过")
                else:
                    self.logger.error(f"    ✗ 标准化失败: key='{key}' ≠ component_id='{agent.component_id}'")
                    raise ValueError(f"Agent ID标准化失败: {key} ≠ {agent.component_id}")

            # 存储集成组件
            self.enhanced_history = enhanced_history
            self.communication_strategy = communication_strategy

            # 初始化上下文
            session = DiscussionSession(
                room_id=room_id,
                topic=topic,
                current_participants=list(normalized_participants.keys()),
                all_participants=list(normalized_participants.keys())
            )

            # 🔧 CRITICAL FIX: 使用标准化后的participants
            self.context = DiscussionContext(session, normalized_participants)
            self.participants = normalized_participants.copy()
            
            # 添加初始系统消息到上下文（避免与participants UUID冲突）
            initial_turn = DiscussionTurn(
                agent_id="system",  # 使用"system"而不是"user"避免ID冲突
                agent_name="System",
                message=initial_message,
                turn_type=TurnType.INITIAL,
                discussion_context={
                    'initial_message': True,
                    'original_sender': 'user',  # 保留原始发送者信息
                    'id_fix_applied': True  # 标记已应用ID修复
                }
            )
            
            await self.context.add_turn(initial_turn)
            
            # 重置状态
            self.metrics = DiscussionMetrics()
            self.should_stop = False
            self.should_pause = False
            self.error_count = 0
            
            # 启动连续循环
            self.state = DiscussionState.RUNNING
            self.is_running = True

            # 验证WebSocket处理器设置状态
            self.logger.info(f"🔍 验证WebSocket处理器设置状态:")
            if self.websocket_handler and self.room_id:
                self.logger.info(f"  ✅ WebSocket处理器: 已设置")
                self.logger.info(f"  ✅ 房间ID: {self.room_id}")
                self.logger.info(f"  ✅ Agent响应将能够广播到前端")
            else:
                self.logger.warning(f"  ⚠️ WebSocket处理器设置不完整:")
                self.logger.warning(f"    websocket_handler: {'✓' if self.websocket_handler else '✗'}")
                self.logger.warning(f"    room_id: {'✓' if self.room_id else '✗'}")
                self.logger.warning(f"    Agent响应可能无法到达前端!")

            # 启动主讨论循环
            self.main_loop_task = asyncio.create_task(
                self._continuous_discussion_loop(),
                name="discussion_main_loop"
            )

            # 启动并行SVR监控
            self.svr_monitor_task = asyncio.create_task(
                self._svr_monitoring_loop(),
                name="svr_monitor_loop"
            )
            
            # 触发启动事件
            await self._emit_event("discussion_started", {
                'session_id': session.session_id,
                'topic': topic,
                'participants': list(participants.keys())
            })
            
            if self.on_discussion_start:
                await self.on_discussion_start(session)
            
            return {
                'success': True,
                'session_id': session.session_id,
                'state': self.state.value,
                'participants': list(participants.keys())
            }
            
        except Exception as e:
            self.state = DiscussionState.ERROR
            self.logger.error(f"启动讨论失败: {e}")
            
            if self.on_error:
                await self.on_error(e)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _continuous_discussion_loop(self):
        """
        主连续讨论循环，实现伪代码:
        
        WHILE TRUE:
            svr_results = computeSVR(context, all_agents)
            operation, selected_agent = SVRhandler(svr_results)
            
            IF operation == 'stop':
                break
            ELSE IF operation == 'continue':
                response = selected_agent.talk(context)
                context.add(response)
        """
        
        self.logger.info("启动连续讨论循环")
        
        try:
            while self.is_running and not self.should_stop:
                
                # 检查暂停条件
                if self.should_pause:
                    self.state = DiscussionState.PAUSED
                    await self._emit_event("discussion_paused", {})
                    
                    # 等待恢复
                    while self.should_pause and not self.should_stop:
                        await asyncio.sleep(0.1)
                    
                    if not self.should_stop:
                        self.state = DiscussionState.RUNNING
                        await self._emit_event("discussion_resumed", {})
                
                # 检查终止条件
                if await self._should_terminate():
                    break
                
                # 步骤1：为所有Agent计算SVR（并行）
                try:
                    # 定期检查WebSocket处理器状态（每5轮检查一次）
                    if self.metrics.total_svr_computations % 5 == 0:
                        self.logger.info(f"🔍 定期WebSocket状态检查 (第{self.metrics.total_svr_computations + 1}次SVR计算):")
                        if self.websocket_handler and self.room_id:
                            self.logger.info(f"  ✅ WebSocket处理器状态正常")
                        else:
                            self.logger.warning(f"  ⚠️ WebSocket处理器状态异常:")
                            self.logger.warning(f"    websocket_handler: {'✓' if self.websocket_handler else '✗'}")
                            self.logger.warning(f"    room_id: {'✓' if self.room_id else '✗'}")

                    svr_results = await self.svr_engine.compute_parallel_svr(
                        self.context, self.participants
                    )
                    self.last_svr_result = svr_results
                    self.metrics.total_svr_computations += 1

                    # 记录主循环SVR计算时间（用于监控循环协调）
                    self._last_main_svr_time = time.time()

                    # 简化SVR计算日志输出
                    global_metrics = svr_results.global_svr_metrics
                    self.logger.info(f"简化SVR计算完成: "
                                   f"全局停止平均={global_metrics.get('global_stop_average', 0.0):.3f}, "
                                   f"讨论质量={global_metrics.get('discussion_quality', 50.0):.1f}, "
                                   f"参与Agent数={global_metrics.get('agent_count', 0)}")

                    # 更新指标
                    await self._update_metrics(svr_results)

                    # 发出SVR更新事件
                    await self._emit_event("svr_computed", {
                        'global_metrics': svr_results.global_svr_metrics,
                        'computation_stats': svr_results.computation_stats
                    })

                    if self.on_svr_update:
                        await self.on_svr_update(svr_results)
                
                except Exception as e:
                    self.logger.error(f"SVR计算失败: {e}")
                    await self._handle_error(e)
                    continue
                
                # 步骤2：处理SVR结果并做决策
                try:
                    decision = await self.svr_handler.process_svr_results(
                        svr_results, self.context, self.participants
                    )
                    self.last_decision = decision

                    # 详细记录决策结果
                    self.logger.info(f"✅ SVR决策完成:")
                    self.logger.info(f"  决策动作: {decision.action.value}")
                    self.logger.info(f"  选择的Agent: {decision.selected_agent_name} (ID: {decision.selected_agent_id})")
                    self.logger.info(f"  决策置信度: {decision.confidence:.2f}")

                    # 记录V值选择详情
                    if decision.metadata and 'selected_v_value' in decision.metadata:
                        selected_v_value = decision.metadata['selected_v_value']
                        self.logger.info(f"  选择依据: V值={selected_v_value:.1f} (最高)")

                    # 如果是CONTINUE决策，验证Agent选择
                    if decision.action == DiscussionAction.CONTINUE:
                        if decision.selected_agent_id:
                            if decision.selected_agent_id in self.participants:
                                self.logger.info(f"  ✓ Agent选择验证通过，准备执行发言")
                            else:
                                self.logger.error(f"  ✗ Agent选择验证失败: {decision.selected_agent_id} 不在participants中")
                        else:
                            self.logger.error(f"  ✗ Agent选择失败: selected_agent_id为None")

                    # 发出决策事件
                    await self._emit_event("decision_made", {
                        'action': decision.action.value,
                        'selected_agent': decision.selected_agent_name,
                        'confidence': decision.confidence,
                        'reasoning': decision.reasoning
                    })

                    if self.on_decision_made:
                        await self.on_decision_made(decision)
                
                except Exception as e:
                    self.logger.error(f"决策制定失败: {e}")
                    await self._handle_error(e)
                    continue
                
                # 步骤3：执行决策
                if decision.action == DiscussionAction.STOP:
                    decision_basis = decision.metadata.get('decision_basis', 'unknown')
                    stop_reason = decision.metadata.get('stop_reason', 'unknown')
                    global_stop_avg = decision.metadata.get('global_stop_average', 0.0)
                    self.logger.info(f"决策: 停止讨论 (基于: {decision_basis}, 原因: {stop_reason}, S值平均: {global_stop_avg:.3f})")
                    break
                
                elif decision.action == DiscussionAction.CONTINUE:
                    if decision.selected_agent_id and decision.selected_agent_id in self.participants:
                        try:
                            selected_agent = self.participants[decision.selected_agent_id]

                            self.logger.info(f"🗣️ 执行Agent发言:")
                            self.logger.info(f"  选择的Agent ID: {decision.selected_agent_id}")
                            self.logger.info(f"  Agent名称: {selected_agent.name}")
                            self.logger.info(f"  当前轮次: 第{self.metrics.total_turns + 1}轮")

                            # 分隔线，便于在日志中识别
                            self.logger.info(f"{'='*60}")
                            self.logger.info(f"🚀 开始 {selected_agent.name} 的推理过程")
                            self.logger.info(f"{'='*60}")

                            # Agent发言
                            response = await self._agent_talk(selected_agent, decision)

                            # 发言完成标识
                            self.logger.info(f"{'='*60}")
                            self.logger.info(f"🏁 {selected_agent.name} 的推理过程完成")
                            self.logger.info(f"{'='*60}")

                            if response:
                                self.logger.info(f"✅ Agent发言成功:")
                                self.logger.info(f"  发言内容长度: {len(response.message.content)} 字符")
                                self.logger.info(f"  Agent ID: {response.agent_id}")
                                self.logger.info(f"  添加到讨论历史")

                                # 添加响应到上下文
                                await self.context.add_turn(response)
                                self.metrics.total_turns += 1

                                self.logger.info(f"  讨论轮次更新: 第{self.metrics.total_turns}轮")
                                self.logger.info(f"  准备下一轮SVR计算和Agent选择")
                                self.logger.info(f"  Agent发言内容长度: {len(response.message.content)} 字符")

                                # 与增强历史集成（如果可用）
                                if self.enhanced_history:
                                    await self._integrate_with_enhanced_history(response)

                                # 发出轮次完成事件
                                await self._emit_event("turn_completed", {
                                    'agent_id': response.agent_id,
                                    'agent_name': response.agent_name,
                                    'content': response.message.content,
                                    'turn_number': self.metrics.total_turns
                                })

                                # 广播Agent响应到WebSocket
                                self.logger.info(f"📡 准备广播Agent响应到前端...")
                                await self._broadcast_agent_response(response)

                                if self.on_turn_complete:
                                    await self.on_turn_complete(response)

                                self.logger.info(f"✅ Agent发言流程完成，准备下一轮SVR计算")
                                self.logger.info(f"  Agent: {response.agent_name}")
                                self.logger.info(f"  轮次: 第{self.metrics.total_turns}轮")
                                self.logger.info(f"  WebSocket广播: 已执行")
                            else:
                                self.logger.error(f"✗ Agent发言失败: _agent_talk返回None")
                                await self._handle_error(Exception("Agent发言返回空响应"))
                                continue

                        except Exception as e:
                            self.logger.error(f"Agent发言过程异常: {e}")
                            await self._handle_error(e)
                            continue
                    else:
                        # 这种情况不应该发生，因为我们已经在决策阶段验证过
                        if not decision.selected_agent_id:
                            self.logger.error("严重错误: CONTINUE决策但selected_agent_id为None")
                        else:
                            self.logger.error(f"严重错误: 选择的Agent {decision.selected_agent_id} 不在participants中")

                        # 触发暂停以避免无限循环
                        self.should_pause = True
                
                elif decision.action == DiscussionAction.PAUSE:
                    # 详细诊断暂停原因
                    pause_reason = decision.metadata.get('pause_reason', 'unknown')
                    self.logger.warning(f"决策: 暂停讨论 (原因: {pause_reason})")

                    # 如果是因为Agent选择失败，提供详细诊断
                    if pause_reason == 'no_suitable_agent':
                        self.logger.error("=== Agent选择失败完整诊断 ===")
                        self.logger.error(f"当前participants数量: {len(self.participants)}")
                        self.logger.error(f"participants keys: {list(self.participants.keys())}")

                        # 检查SVR结果
                        if hasattr(self, 'last_svr_result') and self.last_svr_result:
                            agent_results = self.last_svr_result.agent_results
                            self.logger.error(f"SVR agent_results数量: {len(agent_results) if agent_results else 0}")
                            if agent_results:
                                self.logger.error(f"SVR agent_results keys: {list(agent_results.keys())}")

                                # 检查ID匹配情况
                                agent_results_keys = set(agent_results.keys())
                                participants_keys = set(self.participants.keys())
                                matched_keys = agent_results_keys.intersection(participants_keys)

                                self.logger.error(f"ID匹配分析:")
                                self.logger.error(f"  agent_results keys: {agent_results_keys}")
                                self.logger.error(f"  participants keys: {participants_keys}")
                                self.logger.error(f"  匹配的keys: {matched_keys}")
                                self.logger.error(f"  匹配数量: {len(matched_keys)}")

                                if not matched_keys:
                                    self.logger.error("根本原因: agent_results与participants的key完全不匹配")
                                    self.logger.error("这导致所有Agent在选择阶段被跳过")
                            else:
                                self.logger.error("SVR agent_results为空，SVR计算可能失败")
                        else:
                            self.logger.error("last_svr_result不存在，SVR计算可能未执行")

                        self.logger.error("=== 诊断结束 ===")

                    self.should_pause = True
                
                elif decision.action == DiscussionAction.REDIRECT:
                    self.logger.info("决策: 重定向讨论")
                    # 处理重定向逻辑
                    await self._handle_redirection(decision)
                
                # 小延迟防止紧密循环
                await asyncio.sleep(0.1)
        
        except Exception as e:
            self.logger.error(f"讨论循环中的关键错误: {e}")
            self.state = DiscussionState.ERROR
            if self.on_error:
                await self.on_error(e)
        
        finally:
            await self._cleanup_discussion()

    async def _svr_monitoring_loop(self):
        """
        用于实时更新的并行SVR监控循环
        """

        self.logger.info("启动SVR监控循环")

        try:
            while self.is_running and not self.should_stop:

                if self.state == DiscussionState.RUNNING and self.context and not self.should_pause:
                    try:
                        # 检查是否需要进行监控计算（避免与主循环重复）
                        time_since_last_svr = time.time() - getattr(self, '_last_main_svr_time', 0)

                        # 只有在主循环SVR计算后一定时间才进行监控计算
                        if time_since_last_svr > self.svr_computation_interval * 2:
                            # 为监控计算SVR（较轻的计算）
                            svr_results = await self.svr_engine.compute_parallel_svr(
                                self.context, self.participants
                            )

                            # 更新实时指标
                            await self._update_real_time_metrics(svr_results)

                            # 发出监控更新
                            if self.enable_real_time_updates:
                                await self._emit_event("svr_monitor_update", {
                                    'global_metrics': svr_results.global_svr_metrics,
                                    'timestamp': time.time()
                                })

                            self.logger.debug("SVR监控计算完成")
                        else:
                            self.logger.debug(f"跳过监控SVR计算，距离主循环计算仅{time_since_last_svr:.1f}秒")

                    except Exception as e:
                        self.logger.warning(f"SVR监控错误: {e}")

                # 等待下一个监控周期
                await asyncio.sleep(self.svr_computation_interval)

        except Exception as e:
            self.logger.error(f"SVR监控循环错误: {e}")

    def _get_agent_key_from_participants(self, agent: Agent) -> str:
        """获取Agent在participants字典中对应的key - 简化可靠版本"""

        # 🔧 CRITICAL FIX: 使用Agent ID管理器进行查找
        key, found_agent = self.agent_id_manager.get_agent_by_any_id(self.participants, agent.component_id)

        if key and found_agent:
            self.logger.debug(f"成功找到Agent {agent.name} 对应的key: {key}")
            return key

        # 如果找不到，说明存在严重的系统错误
        self.logger.error(f"严重系统错误：Agent {agent.name} (component_id: {agent.component_id}) 不在participants中")
        self.logger.error(f"可用的participants keys: {list(self.participants.keys())}")
        self.logger.error(f"可用的participants component_ids: {[p.component_id for p in self.participants.values()]}")

        # 记录详细诊断信息
        self.agent_id_manager.log_diagnosis(self.participants)

        # 抛出异常而不是返回可能错误的ID
        raise ValueError(f"Agent ID匹配失败: {agent.component_id} 不在participants中")

    async def _agent_talk(self, agent: Agent, decision: SVRDecision) -> Optional[DiscussionTurn]:
        """
        使用现有的Agent.think()接口让Agent发言
        """

        try:
            # 获取与participants字典一致的agent_id
            consistent_agent_id = self._get_agent_key_from_participants(agent)

            # 详细记录Agent发言开始
            self.logger.info(f"🎯 开始Agent发言流程:")
            self.logger.info(f"  选择的Agent: {agent.name} (ID: {agent.component_id})")
            self.logger.debug(f"  选择的consistent_agent_id: {consistent_agent_id}")
            self.logger.debug(f"  ID匹配成功: {consistent_agent_id in self.participants}")

            # 为Agent准备上下文
            snapshot = await self.context.get_current_snapshot()

            # 构建与Agent.think()兼容的输入数据
            input_data = {
                'user_input': self._build_agent_prompt(snapshot, decision),
                'room_context': {
                    'room_id': snapshot.session_state['session_id'],
                    'room_name': f"讨论: {snapshot.session_state.get('topic', 'Unknown')}",
                    'message_history': [
                        {
                            'sender_id': turn.agent_id,
                            'content': turn.message.content,
                            'timestamp': turn.timestamp
                        }
                        for turn in snapshot.recent_turns[-5:]  # 最近5轮
                    ],
                    'discussion_mode': True,
                    'available_agents': list(self.participants.keys()),
                    'discussion_context': {
                        'total_participants': len(self.participants),
                        'discussion_turn': snapshot.session_state['total_turns'] + 1,
                        'discussion_status': 'ongoing',
                        'svr_guidance': {
                            'expected_value': decision.metadata.get('agent_svr_values', {}).get('value_score', 50),
                            'avoid_repetition': decision.metadata.get('agent_svr_values', {}).get('repeat_risk', 0) > 0.5
                        }
                    }
                }
            }

            self.logger.info(f"  📋 输入数据准备完成，开始调用Agent.think()")

            # 调用agent.think()
            result = await agent.think(input_data)

            self.logger.info(f"  🔄 Agent.think() 调用完成，结果: {result.get('success', False)}")

            if result.get('success', False):
                response_content = result.get('response', '')

                # 创建讨论轮次 - 使用一致的agent_id
                turn = DiscussionTurn(
                    agent_id=consistent_agent_id,  # 使用与participants一致的ID
                    agent_name=agent.name,
                    message=ChatMessage(
                        sender_id=consistent_agent_id,  # 保持一致性
                        content=response_content,
                        message_type=MessageType.TEXT,
                        metadata={
                            'agent_name': agent.name,
                            'decision_confidence': decision.confidence,
                            'svr_guided': True,
                            'original_component_id': agent.component_id  # 保留原始ID用于调试
                        }
                    ),
                    turn_type=self._determine_turn_type(snapshot, consistent_agent_id),
                    discussion_context={
                        'decision_reasoning': decision.reasoning,
                        'svr_values': decision.metadata.get('agent_svr_values', {}),
                        'response_to_guidance': True,
                        'agent_id_source': 'participants_key'  # 标记ID来源
                    }
                )

                # 详细记录Agent发言成功
                self.logger.info(f"✅ Agent发言成功: {agent.name}")
                self.logger.info(f"  📝 响应内容长度: {len(response_content)} 字符")
                self.logger.info(f"  🆔 使用agent_id: {consistent_agent_id}")
                self.logger.debug(f"  原始component_id: {agent.component_id}")
                self.logger.info(f"  📄 响应预览: {response_content[:100]}{'...' if len(response_content) > 100 else ''}")

                # 验证创建的turn的agent_id是否在participants中
                if consistent_agent_id in self.participants:
                    self.logger.debug(f"  ✓ agent_id在participants中，SVR计算应该能找到历史记录")
                else:
                    self.logger.error(f"  ✗ agent_id不在participants中，可能导致SVR计算失败")

                self.logger.info(f"  🎯 DiscussionTurn创建完成，准备返回")
                return turn

            else:
                error_msg = result.get('error', 'Unknown error')
                self.logger.error(f"❌ Agent {agent.name} 生成响应失败:")
                self.logger.error(f"  错误信息: {error_msg}")
                self.logger.error(f"  Agent.think()返回的完整结果: {result}")
                return None

        except Exception as e:
            self.logger.error(f"🚨 Agent {agent.name} 发言过程发生异常:")
            self.logger.error(f"  异常类型: {type(e).__name__}")
            self.logger.error(f"  异常详情: {str(e)}")
            self.logger.error(f"  Agent状态: {agent.status.value if hasattr(agent, 'status') else 'Unknown'}")
            return None

    def _build_agent_prompt(self, snapshot, decision: SVRDecision) -> str:
        """
        基于当前上下文和SVR指导为Agent构建提示
        """

        # 获取最近的讨论上下文
        recent_turns = snapshot.recent_turns[-3:] if snapshot.recent_turns else []
        context_summary = []

        for turn in recent_turns:
            if turn.agent_id != "user":
                context_summary.append(f"{turn.agent_name}: {turn.message.content[:100]}...")

        # 基于SVR值构建指导
        guidance = []
        if decision.metadata.get('agent_svr_values'):
            svr_values = decision.metadata['agent_svr_values']

            if svr_values.get('repeat_risk', 0) > 0.5:
                guidance.append("请避免重复之前的观点，尝试提出新的见解")

            if svr_values.get('value_score', 50) < 40:
                guidance.append("请提供更有价值和深度的内容")

            if decision.confidence < 0.6:
                guidance.append("请确保你的回应与讨论主题密切相关")

        # 构建提示
        prompt_parts = [
            f"当前讨论主题: {snapshot.session_state.get('topic', '未知主题')}",
            "",
            "最近的讨论内容:",
        ]

        if context_summary:
            prompt_parts.extend(context_summary)
        else:
            prompt_parts.append("(讨论刚开始)")

        prompt_parts.extend([
            "",
            "请基于以上讨论内容，提供你的观点和见解。"
        ])

        if guidance:
            prompt_parts.extend([
                "",
                "特别注意:",
                *[f"- {g}" for g in guidance]
            ])

        return "\n".join(prompt_parts)

    def _determine_turn_type(self, snapshot, agent_id: str) -> TurnType:
        """
        基于上下文确定轮次类型
        """

        recent_turns = snapshot.recent_turns[-5:] if snapshot.recent_turns else []

        # 检查此Agent是否之前发过言
        agent_previous_turns = [t for t in recent_turns if t.agent_id == agent_id]

        if not agent_previous_turns:
            return TurnType.INITIAL

        # 检查是否在回应最近的轮次
        if recent_turns and recent_turns[-1].agent_id != agent_id:
            return TurnType.RESPONSE

        return TurnType.SUPPLEMENT

    async def _should_terminate(self) -> bool:
        """
        基于各种条件检查讨论是否应该终止
        """

        if not self.context:
            return True

        snapshot = await self.context.get_current_snapshot()

        # 检查轮次限制
        if snapshot.session_state['total_turns'] >= self.max_turns:
            self.logger.info(f"终止: 达到最大轮次 ({self.max_turns})")
            return True

        # 检查时间限制
        if snapshot.session_state['duration'] >= self.max_duration:
            self.logger.info(f"终止: 达到最大持续时间 ({self.max_duration}s)")
            return True

        # 检查错误计数
        if self.error_count >= self.max_errors:
            self.logger.error(f"终止: 错误过多 ({self.error_count})")
            return True

        return False

    async def _handle_error(self, error: Exception):
        """
        处理讨论循环中的错误
        """

        self.error_count += 1
        self.logger.error(f"讨论错误 ({self.error_count}/{self.max_errors}): {error}")

        await self._emit_event("error_occurred", {
            'error': str(error),
            'error_count': self.error_count,
            'max_errors': self.max_errors
        })

        # 添加延迟防止错误垃圾邮件
        await asyncio.sleep(1.0)

    async def _handle_redirection(self, decision: SVRDecision):
        """
        处理讨论重定向
        """

        # 这可能涉及改变主题、引入新上下文等
        self.logger.info(f"重定向讨论: {decision.reasoning}")

        await self._emit_event("discussion_redirected", {
            'reason': decision.reasoning,
            'selected_agent': decision.selected_agent_name
        })

    async def _update_metrics(self, svr_results: ParallelSVRResult):
        """
        更新讨论指标
        """

        # 更新计算时间
        comp_time = svr_results.computation_stats.get('total_time', 0)
        total_comps = self.metrics.total_svr_computations

        if total_comps > 0:
            self.metrics.average_svr_computation_time = (
                (self.metrics.average_svr_computation_time * (total_comps - 1) + comp_time) / total_comps
            )
        else:
            self.metrics.average_svr_computation_time = comp_time

        # 更新质量趋势
        quality = svr_results.global_svr_metrics.get('discussion_quality', 50.0)
        self.metrics.discussion_quality_trend.append(quality)

        # 只保留最近20次质量测量
        if len(self.metrics.discussion_quality_trend) > 20:
            self.metrics.discussion_quality_trend = self.metrics.discussion_quality_trend[-20:]

        # 更新参与者参与度
        for agent_id, result in svr_results.agent_results.items():
            engagement = result.svr_values.get('composite_score', 50.0) / 100.0
            self.metrics.participant_engagement[agent_id] = engagement

        self.metrics.last_update_time = time.time()

    async def _update_real_time_metrics(self, svr_results: ParallelSVRResult):
        """
        为监控更新实时指标
        """

        # 这是用于实时监控的指标更新的轻量版本
        quality = svr_results.global_svr_metrics.get('discussion_quality', 50.0)

        # 更新参与度分数
        for agent_id, result in svr_results.agent_results.items():
            engagement = result.svr_values.get('composite_score', 50.0) / 100.0
            self.metrics.participant_engagement[agent_id] = engagement

    async def _integrate_with_enhanced_history(self, turn: DiscussionTurn):
        """
        与现有的EnhancedMessageHistory系统集成
        """

        if self.enhanced_history:
            try:
                discussion_context = {
                    'agent_name': turn.agent_name,
                    'turn_type': turn.turn_type.value,
                    'discussion_mode': True,
                    'svr_values': getattr(turn, 'svr_values', {}),
                    'content_analysis': getattr(turn, 'content_analysis', {}),
                    'responding_to': getattr(turn, 'responding_to', None),
                    'triggered_by': getattr(turn, 'triggered_by', None)
                }

                self.enhanced_history.add_message(turn.message, discussion_context)

            except Exception as e:
                self.logger.warning(f"与增强历史集成失败: {e}")

    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """
        发出实时更新事件
        """

        if not self.enable_real_time_updates:
            return

        event = DiscussionEvent(
            event_type=event_type,
            timestamp=time.time(),
            data=data,
            session_id=self.context.session.session_id if self.context else "unknown"
        )

        try:
            await self.event_queue.put(event)

            # 通知订阅者
            for subscriber in self.event_subscribers:
                try:
                    if asyncio.iscoroutinefunction(subscriber):
                        await subscriber(event)
                    else:
                        subscriber(event)
                except Exception as e:
                    self.logger.warning(f"事件订阅者错误: {e}")

        except Exception as e:
            self.logger.warning(f"发出事件失败: {e}")

    async def _broadcast_agent_response(self, turn):
        """广播Agent响应到WebSocket连接"""
        # 详细的状态检查和错误报告
        self.logger.info(f"📡 开始广播Agent响应:")
        self.logger.info(f"  Agent: {turn.agent_name}")
        self.logger.info(f"  消息长度: {len(turn.message.content)} 字符")

        # 检查WebSocket处理器状态
        if not self.websocket_handler:
            self.logger.error(f"🚫 WebSocket广播失败: websocket_handler为None")
            self.logger.error(f"  Agent: {turn.agent_name}")
            self.logger.error(f"  这意味着WebSocket处理器未正确设置或已失效")
            self.logger.error(f"  Agent的响应将无法到达前端!")
            return

        if not self.room_id:
            self.logger.error(f"🚫 WebSocket广播失败: room_id为None")
            self.logger.error(f"  Agent: {turn.agent_name}")
            self.logger.error(f"  这意味着房间ID未正确设置")
            self.logger.error(f"  Agent的响应将无法到达前端!")
            return

        # 状态验证通过
        self.logger.info(f"  ✅ WebSocket处理器状态: 正常")
        self.logger.info(f"  ✅ 房间ID: {self.room_id}")

        try:
            # 🔧 CRITICAL FIX: 构建与前端完全兼容的WebSocket消息格式
            message_id = turn.message.id if hasattr(turn.message, 'id') else str(uuid.uuid4())
            timestamp = turn.message.timestamp.isoformat() if hasattr(turn.message, 'timestamp') else datetime.now().isoformat()

            agent_message = {
                'type': WS_MESSAGE_TYPES['NEW_MESSAGE'],
                'room_id': self.room_id,
                'message_id': message_id,  # 🔧 添加顶级message_id用于去重
                'agent_name': turn.agent_name,  # 🔧 添加顶级agent_name字段
                'message': {
                    'id': message_id,
                    'message_id': message_id,  # 🔧 双重保险
                    'sender': turn.agent_name,  # 🔧 使用agent名称而不是'agent'
                    'sender_id': turn.agent_id,
                    'content': turn.message.content,
                    'timestamp': timestamp,
                    'message_type': 'text',  # 🔧 改为'text'以匹配前端期望
                    'sender_type': 'agent',  # 🔧 明确标识为agent消息
                    'agent_name': turn.agent_name,  # 🔧 在message内部也添加agent_name
                    'metadata': {
                        'agent_name': turn.agent_name,
                        'agent_role': 'chat',
                        'communication_strategy': 'ContinuousDiscussion',
                        'discussion_mode': True,
                        'discussion_turn': self.metrics.total_turns,
                        'discussion_status': 'ongoing',
                        'turn_type': turn.turn_type.value if hasattr(turn.turn_type, 'value') else str(turn.turn_type),
                        'round_number': self.metrics.total_turns,
                        'processing_time': 0,
                        'svr_guided': True,
                        'svr_values': turn.discussion_context.get('svr_values', {}),
                        'discussion_context': {
                            'total_participants': len(self.participants),
                            'is_first_turn': False,
                            'responding_to_user': False,
                            'continuous_discussion': True
                        }
                    }
                }
            }

            self.logger.info(f"  📦 消息格式构建完成")
            self.logger.info(f"  🚀 调用WebSocket广播方法...")

            # 调用WebSocket处理器的广播方法
            await self.websocket_handler._broadcast_room_message(self.room_id, agent_message)

            # 广播成功确认 - 使用INFO级别确保可见
            self.logger.info(f"✅ WebSocket广播成功!")
            self.logger.info(f"  Agent: {turn.agent_name}")
            self.logger.info(f"  房间: {self.room_id}")
            self.logger.info(f"  消息类型: NEW_MESSAGE")
            self.logger.info(f"  消息预览: {turn.message.content[:50]}{'...' if len(turn.message.content) > 50 else ''}")

        except Exception as e:
            self.logger.error(f"❌ WebSocket广播异常:")
            self.logger.error(f"  Agent: {turn.agent_name}")
            self.logger.error(f"  房间: {self.room_id}")
            self.logger.error(f"  异常类型: {type(e).__name__}")
            self.logger.error(f"  异常详情: {str(e)}")
            self.logger.error(f"  这将导致Agent响应无法到达前端!")

    def set_websocket_handler(self, websocket_handler, room_id: str):
        """设置WebSocket处理器用于广播消息"""
        self.logger.info(f"🔧 设置WebSocket处理器:")
        self.logger.info(f"  房间ID: {room_id}")
        self.logger.info(f"  处理器类型: {type(websocket_handler).__name__ if websocket_handler else 'None'}")

        # 验证输入参数
        if not websocket_handler:
            self.logger.error(f"❌ WebSocket处理器设置失败: websocket_handler为None")
            self.logger.error(f"  这将导致所有Agent响应无法广播到前端!")

        if not room_id:
            self.logger.error(f"❌ WebSocket处理器设置失败: room_id为空")
            self.logger.error(f"  这将导致所有Agent响应无法广播到前端!")

        # 设置处理器
        self.websocket_handler = websocket_handler
        self.room_id = room_id

        # 确认设置结果
        if self.websocket_handler and self.room_id:
            self.logger.info(f"✅ WebSocket处理器设置成功!")
            self.logger.info(f"  房间ID: {self.room_id}")
            self.logger.info(f"  处理器已就绪，Agent响应将能够广播到前端")
        else:
            self.logger.error(f"❌ WebSocket处理器设置不完整!")
            self.logger.error(f"  websocket_handler: {'✓' if self.websocket_handler else '✗'}")
            self.logger.error(f"  room_id: {'✓' if self.room_id else '✗'}")
            self.logger.error(f"  Agent响应可能无法正确广播!")

    async def _cleanup_discussion(self):
        """
        讨论结束时清理资源
        """

        self.logger.info("清理讨论")

        self.is_running = False
        self.state = DiscussionState.STOPPING

        # 取消任务
        if self.svr_monitor_task and not self.svr_monitor_task.done():
            self.svr_monitor_task.cancel()
            try:
                await self.svr_monitor_task
            except asyncio.CancelledError:
                pass

        # 清理上下文
        if self.context:
            await self.context.cleanup()

        # 发出结束事件
        await self._emit_event("discussion_ended", {
            'total_turns': self.metrics.total_turns,
            'total_svr_computations': self.metrics.total_svr_computations,
            'final_quality': self.metrics.discussion_quality_trend[-1] if self.metrics.discussion_quality_trend else 0
        })

        if self.on_discussion_end:
            await self.on_discussion_end(self.context.session if self.context else None)

        self.state = DiscussionState.STOPPED

    # 公共控制方法

    async def pause_discussion(self) -> Dict[str, Any]:
        """暂停讨论"""
        if self.state == DiscussionState.RUNNING:
            self.should_pause = True
            return {'success': True, 'message': '讨论暂停请求已发送'}
        else:
            return {'success': False, 'error': f'无法在状态 {self.state.value} 下暂停'}

    async def resume_discussion(self) -> Dict[str, Any]:
        """恢复讨论"""
        if self.state == DiscussionState.PAUSED:
            self.should_pause = False
            return {'success': True, 'message': '讨论已恢复'}
        else:
            return {'success': False, 'error': f'无法在状态 {self.state.value} 下恢复'}

    async def stop_discussion(self) -> Dict[str, Any]:
        """停止讨论"""
        if self.state in [DiscussionState.RUNNING, DiscussionState.PAUSED]:
            self.should_stop = True

            # 等待清理
            if self.main_loop_task:
                try:
                    await asyncio.wait_for(self.main_loop_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self.main_loop_task.cancel()

            return {'success': True, 'message': '讨论已停止'}
        else:
            return {'success': False, 'error': f'无法在状态 {self.state.value} 下停止'}

    def get_current_status(self) -> Dict[str, Any]:
        """获取当前讨论状态"""

        status = {
            'state': self.state.value,
            'is_running': self.is_running,
            'metrics': {
                'total_turns': self.metrics.total_turns,
                'total_svr_computations': self.metrics.total_svr_computations,
                'average_svr_computation_time': self.metrics.average_svr_computation_time,
                'participant_engagement': self.metrics.participant_engagement.copy(),
                'last_update_time': self.metrics.last_update_time
            }
        }

        if self.context:
            status['session'] = {
                'session_id': self.context.session.session_id,
                'topic': self.context.session.topic,
                'participants': self.context.session.current_participants,
                'duration': self.context.session.get_duration()
            }

        if self.last_svr_result:
            status['last_svr_result'] = {
                'global_metrics': self.last_svr_result.global_svr_metrics,
                'computation_stats': self.last_svr_result.computation_stats,
                'timestamp': self.last_svr_result.timestamp
            }

        if self.last_decision:
            status['last_decision'] = {
                'action': self.last_decision.action.value,
                'selected_agent': self.last_decision.selected_agent_name,
                'confidence': self.last_decision.confidence,
                'reasoning': self.last_decision.reasoning
            }

        return status

    def subscribe_to_events(self, callback: Callable):
        """订阅实时事件"""
        self.event_subscribers.append(callback)

    def unsubscribe_from_events(self, callback: Callable):
        """取消订阅实时事件"""
        if callback in self.event_subscribers:
            self.event_subscribers.remove(callback)

    async def get_next_event(self, timeout: float = 1.0) -> Optional[DiscussionEvent]:
        """从队列获取下一个事件"""
        try:
            return await asyncio.wait_for(self.event_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
