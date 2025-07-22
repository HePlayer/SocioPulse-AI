# Server 模块

SocioPulse AI 模块化服务器组件，将原有的单一Server.py文件重构为多个专门的模块。

## 模块结构

```
Server/
├── __init__.py              # 包初始化文件
├── main.py                  # 主服务器类
├── config.py                # 配置常量
├── utils.py                 # 工具函数
├── connection_tester.py     # API连接测试
├── settings_manager.py      # 设置管理
├── websocket_handler.py     # WebSocket处理
├── room_manager.py          # 聊天室管理
└── README.md               # 本文档
```

## 核心组件

### 1. MultiAIServer (main.py)
主服务器类，整合所有功能组件：
- 静态文件服务
- 路由配置
- CORS设置
- 服务器生命周期管理

### 2. SettingsManager (settings_manager.py)
系统设置管理：
- 配置文件读写
- 模型配置管理
- API连接测试接口
- 可用模型列表管理

### 3. WebSocketHandler (websocket_handler.py)
WebSocket连接处理：
- 连接管理
- 消息路由
- 房间订阅
- 广播机制

### 4. RoomManager (room_manager.py)
聊天室管理：
- 房间创建/删除
- Agent管理
- 消息处理
- 历史记录导出

### 5. ConnectionTester (connection_tester.py)
API连接测试：
- OpenAI API测试
- AiHubMix API测试
- 智谱AI API测试

## 配置系统

### 环境变量
- `MULTIAI_HOST`: 服务器主机地址 (默认: 0.0.0.0)
- `MULTIAI_PORT`: 服务器端口 (默认: 8080)

### 配置文件
使用 `config.yaml` 存储系统设置：
- 模型平台配置
- API密钥设置
- 功能开关

## API接口

### 聊天室管理
- `GET /api/rooms` - 获取房间列表
- `POST /api/rooms` - 创建房间
- `GET /api/rooms/{room_id}` - 获取房间信息
- `DELETE /api/rooms/{room_id}` - 删除房间
- `POST /api/rooms/{room_id}/messages` - 发送消息
- `GET /api/rooms/{room_id}/history` - 获取历史记录
- `GET /api/rooms/{room_id}/export` - 导出历史记录

### 设置管理
- `GET /api/settings` - 获取系统设置
- `PUT /api/settings` - 更新系统设置
- `POST /api/test-connection` - 测试API连接
- `GET /api/available-models` - 获取可用模型

### WebSocket
- `GET /ws` - WebSocket连接端点

### 系统监控
- `GET /api/health` - 健康检查

## 使用方法

### 启动服务器
```python
from Server import MultiAIServer

# 创建服务器实例
server = MultiAIServer()

# 启动服务器
runner = await server.start_server()

# 停止服务器
await server.stop_server(runner)
```

### 直接运行
```bash
python Server.py
```

## 模块特性

### 1. 模块化设计
- 职责分离
- 低耦合高内聚
- 易于维护和扩展

### 2. 错误处理
- 统一的错误响应格式
- 详细的日志记录
- 优雅的资源清理

### 3. 配置管理
- 环境变量支持
- 默认配置
- 动态配置更新

### 4. 并发支持
- 异步编程模型
- WebSocket实时通信
- 多房间并发处理

## 扩展指南

### 添加新的API端点
1. 在相应的管理器中添加处理方法
2. 在 `main.py` 中注册路由
3. 更新文档

### 添加新的配置项
1. 在 `config.py` 中定义常量
2. 更新默认设置
3. 在设置管理器中处理

### 添加新的功能模块
1. 创建新的模块文件
2. 在 `__init__.py` 中导出
3. 在主服务器中集成

## 依赖项

- aiohttp: Web服务器框架
- aiohttp-cors: CORS支持
- PyYAML: 配置文件解析
- SocioPulse AI核心组件
