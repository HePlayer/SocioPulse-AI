"""
SocioPulse AI Server 模块

提供模块化的Web服务器组件，包括：
- SocioPulse 服务器主类
- WebSocket处理
- 聊天室管理
- Agent管理
- 设置管理
- API连接测试
"""

from .main import SocioPulseServer, MultiAIServer

__all__ = ['SocioPulseServer', 'MultiAIServer']
__version__ = '1.0.0'
