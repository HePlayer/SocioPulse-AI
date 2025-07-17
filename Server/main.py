"""
SocioPulse AI 主服务器

模块化的MultiAI服务器，整合了所有功能组件
"""

import os
import logging
from aiohttp import web
from aiohttp_cors import setup as cors_setup, ResourceOptions

from Item.Workflow import WorkflowBuilder

from .config import HOST, PORT, INDEX_FILE_PATH
from .settings_manager import SettingsManager
from .websocket_handler import WebSocketHandler
from .room_manager import RoomManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiAIServer:
    """MultiAI服务器主类"""
    
    def __init__(self):
        # 核心状态
        self.app = web.Application()
        self.chat_rooms = {}
        self.websockets = {}
        
        # 初始化工作流构建器
        self.workflow_builder = WorkflowBuilder()
        
        # 初始化管理器
        self.settings_manager = SettingsManager()
        self.websocket_handler = WebSocketHandler(self.chat_rooms, self.websockets)
        self.room_manager = RoomManager(self.chat_rooms, self.workflow_builder)
        
        # 将管理器添加到app对象中，以便其他组件可以访问
        self.app['settings_manager'] = self.settings_manager
        self.app['room_manager'] = self.room_manager
        self.app['websocket_handler'] = self.websocket_handler
        
        # 设置路由和CORS
        self._setup_routes()
        self._setup_cors()
        
        logger.info("MultiAI Server initialized")
    
    def _setup_routes(self):
        """设置路由"""
        # 首页路由
        self.app.router.add_get('/', self._serve_index)
        # 静态文件服务 - 直接映射UserInterface目录下的所有文件
        self.app.router.add_static('/assets/', 'UserInterface/assets/', show_index=False)
        
        # WebSocket路由
        self.app.router.add_get('/ws', self.websocket_handler.handle_websocket_connection)
        
        # 聊天室API路由
        self.app.router.add_get('/api/rooms', self.room_manager.handle_get_rooms)
        self.app.router.add_post('/api/rooms', self.room_manager.handle_create_room)
        self.app.router.add_get('/api/rooms/{room_id}', self.room_manager.handle_get_room_info)
        self.app.router.add_delete('/api/rooms/{room_id}', self.room_manager.handle_delete_room)
        self.app.router.add_post('/api/rooms/{room_id}/messages', self.room_manager.handle_send_message_to_room)
        self.app.router.add_get('/api/rooms/{room_id}/history', self.room_manager.handle_get_room_history)
        self.app.router.add_get('/api/rooms/{room_id}/export', self.room_manager.handle_export_room_history)
        self.app.router.add_get('/api/rooms/{room_id}/agents', self.room_manager.handle_get_room_agents)
        
        # 设置API路由
        self.app.router.add_get('/api/settings', self.settings_manager.handle_get_settings)
        self.app.router.add_post('/api/settings', self.settings_manager.handle_update_settings)  # 修复：改为POST
        self.app.router.add_put('/api/settings', self.settings_manager.handle_update_settings)   # 保持兼容性
        self.app.router.add_post('/api/test-connection', self.settings_manager.handle_test_api_connection)
        self.app.router.add_get('/api/available-models', self.settings_manager.handle_get_available_models)
        
        # 健康检查路由
        self.app.router.add_get('/api/health', self._handle_health_check)
        
        logger.info("Routes configured")
    
    def _setup_cors(self):
        """设置CORS"""
        cors = cors_setup(self.app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)
        
        logger.info("CORS configured")
    
    async def _serve_index(self, request):
        """服务主页"""
        try:
            # 优先使用UserInterface中的index.html
            if os.path.exists('UserInterface/index.html'):
                return web.FileResponse('UserInterface/index.html')
            # 备用原始MultiAI.html
            elif os.path.exists(INDEX_FILE_PATH):
                return web.FileResponse(INDEX_FILE_PATH)
            else:
                return web.Response(
                    text="Index file not found. Please ensure UserInterface/index.html or MultiAI.html exists.",
                    status=404
                )
        except Exception as e:
            logger.error(f"Error serving index: {e}")
            return web.Response(text=f"Error: {e}", status=500)
    
    async def _handle_health_check(self, request):
        """健康检查"""
        return web.json_response({
            'status': 'healthy',
            'version': '1.0.0',
            'active_rooms': len(self.chat_rooms),
            'active_websockets': len(self.websockets)
        })
    
    async def start_server(self):
        """启动服务器"""
        try:
            logger.info(f"Starting MultiAI Server on {HOST}:{PORT}")
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, HOST, PORT)
            await site.start()
            
            logger.info(f"Server started successfully on http://{HOST}:{PORT}")
            return runner
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    async def stop_server(self, runner):
        """停止服务器"""
        try:
            # 停止所有聊天室
            for room_id, room in list(self.chat_rooms.items()):
                try:
                    await room.stop()
                except Exception as e:
                    logger.error(f"Error stopping room {room_id}: {e}")
            
            # 关闭所有WebSocket连接
            for connection_id, ws in list(self.websockets.items()):
                try:
                    await ws.close()
                except Exception as e:
                    logger.error(f"Error closing websocket {connection_id}: {e}")
            
            # 停止服务器
            await runner.cleanup()
            logger.info("Server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")


async def create_server():
    """创建并启动服务器实例"""
    server = MultiAIServer()
    runner = await server.start_server()
    return server, runner


async def main():
    """主函数 - 用于直接运行服务器"""
    import asyncio
    
    server, runner = await create_server()
    
    try:
        # 保持服务器运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await server.stop_server(runner)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
