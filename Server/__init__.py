"""
SocioPulse AI Server 模块

提供模块化的Web服务器组件，包括：
- MultiAI服务器主类
- WebSocket处理
- 聊天室管理
- Agent管理
- 设置管理
- API连接测试
"""

from .main import MultiAIServer

__all__ = ['MultiAIServer']
__version__ = '1.0.0'
