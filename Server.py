"""
SocioPulse AI 服务器入口文件

使用模块化的Server包来启动MultiAI服务器
"""

import asyncio
import logging
from Server import MultiAIServer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    logger.info("Starting SocioPulse AI MultiAI Server")
    
    # 创建并启动服务器
    server = MultiAIServer()
    runner = await server.start_server()
    
    try:
        logger.info("Server is running. Press Ctrl+C to stop.")
        # 保持服务器运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        logger.info("Shutting down server...")
        await server.stop_server(runner)
        logger.info("Server stopped successfully")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server startup interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
