# 多Agent讨论框架

## 概述

这是一个完整的多Agent讨论框架，实现了连续循环架构和并行SVR（Stop-Value-Repeat）计算。框架提供实时监控、事件驱动的架构，并与现有的SocioPulse AI系统完全集成。

## 核心特性

### 🔄 连续循环架构
- 实现伪代码中的连续讨论循环
- 并行SVR计算不阻塞讨论流程
- 实时决策制定和Agent选择

### ⚡ 并行SVR计算
- 同时为所有Agent计算SVR值
- 异步处理确保高性能
- 自适应阈值和智能决策

### 🎯 智能决策系统
- 基于SVR结果的自动决策
- 支持停止、继续、暂停、重定向操作
- 质量监控和干预机制

### 🔗 完整系统集成
- 与现有ChatRoom、Agent.think()无缝集成
- 保持向后兼容性
- 支持EnhancedMessageHistory和CommunicationStrategy

### 📡 实时监控
- WebSocket实时事件推送
- 前端兼容的数据格式
- 性能指标和统计信息

## 架构组件

```
┌─────────────────────────────────────────────────────────────┐
│                 多Agent讨论框架                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ContinuousController│  │ParallelSVREngine│  │ SVRHandler   │ │
│  │                 │  │                 │  │              │ │
│  │ - 连续循环      │  │ - 并行计算      │  │ - 决策制定   │ │
│  │ - 上下文管理    │  │ - 实时监控      │  │ - Agent选择  │ │
│  │ - 流程控制      │  │ - 异步处理      │  │ - 停止逻辑   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│           │                     │                   │       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │DiscussionContext│  │ AgentSVRComputer│  │EventInterface│ │
│  │                 │  │                 │  │              │ │
│  │ - 状态跟踪      │  │ - 个体SVR       │  │ - 前端兼容   │ │
│  │ - 历史管理      │  │ - Agent分析     │  │ - 实时事件   │ │
│  │ - 实时数据      │  │ - 并行安全      │  │ - WebSocket  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## API端点

### 启动增强讨论
```http
POST /api/discussion/start
Content-Type: application/json

{
  "room_id": "room_123",
  "user_input": "请讨论人工智能的发展趋势"
}
```

### 获取讨论状态
```http
GET /api/discussion/status/{room_id}
```

### 控制讨论
```http
POST /api/discussion/control/{room_id}
Content-Type: application/json

{
  "action": "pause|resume|stop"
}
```

### 获取所有讨论状态
```http
GET /api/discussion/all-status
```

### WebSocket实时更新
```
ws://localhost:8080/ws/discussion/{room_id}
```

## 使用示例

### 基本使用

```python
from Server.discussion_framework import DiscussionFrameworkManager
from Item.Communication.message_types import ChatMessage, MessageType

# 创建框架管理器
manager = DiscussionFrameworkManager()

# 准备参与者（Agent字典）
participants = {
    'agent_1': ai_expert_agent,
    'agent_2': tech_analyst_agent,
    'agent_3': product_manager_agent
}

# 创建初始消息
initial_message = ChatMessage(
    sender_id="user",
    content="请讨论人工智能在未来5年的发展趋势",
    message_type=MessageType.TEXT
)

# 启动增强讨论
result = await manager.start_enhanced_discussion(
    room_id="ai_discussion_room",
    topic="AI发展趋势讨论",
    participants=participants,
    initial_message=initial_message
)

if result['success']:
    print(f"讨论启动成功: {result['session_id']}")
    
    # 监控讨论状态
    while True:
        status = await manager.get_discussion_status("ai_discussion_room")
        if not status.get('discussion', {}).get('active'):
            break
        await asyncio.sleep(5)
    
    print("讨论已结束")
```

### 事件监听

```python
from Server.discussion_framework import ContinuousDiscussionController

controller = ContinuousDiscussionController()

# 设置事件处理器
async def on_turn_complete(turn):
    print(f"轮次完成: {turn.agent_name} 说: {turn.message.content[:50]}...")

async def on_decision_made(decision):
    print(f"决策: {decision.action.value} - 选择 {decision.selected_agent_name}")

controller.on_turn_complete = on_turn_complete
controller.on_decision_made = on_decision_made
```

### 前端集成

```javascript
// WebSocket连接
const ws = new WebSocket('ws://localhost:8080/ws/discussion/room_123');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'initial_status':
            updateDiscussionStatus(data.data);
            break;
        case 'event':
            handleDiscussionEvent(data);
            break;
        case 'status_update':
            updateDiscussionStatus(data.data);
            break;
    }
};

function updateDiscussionStatus(status) {
    document.getElementById('discussion-quality').textContent = 
        status.metrics.discussion_quality.toFixed(1);
    document.getElementById('consensus-level').textContent = 
        status.metrics.consensus_level.toFixed(1);
}
```

## SVR算法详解

### Stop Value (停止值)
- **共识贡献**: Agent对达成共识的贡献度
- **讨论饱和**: 从Agent角度看的讨论饱和程度
- **Agent疲劳**: Agent的疲劳指标
- **全局状态**: 整体讨论的停止信号
- **时间因子**: 基于讨论持续时间的因子

### Value Score (价值分数)
- **轮次质量**: 最近发言的质量评估
- **历史表现**: Agent的历史贡献价值
- **互动潜力**: 产生有意义互动的潜力
- **专业相关性**: 与讨论主题的相关程度

### Repeat Risk (重复风险)
- **自我相似性**: 与自己之前发言的相似度
- **模式重复**: 交流模式的重复程度
- **论点回收**: 重复使用相同论点的风险
- **频率风险**: 基于发言频率的重复风险

## 配置选项

```python
controller = ContinuousDiscussionController(
    max_turns=50,                    # 最大轮次数
    max_duration=3600,               # 最大持续时间（秒）
    svr_computation_interval=1.0,    # SVR计算间隔
    enable_real_time_updates=True    # 启用实时更新
)

svr_handler = SVRHandler(
    stop_threshold=0.8,              # 停止阈值
    consensus_threshold=0.85,        # 共识阈值
    quality_threshold=30.0           # 质量阈值
)
```

## 性能监控

框架提供详细的性能指标：

- **计算效率**: 并行SVR计算的效率统计
- **决策准确性**: 决策制定的准确性跟踪
- **参与度平衡**: 各Agent参与度的平衡性
- **讨论质量趋势**: 讨论质量的变化趋势

## 测试

运行测试套件：

```bash
cd Server/discussion_framework
python test_framework.py
```

测试包括：
- 基本框架功能测试
- 框架管理器测试
- SVR计算测试
- 集成测试

## 故障排除

### 常见问题

1. **讨论无法启动**
   - 检查Agent配置是否正确
   - 确认房间存在且有可用Agent
   - 查看日志中的错误信息

2. **SVR计算超时**
   - 检查Agent.think()方法的响应时间
   - 调整SVR计算超时设置
   - 确认网络连接稳定

3. **WebSocket连接失败**
   - 确认讨论会话已启动
   - 检查WebSocket端点路径
   - 验证房间ID正确性

### 日志级别

```python
import logging
logging.getLogger('Server.discussion_framework').setLevel(logging.DEBUG)
```

## 扩展开发

框架设计为可扩展的，支持：

- 自定义SVR算法实现
- 新的决策策略
- 额外的事件类型
- 自定义前端接口

详细的扩展指南请参考开发文档。
