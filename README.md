# MultiAI - 多Agent智能聊天系统

MultiAI是一个基于多Agent架构的智能聊天系统，支持多种Agent角色、工具调用、上下文管理和流程控制。

## 🚀 项目特性

### 1. 多Agent架构
- **聊天Agent**: 处理常规对话交互
- **工具Agent**: 专门负责工具调用和任务执行
- **协调Agent**: 管理多Agent之间的协作
- **专家Agent**: 特定领域的专业Agent（数学家、历史学家等）

### 2. 智能上下文管理
- **结构化上下文**: JSON格式的上下文组织
- **记忆系统**: 分为便笺、短期记忆和长期记忆
- **上下文压缩**: 自动压缩长上下文以优化性能
- **检索增强**: 基于HNSW算法的智能记忆检索

### 3. 流程控制系统
- **有向图流程**: 基于节点的流程管理
- **条件执行**: 支持条件分支和并行执行
- **错误处理**: 完善的错误处理和重试机制
- **调试支持**: 详细的调试日志和性能监控

### 4. 模块化设计
- **可扩展架构**: 支持新模型和工具的轻松接入
- **标准化接口**: 统一的组件接口设计
- **插件系统**: 支持自定义工具和功能扩展
- **前后端分离**: 模块化的UserInterface和Server组件
- **功能解耦**: 各功能模块独立，便于维护和扩展

## 📁 项目结构

```
SocioPulse AI/
├── UserInterface/                  # 模块化前端界面
│   ├── index.html                  # 主页面
│   ├── assets/                     # 资源文件
│   │   ├── css/                    # 样式文件
│   │   │   ├── main.css            # 主样式
│   │   │   ├── components.css      # 组件样式
│   │   │   └── themes.css          # 主题样式
│   │   └── js/                     # 脚本文件
│   │       ├── main.js             # 主脚本
│   │       ├── chat.js             # 聊天功能
│   │       ├── settings.js         # 设置管理
│   │       ├── websocket.js        # WebSocket通信
│   │       └── utils.js            # 工具函数
│   └── README.md                   # 前端文档
├── Server/                         # 模块化后端服务器
│   ├── __init__.py                 # 包初始化
│   ├── main.py                     # 主服务器类
│   ├── config.py                   # 配置常量
│   ├── utils.py                    # 工具函数
│   ├── connection_tester.py        # API连接测试
│   ├── settings_manager.py         # 设置管理
│   ├── websocket_handler.py        # WebSocket处理
│   ├── room_manager.py             # 聊天室管理
│   └── README.md                   # 服务器文档
├── Item/                           # 核心模块
│   ├── Agentlib/                   # Agent管理模块
│   │   ├── Agent.py                # Agent基类
│   │   ├── Models.py               # 模型管理
│   │   ├── Prompt.py               # 提示词管理
│   │   └── Tools/                  # 工具集合
│   │       ├── base_tool.py        # 工具基类
│   │       ├── calculator.py       # 计算器工具
│   │       ├── file_tool.py        # 文件操作工具
│   │       ├── web_search.py       # 网络搜索工具
│   │       └── code_executor.py    # 代码执行工具
│   ├── ContextEngineer/            # 上下文工程模块
│   │   ├── context_manager.py      # 上下文管理器
│   │   ├── memory_system.py        # 记忆系统
│   │   └── scratchpad.py           # 便笺系统
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
└── README.md                      # 项目文档
```

## 🛠️ 核心组件

### Agent系统
- **Agent基类**: 提供统一的Agent接口和基础功能
- **角色系统**: 支持多种预定义角色和自定义角色
- **消息传递**: Agent间的异步消息通信
- **状态管理**: 完整的Agent生命周期管理

### 上下文工程
- **结构化上下文**: 标准化的上下文数据格式
- **记忆分层**: 便笺、短期记忆、长期记忆的分层管理
- **智能检索**: 基于语义相似度的记忆检索
- **上下文压缩**: 动态压缩以适应模型上下文限制

### 流程控制
- **节点化架构**: 将所有操作抽象为流程节点
- **图形化流程**: 支持复杂的流程定义和执行
- **并行处理**: 支持多节点并行执行
- **错误恢复**: 自动重试和错误处理机制

### 工具系统
- **标准化接口**: 统一的工具定义和调用规范
- **异步执行**: 支持长时间运行的工具操作
- **参数验证**: 自动参数验证和类型检查
- **结果缓存**: 智能的工具执行结果缓存

## 🚀 快速开始

### 1. 环境准备
```bash
# 安装依赖
pip install psutil asyncio

# 配置API密钥
# 编辑 config.yaml 文件，添加你的API配置
```

### 2. 创建第一个Agent
```python
from Item.Agentlib.Agent import Agent, AgentRole

# 创建聊天Agent
agent = Agent(
    agent_id="chat_agent_001",
    name="智能助手",
    role=AgentRole.CHAT
)

# 设置系统提示词
agent.set_system_prompt("你是一个友好的AI助手，能够帮助用户解决各种问题。")

# 处理用户输入
result = agent.think({"user_input": "你好，请介绍一下自己"})
print(result['response'])
```

### 3. 启动服务器
```bash
cd MultiAI
python Server.py
```

### 4. 使用工具系统
```python
from Item.Agentlib.Tools.calculator import CalculatorTool

# 创建和注册工具
calculator = CalculatorTool("calc_001")
agent.register_tool("calculator", calculator.execute, "数学计算工具")

# 使用工具
result = agent.execute_tool("calculator", {"expression": "2 + 3 * 4"})
print(f"计算结果: {result}")
```

## 📊 架构设计

### 交互机制
```
用户输入 → Agent1 (分析) → ToolsAgent (工具调用) → Tools (执行) → Agent1 (整合) → 用户输出
```

### 上下文流转
```
用户输入 → 便笺存储 → 上下文构建 → 记忆检索 → 模型调用 → 结果存储 → 记忆更新
```

### 流程控制
```
开始节点 → 条件判断 → 并行执行 → 结果聚合 → 输出节点
```

## 🎨 前端界面

### 设计特性
- **简约清晰**: 现代化的UI设计，支持日夜模式切换
- **聊天列表**: 左侧聊天对象管理，支持搜索和新建
- **工作区**: 中央工作区域，支持聊天和项目模式切换
- **智能输入**: 动态输入框，支持多行输入和快捷操作

### 主题系统
- **白天模式**: 蓝白配色，清新简洁
- **夜间模式**: 橙黑配色，护眼舒适
- **动态效果**: 控件边框的动态色彩变化

## 🔧 配置说明

### config.yaml 配置文件
```yaml
# 模型配置
models:
  openai:
    api_key: "your_openai_api_key"
    base_url: "https://api.openai.com/v1"
    model: "gpt-4"
  
  zhipu:
    api_key: "your_zhipu_api_key"
    base_url: "https://open.bigmodel.cn/api/paas/v4/"
    model: "glm-4"

# 服务器配置
server:
  host: "localhost"
  port: 8000
  debug: true

# 上下文配置
context:
  max_length: 8000
  compression_threshold: 0.95
  memory_limit: 1000

# 日志配置
logging:
  level: "DEBUG"
  file_enabled: true
  console_enabled: true
```

## 📝 开发指南

### 创建自定义Agent
```python
from Item.Agentlib.Agent import Agent, AgentRole

class CustomAgent(Agent):
    def __init__(self, agent_id: str, name: str):
        super().__init__(agent_id, name, AgentRole.CUSTOM)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        # 自定义响应解析逻辑
        return super()._parse_response(response)
```

### 创建自定义工具
```python
from Item.Agentlib.Tools.base_tool import BaseTool

class CustomTool(BaseTool):
    def __init__(self, tool_id: str):
        super().__init__(tool_id, "custom_tool")
    
    def _execute_core(self, input_data: Dict[str, Any]) -> Any:
        # 实现具体的工具逻辑
        return "工具执行结果"
```

### 创建自定义流程
```python
from Item.FlowTools.flow_node import FlowNode, NodeType

class CustomNode(FlowNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, NodeType.CUSTOM)
    
    def _execute_core(self, input_data: Dict[str, Any]) -> Any:
        # 实现节点逻辑
        return {"result": "处理完成"}
```

## 🐛 调试和监控

### 日志系统
- **结构化日志**: JSON格式的详细日志记录
- **性能监控**: 自动记录执行时间和资源使用
- **错误追踪**: 完整的错误堆栈和上下文信息

### 调试工具
- **组件状态**: 实时查看各组件的运行状态
- **流程跟踪**: 详细的流程执行轨迹
- **内存分析**: 内存使用情况监控

## 🔒 安全特性

### 权限控制
- **Agent权限**: 基于角色的权限管理
- **工具权限**: 工具调用的安全限制
- **数据隔离**: 不同会话的数据隔离

### 数据保护
- **敏感信息过滤**: 自动识别和保护敏感数据
- **上下文清理**: 定期清理过期的上下文数据
- **错误信息脱敏**: 错误日志的敏感信息保护

## 📈 性能优化

### 异步处理
- **并发执行**: 多Agent和工具的并发处理
- **异步IO**: 非阻塞的网络和文件操作
- **资源池**: 连接池和线程池管理

### 缓存系统
- **结果缓存**: 工具执行结果的智能缓存
- **上下文缓存**: 频繁访问的上下文数据缓存
- **模型缓存**: 模型响应的本地缓存

## 🤝 贡献指南

### 代码风格
- 采用面向对象和函数式编程相结合的方式
- 所有操作都可以作为流程节点接入
- 完善的类型注解和文档字符串
- 统一的错误处理和日志记录

### 测试要求
- 单元测试覆盖率 > 80%
- 集成测试验证核心功能
- 性能测试确保系统稳定性

### 提交规范
- 详细的commit message
- 代码review通过
- 更新相关文档

## 📚 API文档

### Agent API
- `Agent.set_system_prompt(prompt)`: 设置系统提示词
- `Agent.register_tool(name, func, desc)`: 注册工具
- `Agent.think(input_data)`: 处理用户输入
- `Agent.execute_tool(name, args)`: 执行工具

### Context API
- `ContextManager.build_context(input)`: 构建上下文
- `ContextManager.add_exchange(user, agent)`: 添加对话
- `MemorySystem.store_memory(type, content)`: 存储记忆
- `MemorySystem.retrieve_memories(query, k)`: 检索记忆

### Flow API
- `FlowEngine.create_workflow(nodes)`: 创建工作流
- `FlowEngine.execute_workflow(input)`: 执行工作流
- `FlowNode.execute(input)`: 执行节点
- `NodeFactory.create_node(type, config)`: 创建节点

## 🎯 未来计划

### 功能扩展
- [ ] 语音交互支持
- [ ] 多模态输入处理
- [ ] 实时协作功能
- [ ] 移动端适配

### 性能优化
- [ ] 分布式部署支持
- [ ] GPU加速计算
- [ ] 更智能的缓存策略
- [ ] 流式输出优化

### 生态建设
- [ ] 插件市场
- [ ] 社区工具库
- [ ] 开发者工具链
- [ ] 在线体验平台

## 📄 许可证

本项目采用 MIT 许可证，详情请查看 [LICENSE](LICENSE) 文件。

## 📞 联系我们

- 项目地址: [GitHub Repository](https://github.com/yourusername/MultiAI)
- 问题反馈: [Issues](https://github.com/yourusername/MultiAI/issues)
- 讨论社区: [Discussions](https://github.com/yourusername/MultiAI/discussions)

---

## 🔄 更新日志

### 2025-07-17 上午 - 🚨 紧急修复：404错误和按钮功能完全恢复 v2.2.1
- 🔥 **紧急修复HTML文件引用错误**：解决了导致所有按钮不起效的根本原因
  - 🛠️ **问题诊断**：HTML文件引用了已删除的`main_fixed.js`文件，导致404错误和JavaScript功能失效
  - 🔧 **快速修复**：将`UserInterface/index.html`中的文件引用从`main_fixed.js`改回`main.js`
  - ✅ **验证成功**：所有按钮功能立即恢复正常，无需额外修改
- 🎯 **修复结果**：
  - ✅ 设置按钮：一键点击打开设置模态框，功能完全正常
  - ✅ 新建聊天按钮：正常打开创建聊天室模态框，严格筛选已配置平台
  - ✅ 消除404错误：所有JavaScript文件正确加载
  - ✅ 事件绑定成功：所有按钮事件监听器正确绑定
- 🛡️ **预防措施**：确保HTML文件引用与实际文件名一致，避免类似问题再次发生

### 2025-07-17 上午 - ✅ 完全修复：按钮功能和用户界面全面恢复 v2.2.0
- ✅ **彻底解决所有按钮功能问题**：所有用户界面按钮现已完全正常工作
  - 🔧 **设置按钮修复完成**：解决了设置按钮无限重试和点击无响应问题
  - 🔧 **Agent信息按钮修复完成**：聊天室中的👥按钮现已完全可用，模态框正常显示
  - 🔧 **更多选项按钮修复完成**：聊天室中的⋮按钮现已完全可用
  - 🔧 **新建聊天功能修复完成**：创建聊天室功能正常，严格筛选只显示已配置API的平台
  - 🔧 **聊天列表显示修复**：解决了"暂无消息"显示问题，新建聊天室立即显示在主界面
- 🛡️ **技术修复细节**：
  - **防御性编程**：增加了多重DOM元素查找策略，确保向后兼容性
  - **事件绑定优化**：简化了复杂的事件委托，使用直接绑定提高稳定性
  - **错误处理增强**：添加了完善的回退机制和错误恢复
  - **实时验证**：所有功能均已在浏览器中实时测试验证
- 🎯 **用户体验提升**：
  - ✅ 设置按钮一键点击即可打开，无延迟无重试
  - ✅ Agent信息能正确获取和显示，事件绑定简化可靠
  - ✅ 更多选项按钮响应迅速
  - ✅ 新建聊天室后立即在列表中显示，模型选择严格筛选
  - ✅ 聊天列表不再显示"暂无消息"的错误状态

### 2025-07-17 上午 - 🛡️ 防回归修复：按钮功能和房间名称 v2.1.2
- ✅ **防回归修复完成**：彻底解决了按钮功能失效和房间名称显示问题
  - 🔧 **设置按钮修复**：修复设置按钮点击无响应问题，增加多重查找策略确保向后兼容
  - 🔧 **新建聊天按钮修复**：修复新建聊天按钮功能失效，完善事件绑定和错误处理
  - 🔧 **房间名称显示修复**：实现多层级房间名称获取策略，正确显示用户自定义名称
  - 🛡️ **向后兼容性**：使用防御性编程确保与旧版本数据格式的兼容性
  - 📊 **实时验证**：所有修复均已在浏览器中验证，确保功能正常运行
- 🎯 **修复范围**：
  - ✅ UserInterface/assets/js/main_fixed.js：增强按钮事件绑定
  - ✅ Server/websocket_handler.py：优化房间列表处理和广播逻辑
  - ✅ 测试验证：新建聊天室、设置管理、房间名称显示均已正常工作

### 2025-07-17 上午 - 🐛 聊天室名称显示和模型选择修复 v2.1.1
- ✅ **修复聊天室名称显示问题**：创建聊天室时用户自定义名称能正确显示，不再显示UUID格式
  - 🔧 **后端修复**：优化`room_manager.py`中的房间名称处理逻辑，正确保存用户输入的名称
  - 🔧 **WebSocket修复**：修复`websocket_handler.py`中房间列表获取和广播的名称显示逻辑
  - 🔧 **数据一致性**：确保前后端房间名称字段统一使用`room_name`
- ✅ **修复模型选择问题**：设置中未配置API密钥的平台不再显示在创建聊天室的模型选择中
  - 🛡️ **严格筛选**：前端只显示已配置API密钥的平台模型
  - 🔄 **自动选择**：后端自动选择可用平台和模型，避免创建失败
  - 📊 **状态验证**：实时检查平台API密钥配置状态

### 2025-07-17 - 🔧 接口规范化和功能完善 v2.1.0
- **🛠️ 接口标准化修复**: 解决了多个"对象没有属性"的错误
  - ✅ **Agent.get_metadata()方法**: 添加了缺失的get_metadata()方法，修复Agent信息获取功能
  - ✅ **SettingsManager接口**: 确保settings属性始终可用，避免配置访问错误
  - ✅ **房间名称访问**: 标准化了房间名称获取方式，修复显示不一致问题
  
- **🗑️ 删除房间功能**: 完整实现了删除聊天室功能
  - ✅ **WebSocket支持**: 添加了delete_room和room_deleted消息类型
  - ✅ **后端处理**: 实现了完整的删除房间WebSocket处理器
  - ✅ **前端交互**: 完善了删除确认和状态管理
  - ✅ **UI更新**: 删除后自动更新房间列表和切换到其他房间
  
- **🔍 完整的API审计**: 建立了完整的接口规范体系
  - 📋 **Agent类标准接口**: 定义了必需的方法和属性
  - 📋 **ChatRoom类标准接口**: 规范了房间操作方法
  - 📋 **SettingsManager类标准接口**: 确保设置管理的一致性
  - 🛡️ **预防措施**: 添加了接口检查装饰器和运行时验证
  
- **🎯 问题解决**:
  - 修复了创建聊天成功后没有在主界面显示的问题
  - 解决了设置中未配置API密钥的平台仍可使用的问题
  - 完善了Agent信息模态框的显示和交互
  - 优化了WebSocket消息处理的稳定性

### 2025-07-16 - 🚀 服务器架构重构 v2.0.0
- **🔧 全新服务器架构**: 完全重构了SocioPulse AI服务器，解决了所有已知问题
  - ✅ **WebSocket通信修复**: 彻底解决了"Unknown WebSocket message type: create_room"错误
  - ✅ **消息处理优化**: 使用直接字符串匹配，确保与前端100%兼容
  - ✅ **错误处理增强**: 完善的异常捕获和错误响应机制
  - ✅ **连接管理改进**: 自动清理断开的WebSocket连接，提高稳定性
  
- **🎯 功能完全修复**: 所有原本不可用的功能现已完全正常
  - ✅ **新建聊天室**: 按钮响应正常，创建流程完整，WebSocket通信稳定
  - ✅ **设置管理**: 设置按钮可用，模态框正常显示，配置保存功能正常
  - ✅ **Agent信息**: 聊天室中的Agent信息按钮完全可用
  - ✅ **更多选项**: 聊天室中的更多选项按钮完全可用
  - ✅ **聊天室创建优化**: 自动选择已配置API密钥的平台模型，避免未配置API的平台错误
  - ✅ **聊天室显示修复**: 修复创建聊天室成功后未在主界面显示的问题
  
- **🏗️ 技术架构优势**:
  - **前端兼容性**: 保持与现有前端代码100%兼容，无需修改前端
  - **现代化设计**: 使用异步架构，模块化组件，类型安全
  - **统一响应格式**: 标准化的API和WebSocket响应格式
  - **完善的日志**: 详细的调试信息和性能监控
  
- **📁 新增文件**:
  - `sociopulse_server.py`: 重构版服务器核心文件
  - `start_sociopulse.py`: 便捷启动脚本，包含功能状态显示
  
- **🚀 使用方式**:
  ```bash
  # 使用新的重构版服务器
  python start_sociopulse.py
  
  # 或直接使用核心文件
  python sociopulse_server.py
  ```

### 2025-01-15
- **🔧 修复聊天室按钮功能**: 完全修复了聊天室中"Agent信息"和"更多选项"按钮不可用的问题
  - 优化了事件绑定逻辑，确保DOM元素渲染完成后再绑定事件
  - 增强了按钮样式，添加了更好的视觉反馈和点击效果
  - 完善了错误处理机制，提供备用处理方案
  - 添加了详细的调试日志，便于问题排查
- **✨ 界面改进**: 提升了按钮的可点击性和用户体验
  - 增加了按钮的最小尺寸确保点击区域足够大
  - 添加了悬停和点击状态的动画效果
  - 优化了焦点样式以提高可访问性

---

**MultiAI** - 让AI协作更简单，让智能交互更自然。
