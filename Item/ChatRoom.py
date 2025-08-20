"""
兼容层：保留旧导入路径 Item.ChatRoom
实际实现已迁移至 comm/chat_room.py
"""
from comm.chat_room import (
    ChatRoom,
    ChatRoomConfig,
)

# 兼容导出通信相关类型（旧代码常从 Item.ChatRoom 引用）
from Item.Communication.message_types import ChatMessage, MessageType, CommunicationMode  # noqa: F401

__all__ = [
    'ChatRoom',
    'ChatRoomConfig',
    'ChatMessage',
    'MessageType',
    'CommunicationMode',
]

