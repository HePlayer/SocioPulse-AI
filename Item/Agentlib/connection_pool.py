"""
模型连接池管理器
提供高效的HTTP连接复用，避免每次API调用时重新建立连接
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionPoolStatus(Enum):
    """连接池状态"""
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class ConnectionConfig:
    """连接配置"""
    platform: str
    api_base: str
    api_key: str
    max_connections: int = 10
    connection_timeout: float = 30.0
    read_timeout: float = 60.0
    keepalive_timeout: float = 30.0


class ModelConnectionPool:
    """模型连接池管理器"""
    
    def __init__(self):
        self.pools: Dict[str, aiohttp.ClientSession] = {}
        self.configs: Dict[str, ConnectionConfig] = {}
        self.status = ConnectionPoolStatus.INITIALIZING
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5分钟清理一次
        
        logger.info("ModelConnectionPool initialized")
    
    async def get_session(self, platform: str, api_base: str, api_key: str) -> aiohttp.ClientSession:
        """获取或创建连接会话"""
        pool_key = f"{platform}_{hash(api_base)}"
        
        # 检查是否需要清理
        await self._cleanup_if_needed()
        
        if pool_key not in self.pools:
            await self._create_session(pool_key, platform, api_base, api_key)
        
        return self.pools[pool_key]
    
    async def _create_session(self, pool_key: str, platform: str, api_base: str, api_key: str):
        """创建新的连接会话"""
        try:
            # 配置连接器
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30.0,
                enable_cleanup_closed=True
            )
            
            # 配置超时
            timeout = aiohttp.ClientTimeout(
                total=60.0,
                connect=30.0
            )
            
            # 创建会话
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'SocioPulse-AI/1.0',
                    'Connection': 'keep-alive'
                }
            )
            
            self.pools[pool_key] = session
            self.configs[pool_key] = ConnectionConfig(
                platform=platform,
                api_base=api_base,
                api_key=api_key
            )
            
            logger.info(f"Created connection pool for {platform}: {pool_key}")
            
        except Exception as e:
            logger.error(f"Failed to create connection pool for {platform}: {e}")
            raise
    
    async def _cleanup_if_needed(self):
        """定期清理连接池"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_idle_connections()
            self.last_cleanup = current_time
    
    async def _cleanup_idle_connections(self):
        """清理空闲连接"""
        try:
            for pool_key, session in list(self.pools.items()):
                if session.closed:
                    del self.pools[pool_key]
                    if pool_key in self.configs:
                        del self.configs[pool_key]
                    logger.debug(f"Cleaned up closed connection pool: {pool_key}")
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {e}")
    
    async def close_all(self):
        """关闭所有连接池"""
        try:
            for pool_key, session in self.pools.items():
                if not session.closed:
                    await session.close()
                logger.debug(f"Closed connection pool: {pool_key}")
            
            self.pools.clear()
            self.configs.clear()
            self.status = ConnectionPoolStatus.CLOSED
            logger.info("All connection pools closed")
            
        except Exception as e:
            logger.error(f"Error closing connection pools: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        return {
            'total_pools': len(self.pools),
            'active_pools': len([s for s in self.pools.values() if not s.closed]),
            'status': self.status.value,
            'last_cleanup': self.last_cleanup,
            'platforms': list(set(config.platform for config in self.configs.values()))
        }


# 全局连接池实例
_global_connection_pool: Optional[ModelConnectionPool] = None


async def get_connection_pool() -> ModelConnectionPool:
    """获取全局连接池实例"""
    global _global_connection_pool
    
    if _global_connection_pool is None:
        _global_connection_pool = ModelConnectionPool()
        _global_connection_pool.status = ConnectionPoolStatus.READY
    
    return _global_connection_pool


async def cleanup_connection_pool():
    """清理全局连接池"""
    global _global_connection_pool
    
    if _global_connection_pool:
        await _global_connection_pool.close_all()
        _global_connection_pool = None
