"""
消息类型定义
避免循环导入问题
"""

import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"
    COMMAND = "command"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    JOIN = "join"
    LEAVE = "leave"


class CommunicationMode(Enum):
    """通信模式"""
    BROADCAST = "broadcast"      # 广播模式：消息发送给所有人
    DIRECT = "direct"           # 直接模式：点对点通信
    NETWORK = "network"         # 网络模式：动态拓扑
    SEQUENTIAL = "sequential"   # 顺序模式：按顺序传递


@dataclass
class ChatMessage:
    """聊天消息"""
    sender_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    receiver_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    id: str = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """从字典创建"""
        return cls(
            id=data.get('id'),
            sender_id=data['sender_id'],
            receiver_id=data.get('receiver_id'),
            content=data['content'],
            message_type=MessageType(data.get('message_type', 'text')),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None,
            metadata=data.get('metadata', {})
        )
