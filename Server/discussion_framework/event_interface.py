"""
前端兼容性接口
为前端消费讨论事件提供接口
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .continuous_controller import ContinuousDiscussionController, DiscussionEvent


class DiscussionEventInterface:
    """前端消费讨论事件的接口"""
    
    def __init__(self, controller: ContinuousDiscussionController):
        self.controller = controller
        self.event_buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = 100
        
        # 订阅控制器事件
        self.controller.subscribe_to_events(self.handle_event)
    
    def get_frontend_status(self) -> Dict[str, Any]:
        """获取为前端格式化的状态"""
        
        status = self.controller.get_current_status()
        
        # 为前端格式化
        frontend_status = {
            'discussion': {
                'active': status['is_running'],
                'state': status['state'],
                'session_id': status.get('session', {}).get('session_id'),
                'topic': status.get('session', {}).get('topic'),
                'participants': status.get('session', {}).get('participants', []),
                'duration': status.get('session', {}).get('duration', 0)
            },
            'metrics': {
                'total_turns': status['metrics']['total_turns'],
                'discussion_quality': 0,
                'consensus_level': 0,
                'participant_engagement': status['metrics']['participant_engagement']
            },
            'last_decision': None
        }
        
        # 添加SVR指标（如果可用）
        if 'last_svr_result' in status:
            svr_metrics = status['last_svr_result']['global_metrics']
            frontend_status['metrics'].update({
                'discussion_quality': svr_metrics.get('discussion_quality', 0),
                'consensus_level': svr_metrics.get('consensus_level', 0)
            })
        
        # 添加最后决策（如果可用）
        if 'last_decision' in status:
            frontend_status['last_decision'] = {
                'action': status['last_decision']['action'],
                'selected_agent': status['last_decision']['selected_agent'],
                'confidence': status['last_decision']['confidence']
            }
        
        return frontend_status
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取前端的最近事件"""
        
        return self.event_buffer[-limit:] if self.event_buffer else []
    
    async def handle_event(self, event: DiscussionEvent):
        """处理事件并为前端格式化"""
        
        frontend_event = {
            'type': event.event_type,
            'timestamp': event.timestamp,
            'session_id': event.session_id,
            'data': self._format_event_data(event.event_type, event.data)
        }
        
        self.event_buffer.append(frontend_event)
        
        # 维护缓冲区大小
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer = self.event_buffer[-self.max_buffer_size:]
    
    def _format_event_data(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """为前端消费格式化事件数据"""
        
        if event_type == 'turn_completed':
            return {
                'agent_name': data.get('agent_name'),
                'content_preview': data.get('content', '')[:100] + '...' if len(data.get('content', '')) > 100 else data.get('content', ''),
                'turn_number': data.get('turn_number')
            }
        
        elif event_type == 'decision_made':
            return {
                'action': data.get('action'),
                'selected_agent': data.get('selected_agent'),
                'confidence': data.get('confidence'),
                'reasoning_summary': data.get('reasoning', [])[:2]  # 前2个原因
            }
        
        elif event_type == 'svr_computed':
            return {
                'discussion_quality': data.get('global_metrics', {}).get('discussion_quality', 0),
                'consensus_level': data.get('global_metrics', {}).get('consensus_level', 0),
                'computation_time': data.get('computation_stats', {}).get('total_time', 0)
            }
        
        elif event_type == 'discussion_started':
            return {
                'session_id': data.get('session_id'),
                'topic': data.get('topic'),
                'participant_count': len(data.get('participants', []))
            }
        
        elif event_type == 'discussion_ended':
            return {
                'total_turns': data.get('total_turns', 0),
                'total_computations': data.get('total_svr_computations', 0),
                'final_quality': data.get('final_quality', 0)
            }
        
        elif event_type == 'error_occurred':
            return {
                'error_message': data.get('error', ''),
                'error_count': data.get('error_count', 0),
                'max_errors': data.get('max_errors', 0)
            }
        
        else:
            return data
    
    def get_websocket_data(self) -> Dict[str, Any]:
        """获取WebSocket传输的数据"""
        
        return {
            'status': self.get_frontend_status(),
            'recent_events': self.get_recent_events(5),
            'timestamp': time.time()
        }
    
    def get_api_response(self) -> Dict[str, Any]:
        """获取API响应格式的数据"""
        
        frontend_status = self.get_frontend_status()
        
        return {
            'success': True,
            'data': {
                'discussion_active': frontend_status['discussion']['active'],
                'discussion_state': frontend_status['discussion']['state'],
                'session_info': frontend_status['discussion'],
                'metrics': frontend_status['metrics'],
                'last_decision': frontend_status['last_decision'],
                'recent_events': self.get_recent_events(10)
            },
            'timestamp': time.time()
        }
    
    def cleanup(self):
        """清理资源"""
        
        # 取消订阅事件
        self.controller.unsubscribe_from_events(self.handle_event)
        
        # 清空缓冲区
        self.event_buffer.clear()


class WebSocketEventStreamer:
    """WebSocket事件流处理器"""
    
    def __init__(self, event_interface: DiscussionEventInterface):
        self.event_interface = event_interface
        self.connected_clients: List[Any] = []  # WebSocket连接列表
    
    async def add_client(self, websocket):
        """添加WebSocket客户端"""
        self.connected_clients.append(websocket)
        
        # 发送初始状态
        initial_data = {
            'type': 'initial_status',
            'data': self.event_interface.get_frontend_status()
        }
        
        try:
            await websocket.send_json(initial_data)
        except Exception as e:
            # 连接可能已关闭
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)
    
    async def remove_client(self, websocket):
        """移除WebSocket客户端"""
        if websocket in self.connected_clients:
            self.connected_clients.remove(websocket)
    
    async def broadcast_event(self, event_data: Dict[str, Any]):
        """向所有连接的客户端广播事件"""
        
        if not self.connected_clients:
            return
        
        disconnected_clients = []
        
        for websocket in self.connected_clients:
            try:
                await websocket.send_json({
                    'type': 'event',
                    'data': event_data
                })
            except Exception as e:
                # 连接已断开
                disconnected_clients.append(websocket)
        
        # 清理断开的连接
        for websocket in disconnected_clients:
            self.connected_clients.remove(websocket)
    
    async def send_status_update(self):
        """发送状态更新"""
        
        if not self.connected_clients:
            return
        
        status_data = {
            'type': 'status_update',
            'data': self.event_interface.get_frontend_status()
        }
        
        await self.broadcast_event(status_data)
    
    def get_client_count(self) -> int:
        """获取连接的客户端数量"""
        return len(self.connected_clients)
