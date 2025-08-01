"""
通信策略基类
定义Agent间通信的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .message_types import ChatMessage


class CommunicationResult(Enum):
    """通信结果状态"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    NO_RECIPIENTS = "no_recipients"


@dataclass
class CommunicationContext:
    """通信上下文"""
    sender_id: str
    message: ChatMessage
    room_id: str
    room_name: str
    available_agents: Dict[str, Any]  # agent_id -> Agent对象
    message_history: List[ChatMessage]
    metadata: Dict[str, Any]


@dataclass
class CommunicationResponse:
    """通信响应"""
    result: CommunicationResult
    delivered_to: List[str]  # 成功接收消息的Agent ID列表
    failed_deliveries: List[str]  # 投递失败的Agent ID列表
    responses: List[ChatMessage]  # Agent的响应消息
    metadata: Dict[str, Any]
    error_message: Optional[str] = None


class CommunicationStrategy(ABC):
    """通信策略抽象基类"""
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.logger = None  # 将在子类中设置
    
    @abstractmethod
    async def deliver_message(self, context: CommunicationContext) -> CommunicationResponse:
        """
        投递消息给相关的Agent
        
        Args:
            context: 通信上下文
            
        Returns:
            CommunicationResponse: 通信结果
        """
        pass
    
    @abstractmethod
    def get_target_agents(self, context: CommunicationContext) -> List[str]:
        """
        获取目标Agent列表
        
        Args:
            context: 通信上下文
            
        Returns:
            List[str]: 目标Agent ID列表
        """
        pass
    
    @abstractmethod
    def should_process_response(self, context: CommunicationContext) -> bool:
        """
        判断是否应该处理Agent响应
        
        Args:
            context: 通信上下文
            
        Returns:
            bool: 是否处理响应
        """
        pass
    
    def log_info(self, message: str, extra: Dict[str, Any] = None):
        """记录信息日志"""
        if self.logger:
            self.logger.info(f"[{self.strategy_name}] {message}", extra or {})
    
    def log_warning(self, message: str, extra: Dict[str, Any] = None):
        """记录警告日志"""
        if self.logger:
            self.logger.warning(f"[{self.strategy_name}] {message}", extra or {})
    
    def log_error(self, message: str, error: Exception = None, extra: Dict[str, Any] = None):
        """记录错误日志"""
        if self.logger:
            if error:
                self.logger.error(f"[{self.strategy_name}] {message}: {error}", extra or {})
            else:
                self.logger.error(f"[{self.strategy_name}] {message}", extra or {})
