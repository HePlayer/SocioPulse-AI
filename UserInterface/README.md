# SocioPulse AI 用户界面

## 文件结构

```
UserInterface/
├── index.html                 # 主页面入口
├── assets/
│   ├── css/
│   │   ├── themes.css        # 主题样式（浅色/深色模式）
│   │   ├── main.css          # 主要样式（布局、基础组件）
│   │   └── components.css    # 组件样式（模态框、按钮等）
│   └── js/
│       ├── utils.js          # 工具函数（通知、主题切换、消息去重）
│       ├── websocket.js      # WebSocket连接管理
│       ├── settings.js       # 设置管理（配置、存储）
│       ├── chat.js           # 聊天管理（房间、消息）
│       └── main.js           # 主入口文件（应用初始化）
└── README.md                 # 本文件
```

## 功能模块

### CSS 模块
- **themes.css**: 管理浅色/深色主题的颜色变量和主题切换相关样式
- **main.css**: 包含页面布局、基础组件样式、响应式设计
- **components.css**: 专门的组件样式，如模态框、下拉菜单、设置面板等

### JavaScript 模块
- **utils.js**: 提供通用工具函数，包括通知系统、主题切换、消息去重系统
- **websocket.js**: 管理WebSocket连接、重连机制、消息处理
- **settings.js**: 处理用户设置的加载、保存、同步，包括模型配置和功能设置
- **chat.js**: 管理聊天功能，包括房间创建、消息发送接收、Agent配置
- **main.js**: 应用程序的主入口，负责初始化各个模块和全局事件绑定

## 使用说明

1. 将整个UserInterface文件夹部署到Web服务器
2. 通过浏览器访问 `index.html`
3. 确保后端服务器正在运行并支持WebSocket连接

## 特性

- 模块化架构，便于维护和扩展
- 响应式设计，支持桌面和移动设备
- 浅色/深色主题切换
- 实时WebSocket通信
- 本地存储和服务器同步的设置管理
- 消息去重机制防止重复显示
- 完整的错误处理和用户反馈

## 开发说明

各个模块通过全局变量进行通信：
- `window.app`: 主应用实例
- `window.wsManager`: WebSocket管理器
- `window.settingsManager`: 设置管理器
- `window.chatManager`: 聊天管理器

修改任何模块时请确保不破坏模块间的接口约定。
