# MultiAI - 多Agent智能聊天系统 2025/7/15

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

## 📁 项目结构

```
MultiAI/
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
├── Server.py                       # 后端服务器
├── MultiAI.html                    # 前端界面
├── config.yaml                     # 配置文件
└── README.md                       # 项目文档
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

**MultiAI** - 让AI协作更简单，让智能交互更自然。
