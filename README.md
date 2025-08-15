# SocioPulse-AI - 多Agent智能讨论系统

SocioPulse-AI是一个基于多Agent架构的智能讨论系统，支持单Agent对话和多Agent连续讨论，具备实时WebSocket通信、智能上下文管理和SVR决策机制。

## 🚀 核心功能

### 1. 多Agent智能讨论 🤖 ✅ **已完成实现**
- **单Agent对话**: 支持与单个AI Agent进行深度对话交互
- **多Agent连续讨论**: 多个Agent自主进行连续讨论，基于SVR机制智能决策
- **智能Agent选择**: 基于讨论上下文和Agent专长自动选择最适合的发言者


### 2. SVR决策机制 🧠 ✅ **已完成实现**
- **Stop-Value-Repeat评估**: 每轮讨论后评估是否停止、继续或重复
- **并行SVR计算**: 所有Agent并行计算SVR值，提高决策效率
- **自适应阈值**: 根据讨论进展动态调整决策阈值

### 3. 实时WebSocket通信 📡 ✅ **已完成实现**
- **双向实时通信**: 用户与Agent、Agent与Agent之间的实时消息传递
- **房间管理**: 支持多个讨论房间，每个房间独立运行
- **消息广播**: 智能消息路由和广播，确保所有参与者实时接收消息
- **连接管理**: 自动连接恢复、断线重连和状态同步
- **消息去重**: 防止重复消息显示，提供流畅的用户体验

### 4. 智能上下文工程系统 🧠 ✅ **已完成实现**
- **5个输入部分组织**: 开发者指令、历史对话、用户输入、工具调用结果、外部数据源的结构化管理
- **3个存储类别**: 便笺（scratchpad）、记忆（memory）、当前上下文（current context）的分层存储
- **三种记忆类型**: 情景记忆（特定情景行为）、程序记忆（操作流程）、语义记忆（事实知识）
- **HNSW高效检索**: 基于分层小世界图算法的O(log N)向量检索，支持语义相似度搜索
- **智能上下文压缩**: 使用COCOM方法，达到95%阈值时自动压缩，优化token使用
- **多格式输出**: 支持JSON、Markdown、Text三种格式的上下文输出

### 5. 智能存储系统 💾 ✅ **已完成实现**
- **多层级存储架构**: IndexedDB持久化存储 + localStorage快速缓存 + 内存缓存的三层存储体系
- **智能数据管理**: 自动消息保存、批量处理、数据去重和智能缓存策略
- **高性能检索**: 基于索引的快速消息检索，支持房间、时间、发送者等多维度查询
- **离线支持**: 完整的离线消息存储和恢复，确保数据不丢失
- **房间持久化**: 服务器重启后自动恢复聊天室和配置
- **事件驱动架构**: 基于EventBus的松耦合事件系统，支持存储状态监控

## 📁 项目结构

```
SocioPulse-AI/
├── UserInterface/                  # 前端界面
│   ├── index.html                  # 主页面
│   ├── assets/                     # 资源文件
│   │   ├── css/                    # 样式文件
│   │   │   ├── main.css            # 主样式
│   │   │   ├── components.css      # 组件样式
│   │   │   └── themes.css          # 主题样式
│   │   └── js/                     # 脚本文件
│   │       ├── main.js             # 主脚本
│   │       ├── chat.js             # 聊天功能
│   │       ├── chat-manager.js     # 聊天管理器
│   │       ├── websocket.js        # WebSocket通信
│   │       ├── settings.js         # 设置管理
│   │       ├── utils.js            # 工具函数
│   │       └── storage/            # 存储系统
│   │           ├── storage-manager.js      # 主存储管理器
│   │           ├── indexeddb-manager.js    # IndexedDB管理
│   │           ├── localstorage-manager.js # localStorage管理
│   │           ├── memory-cache.js         # 内存缓存
│   │           ├── data-models.js          # 数据模型
│   │           └── event-bus.js            # 事件总线
│   └── README.md                   # 前端文档
├── Server/                         # 后端服务器
│   ├── __init__.py                 # 包初始化
│   ├── main.py                     # 主服务器类
│   ├── config.py                   # 配置常量
│   ├── utils.py                    # 工具函数
│   ├── connection_tester.py        # API连接测试
│   ├── settings_manager.py         # 设置管理
│   ├── websocket_handler.py        # WebSocket处理
│   ├── room_manager.py             # 聊天室管理
│   ├── room_persistence.py         # 房间持久化
│   └── discussion_framework/       # 连续讨论框架
│       ├── __init__.py             # 框架初始化
│       ├── framework_manager.py    # 框架管理器
│       ├── continuous_controller.py # 连续讨论控制器
│       ├── parallel_svr_engine.py  # 并行SVR引擎
│       ├── svr_handler.py          # SVR处理器
│       ├── discussion_context.py   # 讨论上下文
│       ├── agent_id_manager.py     # Agent ID管理
│       └── event_interface.py      # 事件接口
├── Item/                           # 核心模块
│   ├── Agentlib/                   # Agent管理模块
│   │   ├── Agent.py                # Agent基类
│   │   ├── Models.py               # 模型管理
│   │   ├── Prompt.py               # 提示词管理
│   │   ├── model_manager.py        # 模型管理器
│   │   ├── enhanced_models.py      # 增强模型类
│   │   └── Tools/                  # 工具集合
│   │       ├── base_tool.py        # 工具基类
│   │       ├── calculator.py       # 计算器工具
│   │       ├── file_tool.py        # 文件操作工具
│   │       ├── web_search.py       # 网络搜索工具
│   │       └── code_executor.py    # 代码执行工具
│   ├── ContextEngineer/            # 上下文工程模块
│   │   ├── context_manager.py      # 上下文管理器
│   │   ├── memory_system.py        # 记忆系统
│   │   ├── scratchpad.py           # 便笺系统
│   │   ├── retrieval_engine.py     # 检索引擎
│   │   ├── context_compressor.py   # 上下文压缩器
│   │   ├── hnsw_index.py           # HNSW索引
│   │   └── distance_metrics.py     # 距离度量
│   ├── Communication/              # 通信模块
│   │   ├── discussion_types.py     # 讨论类型定义
│   │   └── message_types.py        # 消息类型定义
│   ├── FlowTools/                  # 流程控制模块
│   │   ├── base_component.py       # 基础组件
│   │   ├── flow_node.py            # 流程节点
│   │   ├── flow_engine.py          # 流程引擎
│   │   ├── node_factory.py         # 节点工厂
│   │   └── debug_logger.py         # 调试日志器
│   ├── Workflow.py                 # 工作流管理
│   └── ChatRoom.py                 # 聊天室管理
├── Server.py                       # 服务器入口文件
├── config.yaml                     # 配置文件
├── requirements.txt                # Python依赖
├── logs/                          # 日志文件
├── workspace/                     # 工作空间
│   └── rooms/                     # 房间持久化存储
└── README.md                      # 项目文档
```

## 🛠️ 技术架构

### 前端技术栈
- **HTML5 + CSS3**: 现代化的用户界面设计
- **原生JavaScript**: 高性能的前端逻辑处理
- **WebSocket API**: 实时双向通信
- **IndexedDB**: 客户端数据持久化存储
- **localStorage**: 快速缓存和会话管理
- **响应式设计**: 支持多种设备和屏幕尺寸

### 后端技术栈
- **Python 3.8+**: 主要开发语言
- **aiohttp**: 高性能异步Web框架（实际使用）
- **WebSocket**: 实时通信协议
- **asyncio**: 异步编程支持
- **YAML**: 配置文件格式
- **文件系统**: 数据持久化存储

### 核心组件架构

#### Agent系统
- **Agent基类**: 提供统一的Agent接口和基础功能
- **角色系统**: 支持历史学家、数学家、程序员等专业角色
- **消息传递**: Agent间的异步消息通信
- **状态管理**: 完整的Agent生命周期管理
- **模型集成**: 支持OpenAI、智谱AI等多种LLM平台

#### 连续讨论框架
- **框架管理器**: 统一管理多Agent讨论会话
- **连续控制器**: 控制讨论流程和Agent轮换
- **SVR引擎**: 并行计算Stop-Value-Repeat决策
- **讨论上下文**: 维护讨论历史和状态信息
- **事件接口**: 处理讨论过程中的各种事件

#### WebSocket通信系统
- **连接管理**: 自动连接、断线重连、状态同步
- **消息路由**: 智能消息分发和广播
- **房间管理**: 多房间隔离和状态管理
- **错误处理**: 完善的错误恢复机制
- **性能优化**: 消息去重、批量处理、连接池

## 🚀 快速开始

### 1. 环境要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows、macOS、Linux
- **内存**: 建议 4GB 以上
- **网络**: 需要访问LLM API服务（OpenAI、智谱AI等）

### 2. 安装依赖
```bash
# 克隆项目
git clone https://github.com/yourusername/SocioPulse-AI.git
cd SocioPulse-AI

# 安装Python依赖
pip install -r requirements.txt
```

### 3. 配置API密钥
编辑 `config.yaml` 文件，添加你的API配置：

```yaml
models:
  default_platform: zhipu
  platforms:
    openai:
      api_base: "https://api.openai.com/v1"
      api_key: "your_openai_api_key"
      available_models:
        - gpt-4
        - gpt-4-turbo
        - gpt-3.5-turbo
      default_model: gpt-4
      enabled_models:
        - gpt-4
        - gpt-4-turbo
        - gpt-3.5-turbo
    zhipu:
      api_base: "https://open.bigmodel.cn/api/paas/v4"
      api_key: "your_zhipu_api_key"
      available_models:
        - glm-4
        - glm-4-plus
        - glm-3-turbo
        - glm-4-flash-250414
      default_model: glm-4
      enabled_models:
        - glm-4
        - glm-4-plus
        - glm-3-turbo
        - glm-4-flash-250414

server:
  host: "localhost"
  port: 8000
  debug: true
```

### 4. 启动服务器
```bash
# 启动SocioPulse-AI服务器
python Server.py
```

服务器启动后，你会看到类似以下的输出：
```
🚀 SocioPulse-AI Server starting...
📡 WebSocket server running on ws://localhost:8000/ws
🌐 HTTP server running on http://localhost:8000
✅ Server is ready!
```

### 5. 访问前端界面
打开浏览器，访问：
```
http://localhost:8000
```

### 6. 创建你的第一个讨论
1. **配置API密钥**: 点击设置按钮，输入你的API密钥
2. **创建聊天室**: 点击"新建聊天"，选择Agent数量和模型
3. **开始对话**: 发送消息开始与Agent对话
4. **多Agent讨论**: 创建多Agent房间，观看Agent之间的智能讨论

## 📊 系统架构设计

### 单Agent对话流程
```
用户输入 → WebSocket → 房间管理器 → Agent处理 → 模型调用 → 响应生成 → WebSocket → 前端显示
```

### 多Agent连续讨论流程
```
用户输入 → 讨论启动 → Agent选择 → 并行SVR计算 → 决策判断 → Agent发言 → 消息广播 → 循环继续
```

### SVR决策机制
```
所有Agent并行计算SVR → 汇总结果 → Delta分析 → 停止/继续/重复决策 → 下一轮讨论
```

### WebSocket通信架构
```
前端 ↔ WebSocket连接 ↔ 消息路由器 ↔ 房间管理器 ↔ Agent系统 ↔ 讨论框架
```

### 数据存储架构
```
内存缓存 ← → localStorage ← → IndexedDB ← → 文件系统持久化
```

## 🎨 用户界面

### 界面特性
- **现代化设计**: 简约清晰的UI设计，支持日夜模式切换
- **房间管理**: 左侧房间列表，支持创建、删除、搜索聊天室
- **实时聊天**: 中央聊天区域，实时显示用户和Agent消息
- **Agent信息**: 显示Agent头像、名称和角色信息
- **设置面板**: 完整的API配置和系统设置管理
- **响应式布局**: 适配不同屏幕尺寸和设备

### 主题系统
- **白天模式**: 蓝白配色，清新简洁的视觉体验
- **夜间模式**: 橙黑配色，护眼舒适的暗色主题
- **动态效果**: 平滑的过渡动画和交互反馈
- **自适应元素**: Agent名称框根据内容长度自动调整

### 交互功能
- **实时消息**: WebSocket实时消息传输，无延迟显示
- **消息去重**: 智能防重复，确保消息显示的准确性
- **自动滚动**: 新消息自动滚动到底部，保持最佳阅读体验
- **离线支持**: 本地存储确保数据不丢失，支持离线查看历史

## 🔧 配置说明

### config.yaml 配置文件
```yaml
# 模型配置
models:
  openai:
    api_key: "your_openai_api_key"
    base_url: "https://api.openai.com/v1"
    model: "gpt-4"
    max_tokens: 4000
    temperature: 0.7

  zhipu:
    api_key: "your_zhipu_api_key"
    base_url: "https://open.bigmodel.cn/api/paas/v4/"
    model: "glm-4-flash-250414"
    max_tokens: 4000
    temperature: 0.7

# 服务器配置
server:
  host: "localhost"
  port: 8000
  debug: true
  cors_origins: ["*"]
  websocket_timeout: 300

# 连续讨论配置
discussion:
  max_agents: 10
  max_rounds: 50
  svr_threshold: 0.7
  delta_cap: 0.2
  parallel_svr: true

# 存储配置
storage:
  enable_persistence: true
  room_storage_path: "workspace/rooms"
  auto_save_interval: 30
  max_history_length: 1000

# 上下文工程配置
context_engineer:
  max_context_length: 8000
  compression_threshold: 0.95
  memory_types: ["episodic", "procedural", "semantic"]
  retrieval_top_k: 5

# 日志配置
logging:
  level: "DEBUG"
  file_enabled: true
  console_enabled: true
```

## 📝 开发指南

### 创建专业Agent角色
```python
from Item.Agentlib.Agent import Agent

# 创建专业领域Agent
def create_expert_agent(agent_id, expertise, model_config):
    agent = Agent(agent_id=agent_id)

    # 设置专业角色提示词
    system_prompt = f"""你是一位{expertise}专家，具有深厚的专业知识和丰富的实践经验。
    在多Agent讨论中，请从{expertise}的角度提供专业见解和建设性意见。
    保持客观、准确，并能够与其他专家进行高质量的学术讨论。"""

    agent.set_system_prompt(system_prompt)
    agent.set_model_config(model_config)
    return agent

# 使用示例
historian = create_expert_agent("hist_001", "历史学", {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
})
```

### 自定义讨论配置
```python
# 创建特定主题的讨论房间
discussion_config = {
    "room_name": "AI伦理讨论",
    "agents": [
        {"role": "哲学家", "model": "gpt-4"},
        {"role": "技术专家", "model": "glm-4-flash"},
        {"role": "法律专家", "model": "gpt-4"}
    ],
    "discussion_settings": {
        "max_rounds": 30,
        "svr_threshold": 0.7,
        "enable_parallel_svr": True
    },
    "initial_topic": "人工智能在决策中的伦理考量"
}
```

### 扩展SVR决策机制
```python
# 自定义SVR评估策略
class CustomSVRStrategy:
    def calculate_stop_score(self, discussion_history):
        # 基于讨论完整性评估是否应该停止
        return stop_score

    def calculate_value_score(self, agent_response, context):
        # 评估Agent响应的价值和贡献
        return value_score

    def calculate_repeat_score(self, recent_messages):
        # 检测内容重复程度
        return repeat_score
```

## 🐛 调试和监控

### 日志系统
- **分层日志**: 支持DEBUG、INFO、WARNING、ERROR等级别
- **实时监控**: 服务器控制台实时显示系统状态
- **WebSocket诊断**: 详细的连接状态和消息传输日志
- **讨论流程追踪**: 完整的多Agent讨论过程记录
- **SVR决策日志**: 详细的Stop-Value-Repeat计算过程

### 前端调试
```javascript
// 浏览器控制台查看WebSocket消息
console.log('WebSocket状态:', window.wsManager?.ws?.readyState);
console.log('当前房间:', window.chatManager?.currentRoomId);

// 查看存储系统状态
window.storageManager?.getStorageStats().then(stats => {
    console.log('存储统计:', stats);
});
```

### 服务器调试
```bash
# 启动调试模式
python Server.py --debug

# 查看特定模块日志
grep "ContinuousDiscussionController" logs/server.log

# 监控WebSocket连接
grep "WebSocket" logs/server.log | tail -20
```
### 常见问题排查

**问题1: Agent消息不显示**
```bash
# 检查WebSocket连接状态
grep "WebSocket connected" logs/server.log

# 检查消息广播
grep "WebSocket广播成功" logs/server.log

# 前端检查
# 浏览器控制台应该看到 "💬 Processing new_message"
```

**问题2: 连续讨论不启动**
```bash
# 检查SVR引擎状态
grep "SVR引擎" logs/server.log

# 检查Agent配置
grep "Agent配置" logs/server.log
```

## 🔒 安全特性

### 数据安全
- **API密钥保护**: 配置文件中的敏感信息加密存储
- **房间隔离**: 不同聊天室的数据完全隔离
- **会话管理**: 自动清理过期的WebSocket连接
- **输入验证**: 严格的用户输入验证和过滤

### 隐私保护
- **本地存储**: 聊天记录优先存储在本地浏览器
- **数据清理**: 支持手动清理聊天历史和缓存
- **匿名化**: Agent讨论中不包含用户个人信息

## 📈 性能优化

### 实时通信优化
- **WebSocket连接池**: 高效的连接管理和复用
- **消息去重**: 防止重复消息影响性能
- **批量处理**: 消息的批量发送和处理
- **自动重连**: 网络中断时的自动恢复机制

### 存储性能
- **三层存储**: 内存→localStorage→IndexedDB的分层缓存
- **智能索引**: 基于时间、房间、发送者的多维索引
- **异步操作**: 所有存储操作都是异步非阻塞的
- **数据压缩**: 长期存储数据的智能压缩

## 📚 API文档

### WebSocket API
```javascript
// 连接WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// 发送消息
ws.send(JSON.stringify({
    type: 'send_message',
    room_id: 'room_123',
    content: '你好，请开始讨论AI的未来发展'
}));

// 创建房间
ws.send(JSON.stringify({
    type: 'create_room',
    room_name: '技术讨论',
    agents: [
        {name: 'Agent 1', model: 'gpt-4'},
        {name: 'Agent 2', model: 'glm-4-flash'}
    ]
}));
```

### 前端存储API
```javascript
// 获取存储管理器
const storage = window.storageManager;

// 保存消息
await storage.saveMessage(roomId, messageData);

// 获取房间历史
const history = await storage.getRoomHistory(roomId);

// 获取存储统计
const stats = await storage.getStorageStats();
```

### 连续讨论API
```python
# 创建讨论框架
from Server.discussion_framework import FrameworkManager

framework = FrameworkManager()

# 启动连续讨论
await framework.start_continuous_discussion(
    room_id="room_123",
    agents=agent_list,
    initial_message="讨论主题"
)

# 停止讨论
await framework.stop_discussion(room_id)
```




## 🌟 项目亮点

SocioPulse-AI 不仅仅是一个聊天工具，更是一个**智能讨论生态系统**：

- **🤖 真正的多Agent智能**: 不是简单的轮流发言，而是基于SVR机制的智能决策
- **🧠 深度上下文理解**: 上下文工程系统，让Agent具备真正的记忆和理解能力
- **💾 智能数据管理**: 三层存储架构，确保数据安全和访问效率
- **🎯 专业级讨论**: 支持学术讨论、技术辩论、创意头脑风暴等多种场景

**SocioPulse-AI** - 让AI协作更智能，让多元讨论更深入。
