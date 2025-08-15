"""
通信策略工厂
根据通信模式创建相应的通信策略实例
"""

from typing import Dict, Type, Optional
from .message_types import CommunicationMode
from .base_strategy import CommunicationStrategy
from .direct_strategy import DirectCommunicationStrategy
from .broadcast_strategy import BroadcastCommunicationStrategy
from .network_strategy import NetworkCommunicationStrategy
from .discussion_strategy import DiscussionCommunicationStrategy


class CommunicationStrategyFactory:
    """通信策略工厂类"""
    
    # 策略映射表
    _strategy_map: Dict[CommunicationMode, Type[CommunicationStrategy]] = {
        CommunicationMode.DIRECT: DirectCommunicationStrategy,
        CommunicationMode.BROADCAST: BroadcastCommunicationStrategy,
        CommunicationMode.NETWORK: NetworkCommunicationStrategy,
    }
    
    # 策略实例缓存
    _strategy_cache: Dict[CommunicationMode, CommunicationStrategy] = {}
    
    @classmethod
    def create_strategy(cls, mode: CommunicationMode, discussion_enabled: bool = False) -> CommunicationStrategy:
        """
        创建通信策略实例
        
        Args:
            mode: 通信模式
            discussion_enabled: 是否启用讨论模式
            
        Returns:
            CommunicationStrategy: 通信策略实例
        """
        # 如果启用讨论模式，优先使用讨论策略
        if discussion_enabled:
            cache_key = 'discussion'
            if cache_key not in cls._strategy_cache:
                cls._strategy_cache[cache_key] = DiscussionCommunicationStrategy()
            return cls._strategy_cache[cache_key]
        
        # 使用标准策略
        if mode not in cls._strategy_map:
            raise ValueError(f"Unsupported communication mode: {mode}")
        
        # 使用缓存避免重复创建
        if mode not in cls._strategy_cache:
            strategy_class = cls._strategy_map[mode]
            cls._strategy_cache[mode] = strategy_class()
        
        return cls._strategy_cache[mode]
    
    @classmethod
    def get_available_modes(cls) -> list:
        """获取所有可用的通信模式"""
        return list(cls._strategy_map.keys())
    
    @classmethod
    def register_strategy(cls, mode: CommunicationMode, strategy_class: Type[CommunicationStrategy]):
        """
        注册新的通信策略
        
        Args:
            mode: 通信模式
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, CommunicationStrategy):
            raise ValueError("Strategy class must inherit from CommunicationStrategy")
        
        cls._strategy_map[mode] = strategy_class
        # 清除缓存以确保使用新策略
        if mode in cls._strategy_cache:
            del cls._strategy_cache[mode]
    
    @classmethod
    def clear_cache(cls):
        """清除策略缓存"""
        cls._strategy_cache.clear()
    
    @classmethod
    def get_strategy_info(cls, mode: CommunicationMode) -> Dict[str, str]:
        """
        获取策略信息
        
        Args:
            mode: 通信模式
            
        Returns:
            Dict[str, str]: 策略信息
        """
        if mode not in cls._strategy_map:
            return {"error": f"Unknown communication mode: {mode}"}
        
        strategy_class = cls._strategy_map[mode]
        return {
            "mode": mode.value,
            "class_name": strategy_class.__name__,
            "description": strategy_class.__doc__ or "No description available"
        }
    
    @classmethod
    def validate_mode(cls, mode: CommunicationMode) -> bool:
        """
        验证通信模式是否支持
        
        Args:
            mode: 通信模式
            
        Returns:
            bool: 是否支持
        """
        return mode in cls._strategy_map
