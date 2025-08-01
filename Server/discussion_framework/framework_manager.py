"""
讨论框架管理器
管理多个讨论会话和与现有系统的集成
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .continuous_controller import ContinuousDiscussionController, DiscussionState
from .parallel_svr_engine import ParallelSVREngine
from .svr_handler import SVRHandler
from .event_interface import DiscussionEventInterface
from Item.Communication.message_types import ChatMessage, MessageType
from Item.Agentlib import Agent


@dataclass
class DiscussionSessionInfo:
    """讨论会话信息"""
    session_id: str
    room_id: str
    topic: str
    controller: ContinuousDiscussionController
    event_interface: DiscussionEventInterface
    start_time: float
    participants: List[str]


class DiscussionFrameworkManager:
    """讨论框架管理器 - 管理多个讨论会话"""
    
    def __init__(self):
        # 活跃的讨论会话
        self.active_sessions: Dict[str, DiscussionSessionInfo] = {}
        
        # 共享的SVR引擎和处理器
        self.svr_engine = ParallelSVREngine()
        self.svr_handler = SVRHandler()
        
        # 性能监控
        self.total_sessions_created = 0
        self.total_sessions_completed = 0
        
        # 日志记录
        self.logger = logging.getLogger(self.__class__.__name__)

        # WebSocket处理器引用
        self.websocket_handler = None
    
    async def start_enhanced_discussion(self, 
                                      room_id: str,
                                      topic: str,
                                      participants: Dict[str, Agent],
                                      initial_message: ChatMessage,
                                      enhanced_history=None,
                                      communication_strategy=None) -> Dict[str, Any]:
        """
        启动增强讨论会话 - 增强诊断版本

        Args:
            room_id: 房间ID
            topic: 讨论主题
            participants: 参与的Agent
            initial_message: 初始消息
            enhanced_history: 增强历史管理器
            communication_strategy: 通信策略

        Returns:
            Dict: 启动结果
        """

        self.logger.info(f"🚀 启动增强讨论会话: {room_id}")

        try:
            # 🔧 CRITICAL FIX: 全面的启动前诊断
            self.logger.info("🔍 启动前系统诊断:")
            self.logger.info(f"  房间ID: {room_id}")
            self.logger.info(f"  主题: {topic}")
            self.logger.info(f"  参与者数量: {len(participants)}")
            self.logger.info(f"  WebSocket处理器状态: {'✓' if self.websocket_handler else '✗'}")

            if self.websocket_handler:
                self.logger.info(f"  WebSocket处理器类型: {type(self.websocket_handler).__name__}")
            else:
                self.logger.error("❌ WebSocket处理器未设置，Agent响应将无法广播到前端!")

            # 检查是否已有活跃会话
            if room_id in self.active_sessions:
                existing_session = self.active_sessions[room_id]
                if existing_session.controller.state in [DiscussionState.RUNNING, DiscussionState.PAUSED]:
                    return {
                        'success': False,
                        'error': f'房间 {room_id} 已有活跃的讨论会话',
                        'existing_session_id': existing_session.session_id
                    }
                else:
                    # 清理已完成的会话
                    await self._cleanup_session(room_id)
            
            # 创建新的控制器
            controller = ContinuousDiscussionController(
                svr_engine=self.svr_engine,
                svr_handler=self.svr_handler,
                max_turns=50,
                max_duration=3600,
                enable_real_time_updates=True
            )

            # 🔧 CRITICAL FIX: 强制设置WebSocket处理器
            self.logger.info(f"🔧 设置WebSocket处理器到控制器:")
            if self.websocket_handler:
                self.logger.info(f"  ✅ WebSocket处理器可用，正在设置...")
                controller.set_websocket_handler(self.websocket_handler, room_id)

                # 验证设置是否成功
                if controller.websocket_handler and controller.room_id:
                    self.logger.info(f"  ✅ WebSocket处理器设置成功验证")
                    self.logger.info(f"    控制器WebSocket处理器: {'✓' if controller.websocket_handler else '✗'}")
                    self.logger.info(f"    控制器房间ID: {controller.room_id}")
                else:
                    self.logger.error(f"  ❌ WebSocket处理器设置验证失败")
                    self.logger.error(f"    控制器WebSocket处理器: {'✓' if controller.websocket_handler else '✗'}")
                    self.logger.error(f"    控制器房间ID: {controller.room_id}")
            else:
                self.logger.error(f"  ❌ 框架管理器的WebSocket处理器为None")
                self.logger.error(f"  Agent响应将无法广播到前端!")
            
            # 设置事件处理器
            await self._setup_controller_events(controller, room_id)
            
            # 启动讨论
            result = await controller.start_discussion(
                room_id=room_id,
                topic=topic,
                participants=participants,
                initial_message=initial_message,
                enhanced_history=enhanced_history,
                communication_strategy=communication_strategy
            )
            
            if result['success']:
                # 创建事件接口
                event_interface = DiscussionEventInterface(controller)
                
                # 创建会话信息
                session_info = DiscussionSessionInfo(
                    session_id=result['session_id'],
                    room_id=room_id,
                    topic=topic,
                    controller=controller,
                    event_interface=event_interface,
                    start_time=time.time(),
                    participants=list(participants.keys())
                )
                
                # 注册会话
                self.active_sessions[room_id] = session_info
                self.total_sessions_created += 1
                
                self.logger.info(f"✅ 启动增强讨论会话成功: {result['session_id']} (房间: {room_id})")

                return {
                    'success': True,
                    'session_id': result['session_id'],
                    'room_id': room_id,
                    'participants': result['participants'],
                    'framework_status': controller.get_current_status(),
                    'websocket_status': 'connected' if controller.websocket_handler else 'disconnected'
                }
            else:
                self.logger.error(f"❌ 控制器启动讨论失败: {result.get('error', 'Unknown error')}")
                return result

        except Exception as e:
            self.logger.error(f"❌ 启动增强讨论会话失败 (房间: {room_id}): {e}")
            import traceback
            self.logger.error(f"异常堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_discussion_status(self, room_id: str) -> Dict[str, Any]:
        """获取讨论状态"""
        
        if room_id not in self.active_sessions:
            return {
                'active': False,
                'message': '没有活跃的讨论会话'
            }
        
        session_info = self.active_sessions[room_id]
        status = session_info.controller.get_current_status()
        
        # 添加会话特定信息
        status['session_info'] = {
            'session_id': session_info.session_id,
            'room_id': session_info.room_id,
            'topic': session_info.topic,
            'start_time': session_info.start_time,
            'duration': time.time() - session_info.start_time,
            'participants': session_info.participants
        }
        
        # 添加前端兼容的状态
        status['frontend_status'] = session_info.event_interface.get_frontend_status()
        
        return status
    
    async def control_discussion(self, room_id: str, action: str) -> Dict[str, Any]:
        """控制讨论（暂停、恢复、停止）"""
        
        if room_id not in self.active_sessions:
            return {
                'success': False,
                'error': f'房间 {room_id} 没有活跃的讨论会话'
            }
        
        controller = self.active_sessions[room_id].controller
        
        if action == 'pause':
            result = await controller.pause_discussion()
        elif action == 'resume':
            result = await controller.resume_discussion()
        elif action == 'stop':
            result = await controller.stop_discussion()
            # 如果成功停止，清理会话
            if result.get('success'):
                await self._cleanup_session(room_id)
        else:
            return {
                'success': False,
                'error': f'未知操作: {action}'
            }
        
        return result

    def set_websocket_handler(self, websocket_handler):
        """设置WebSocket处理器用于消息广播"""
        self.websocket_handler = websocket_handler
        self.logger.info("WebSocket handler set for discussion framework manager")
    
    async def get_all_discussion_statuses(self) -> Dict[str, Any]:
        """获取所有活跃讨论的状态"""
        
        statuses = {}
        
        for room_id, session_info in self.active_sessions.items():
            try:
                status = await self.get_discussion_status(room_id)
                statuses[room_id] = status
            except Exception as e:
                statuses[room_id] = {
                    'error': str(e)
                }
        
        return {
            'active_sessions': len(self.active_sessions),
            'total_sessions_created': self.total_sessions_created,
            'total_sessions_completed': self.total_sessions_completed,
            'room_statuses': statuses
        }
    
    async def cleanup_finished_sessions(self):
        """清理已完成的讨论会话"""
        
        finished_rooms = []
        
        for room_id, session_info in self.active_sessions.items():
            if session_info.controller.state in [DiscussionState.STOPPED, DiscussionState.ERROR]:
                finished_rooms.append(room_id)
        
        for room_id in finished_rooms:
            await self._cleanup_session(room_id)
    
    async def _setup_controller_events(self, controller: ContinuousDiscussionController, room_id: str):
        """为控制器设置事件处理器"""
        
        async def on_discussion_start(session):
            self.logger.info(f"讨论开始: {session.session_id} (房间: {room_id})")
        
        async def on_discussion_end(session):
            if session:
                self.logger.info(f"讨论结束: {session.session_id} (房间: {room_id})")
                self.total_sessions_completed += 1
                # 延迟清理会话
                asyncio.create_task(self._delayed_cleanup(room_id, 5.0))
        
        async def on_turn_complete(turn):
            self.logger.debug(f"轮次完成: {turn.agent_name} (房间: {room_id})")
        
        async def on_error(error):
            self.logger.error(f"讨论框架错误 (房间: {room_id}): {error}")
        
        # 设置事件处理器
        controller.on_discussion_start = on_discussion_start
        controller.on_discussion_end = on_discussion_end
        controller.on_turn_complete = on_turn_complete
        controller.on_error = on_error
    
    async def _cleanup_session(self, room_id: str):
        """清理会话"""
        
        if room_id in self.active_sessions:
            session_info = self.active_sessions[room_id]
            
            # 确保控制器已停止
            if session_info.controller.state not in [DiscussionState.STOPPED, DiscussionState.ERROR]:
                await session_info.controller.stop_discussion()
            
            # 移除会话
            del self.active_sessions[room_id]
            self.logger.info(f"清理讨论会话: {session_info.session_id} (房间: {room_id})")
    
    async def _delayed_cleanup(self, room_id: str, delay: float):
        """延迟清理会话"""
        await asyncio.sleep(delay)
        await self._cleanup_session(room_id)
    
    def get_framework_statistics(self) -> Dict[str, Any]:
        """获取框架统计信息"""
        
        active_states = {}
        for session_info in self.active_sessions.values():
            state = session_info.controller.state.value
            active_states[state] = active_states.get(state, 0) + 1
        
        return {
            'total_sessions_created': self.total_sessions_created,
            'total_sessions_completed': self.total_sessions_completed,
            'active_sessions': len(self.active_sessions),
            'active_session_states': active_states,
            'svr_engine_stats': self.svr_engine.get_performance_metrics(),
            'svr_handler_stats': self.svr_handler.get_decision_statistics()
        }
