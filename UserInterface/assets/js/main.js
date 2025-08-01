// 主入口文件

class MultiAIApp {
    constructor() {
        this.initialized = false;
        this.wsManager = null;
        this.settingsManager = null;
        this.chatManager = null;
        this.modalManager = null;
    }

    // 初始化应用程序
    async initialize() {
        if (this.initialized) return;

        try {
            console.log('Initializing MultiAI Application...');

            // 初始化设置管理器
            this.settingsManager = new SettingsManager();
            window.settingsManager = this.settingsManager;
            await this.settingsManager.loadSettings();
            
            // 初始化模态框管理器
            this.modalManager = new ModalManager();
            window.modalManager = this.modalManager;

            // 初始化主题
            this.initializeTheme();

            // 初始化WebSocket管理器
            this.wsManager = new WebSocketManager();
            window.wsManager = this.wsManager;

            // 初始化聊天管理器
            this.chatManager = new ChatManager();
            window.chatManager = this.chatManager;

            // 绑定全局事件
            this.bindGlobalEvents();

            // 连接WebSocket
            this.wsManager.connect();

            // 初始化各个模块
            this.chatManager.initialize();

            this.initialized = true;
            console.log('MultiAI Application initialized successfully');

        } catch (error) {
            console.error('Failed to initialize application:', error);
            showNotification('应用程序初始化失败，请刷新页面重试', 'error');
        }
    }

    // 初始化主题
    initializeTheme() {
        // 从设置中获取主题偏好
        const settings = this.settingsManager.getSettings();
        let theme = settings.features.ui.theme;

        // 如果设置中没有，从localStorage获取
        if (!theme) {
            theme = localStorage.getItem('theme') || 'light';
        }

        // 应用主题
        window.currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);

        // 更新主题切换按钮
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.textContent = theme === 'light' ? '🌙' : '☀️';
        }
    }

    // 绑定全局事件
    bindGlobalEvents() {
        console.log('🔧 Starting global event binding...');
        
        // 使用防御性事件绑定
        this.safeBindEvent('.theme-toggle', 'click', toggleTheme, window, '主题切换按钮');
        this.safeBindEvent('#settingsBtn', 'click', () => this.showSettingsModal(), this, '设置按钮');

        // 新建聊天按钮 - 这是一个关键的修复
        this.safeBindEvent('.add-chat-btn', 'click', () => {
            console.log('🆕 新建聊天按钮被点击');
            if (this.chatManager) {
                this.chatManager.showCreateRoomModal();
            } else {
                console.error('❌ ChatManager 未初始化');
                showNotification('聊天管理器未就绪，请刷新页面重试', 'error');
                // 尝试重新初始化
                this.reinitializeChatManager();
            }
        }, this, '新建聊天按钮');

        // 全局事件委托 - 解决动态按钮不响应问题
        this.setupGlobalEventDelegation();

        // 静态模态框事件绑定
        this.safeBindEvent('#closeAgentInfoModal', 'click', () => this.hideAgentInfoModal(), this, 'Agent信息关闭按钮1');
        this.safeBindEvent('#closeAgentInfoBtn', 'click', () => this.hideAgentInfoModal(), this, 'Agent信息关闭按钮2');

        // 设置模态框事件
        this.bindSettingsModalEvents();

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K 快速搜索
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('.search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }

            // ESC 关闭模态框
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });

        // 窗口大小改变事件
        window.addEventListener('resize', () => {
            this.handleWindowResize();
        });

        console.log('✅ Global events binding completed');
    }

    // 设置全局事件委托 - 解决动态按钮问题
    setupGlobalEventDelegation() {
        console.log('🎯 Setting up global event delegation for dynamic buttons...');
        
        // 使用事件委托监听整个文档的点击事件
        document.addEventListener('click', (e) => {
            // Agent信息按钮处理
            if (e.target.id === 'agentInfoBtn' || e.target.closest('#agentInfoBtn')) {
                e.preventDefault();
                e.stopPropagation();
                console.log('👤 Agent info button clicked via delegation');
                this.handleAgentInfoClick();
                return;
            }
            
            // 更多选项按钮处理
            if (e.target.id === 'moreOptionsBtn' || e.target.closest('#moreOptionsBtn')) {
                e.preventDefault();
                e.stopPropagation();
                console.log('⋮ More options button clicked via delegation');
                this.handleMoreOptionsClick(e);
                return;
            }
        });
        
        console.log('✅ Global event delegation setup completed');
    }

    // 处理Agent信息按钮点击
    handleAgentInfoClick() {
        console.log('👤 处理Agent信息按钮点击...');
        
        try {
            // 方法1：尝试使用ChatManager的actionManager
            if (this.chatManager && this.chatManager.actionManager) {
                console.log('✅ 使用ChatManager.actionManager.showAgentInfo');
                this.chatManager.actionManager.showAgentInfo();
                return;
            }
            
            // 方法2：直接调用showAgentInfoModal
            console.log('⚠️ 使用备用方法显示Agent信息');
            this.showAgentInfoModal();
            
        } catch (error) {
            console.error('❌ Agent信息按钮处理出错:', error);
            showNotification('无法显示Agent信息', 'error');
        }
    }

    // 处理更多选项按钮点击
    handleMoreOptionsClick(event) {
        console.log('⋮ 处理更多选项按钮点击...');
        
        try {
            // 方法1：尝试使用ChatManager的actionManager
            if (this.chatManager && this.chatManager.actionManager) {
                console.log('✅ 使用ChatManager.actionManager.showMoreOptions');
                this.chatManager.actionManager.showMoreOptions(event);
                return;
            }
            
            // 方法2：直接调用showMoreOptionsDropdown
            console.log('⚠️ 使用备用方法显示更多选项');
            this.showMoreOptionsDropdown(event);
            
        } catch (error) {
            console.error('❌ 更多选项按钮处理出错:', error);
            showNotification('无法显示更多选项', 'error');
        }
    }

    // 安全的事件绑定方法
    safeBindEvent(selector, eventType, handler, context, description = '') {
        try {
            const element = typeof selector === 'string' 
                ? document.querySelector(selector) 
                : selector;
                
            if (element) {
                const boundHandler = context ? handler.bind(context) : handler;
                element.addEventListener(eventType, boundHandler);
                console.log(`✅ Event bound successfully: ${description || selector}`);
                return true;
            } else {
                console.warn(`⚠️ Element not found for binding: ${description || selector}`);
                return false;
            }
        } catch (error) {
            console.error(`❌ Error binding event for ${description || selector}:`, error);
            return false;
        }
    }

    // 重新初始化聊天管理器
    async reinitializeChatManager() {
        console.log('🔄 Attempting to reinitialize ChatManager...');
        try {
            this.chatManager = new ChatManager();
            window.chatManager = this.chatManager;
            this.chatManager.initialize();
            console.log('✅ ChatManager reinitialized successfully');
            showNotification('聊天管理器已重新初始化', 'success');
        } catch (error) {
            console.error('❌ Failed to reinitialize ChatManager:', error);
            showNotification('重新初始化失败，请刷新页面', 'error');
        }
    }

    // 绑定设置模态框事件
    bindSettingsModalEvents() {
        // 设置模态框
        const settingsModal = document.getElementById('settingsModal');
        const closeSettingsModal = document.getElementById('closeSettingsModal');
        const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');

        if (closeSettingsModal) {
            closeSettingsModal.addEventListener('click', () => this.hideSettingsModal());
        }

        if (cancelSettingsBtn) {
            cancelSettingsBtn.addEventListener('click', () => this.hideSettingsModal());
        }

        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }

        // 点击模态框外部关闭
        if (settingsModal) {
            settingsModal.addEventListener('click', (e) => {
                if (e.target === settingsModal) {
                    this.hideSettingsModal();
                }
            });
        }

        // 标签页切换
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchSettingsTab(tabName);
            });
        });
    }

    // 显示设置模态框
    showSettingsModal() {
        console.log('🛠️ 尝试显示设置模态框...');
        
        try {
            // 初始化设置界面
            console.log('📋 初始化设置UI...');
            this.settingsManager.initializeSettingsUI();
            console.log('✅ 设置UI初始化成功');
            
            // 使用模态框管理器显示设置模态框
            if (this.modalManager && this.modalManager.showModal('settingsModal')) {
                console.log('✅ 设置模态框显示成功');
            } else {
                // 回退方案：直接显示模态框
                const modal = document.getElementById('settingsModal');
                if (modal) {
                    modal.style.display = 'flex';
                    modal.classList.add('show');
                    console.log('⚠️ 使用回退方法显示设置模态框');
                } else {
                    throw new Error('找不到设置模态框元素');
                }
            }
        } catch (error) {
            console.error('❌ 显示设置模态框时出错:', error);
            showNotification('无法显示设置模态框', 'error');
        }
    }

    // 隐藏设置模态框
    hideSettingsModal() {
        if (this.modalManager) {
            this.modalManager.hideModal('settingsModal');
        } else {
            const modal = document.getElementById('settingsModal');
            if (modal) {
                modal.classList.remove('show');
                modal.style.display = 'none';
            }
        }
    }

    // 切换设置标签页
    switchSettingsTab(tabName) {
        // 更新标签按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');

        // 更新标签内容
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`)?.classList.add('active');
    }

    // 保存设置
    async saveSettings() {
        try {
            const newSettings = this.settingsManager.saveCurrentSettings();
            
            // 同步到服务器
            const success = await this.settingsManager.syncToServer();
            
            if (success) {
                showNotification('设置保存成功', 'success');
            } else {
                showNotification('设置已保存到本地，但同步服务器失败', 'warning');
            }
            
            this.hideSettingsModal();
            
        } catch (error) {
            console.error('Error saving settings:', error);
            showNotification('保存设置时出错', 'error');
        }
    }

    // 关闭所有模态框
    closeAllModals() {
        if (this.modalManager) {
            this.modalManager.closeAllModals();
        } else {
            // 回退方案：直接隐藏所有模态框
            const modals = document.querySelectorAll('.modal-overlay');
            modals.forEach(modal => {
                modal.classList.remove('show');
                modal.style.display = 'none';
            });
        }
    }

    // 处理窗口大小改变
    handleWindowResize() {
        // 检查是否为移动设备
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            // 移动设备特殊处理
            const chatList = document.querySelector('.chat-list');
            if (chatList && !chatList.classList.contains('show')) {
                chatList.style.transform = 'translateX(-100%)';
            }
        } else {
            // 桌面设备恢复正常
            const chatList = document.querySelector('.chat-list');
            if (chatList) {
                chatList.style.transform = '';
            }
        }
    }

    // 显示Agent信息模态框 - 使用模态框管理器
    showAgentInfoModal() {
        console.log('👤 显示Agent信息模态框');
        
        // 首选方法：使用ChatManager的actionManager
        if (window.chatManager && window.chatManager.actionManager) {
            console.log('✅ 使用ChatManager.actionManager.showAgentInfo');
            window.chatManager.actionManager.showAgentInfo();
            return;
        }
        
        // 备选方法：使用模态框管理器
        if (this.modalManager && this.modalManager.showModal('agentInfoModal')) {
            console.log('✅ 使用模态框管理器显示Agent信息模态框');
            // 尝试加载Agent信息
            this.loadAgentInfo();
            return;
        }
        
        // 最后的回退方案：直接显示模态框
        console.error('❌ 无法使用标准方法显示Agent信息');
        const modal = document.getElementById('agentInfoModal');
        if (modal) {
            console.log('⚠️ 使用回退方法显示Agent信息模态框');
            modal.style.display = 'flex';
            modal.classList.add('show');
        } else {
            showNotification('无法显示Agent信息', 'error');
        }
    }

    // 加载Agent信息
    async loadAgentInfo() {
        const content = document.getElementById('agentInfoContent');
        if (!content) return;

        try {
            // 显示加载状态
            content.innerHTML = `
                <div class="loading-placeholder">
                    <div class="loading-spinner"></div>
                    <p>加载Agent信息中...</p>
                </div>
            `;

            // 请求Agent信息
            const response = await fetch('/api/agents');
            if (response.ok) {
                const agents = await response.json();
                this.displayAgentInfo(agents);
            } else {
                throw new Error('Failed to load agent info');
            }
        } catch (error) {
            console.error('Error loading agent info:', error);
            content.innerHTML = `
                <div class="loading-placeholder">
                    <p>加载失败，请重试</p>
                </div>
            `;
        }
    }

    // 显示Agent信息
    displayAgentInfo(agents) {
        const content = document.getElementById('agentInfoContent');
        if (!content) return;

        if (!agents || agents.length === 0) {
            content.innerHTML = `
                <div class="loading-placeholder">
                    <p>暂无Agent信息</p>
                </div>
            `;
            return;
        }

        const agentList = document.createElement('div');
        agentList.className = 'agent-list';

        agents.forEach(agent => {
            const agentItem = this.createAgentInfoItem(agent);
            agentList.appendChild(agentItem);
        });

        content.innerHTML = '';
        content.appendChild(agentList);
    }

    // 创建Agent信息项
    createAgentInfoItem(agent) {
        const item = document.createElement('div');
        item.className = 'agent-item';

        const avatarText = agent.name.charAt(0).toUpperCase();
        const status = agent.status === 'online' ? 'online' : 'offline';

        item.innerHTML = `
            <div class="agent-item-header">
                <div class="agent-item-avatar">${avatarText}</div>
                <div class="agent-item-info">
                    <div class="agent-item-name">${agent.name}</div>
                    <div class="agent-item-role">${agent.role || '助手'}</div>
                    <div class="agent-item-model">${agent.model}</div>
                </div>
                <div class="agent-item-status">
                    <span class="status-indicator ${status}"></span>
                    <span>${status === 'online' ? '在线' : '离线'}</span>
                </div>
            </div>
            <div class="agent-item-actions">
                <button class="agent-action-btn edit" onclick="editAgent('${agent.id}')">编辑</button>
                <button class="agent-action-btn remove" onclick="removeAgent('${agent.id}')">删除</button>
            </div>
        `;

        return item;
    }

    // 隐藏Agent信息模态框 - 使用模态框管理器
    hideAgentInfoModal() {
        console.log('🔒 隐藏Agent信息模态框');
        
        // 首选方法：使用模态框管理器
        if (this.modalManager) {
            console.log('✅ 使用模态框管理器隐藏Agent信息模态框');
            this.modalManager.hideModal('agentInfoModal');
            return;
        }
        
        // 备选方法：使用ChatManager的方法
        if (window.chatManager && window.chatManager.hideAgentInfoModal) {
            console.log('✅ 使用ChatManager.hideAgentInfoModal');
            window.chatManager.hideAgentInfoModal();
            return;
        }
        
        // 最后的回退方案：直接隐藏模态框
        console.warn('⚠️ 使用回退方法隐藏Agent信息模态框');
        const modal = document.getElementById('agentInfoModal');
        if (modal) {
            modal.classList.remove('show');
            modal.style.display = 'none';
        }
    }

    // 显示更多选项下拉菜单 - 委托给ChatManager
    showMoreOptionsDropdown(event) {
        console.log('⚠️ App.showMoreOptionsDropdown is deprecated, use ChatManager methods instead');
        
        if (window.chatManager) {
            // 尝试使用ChatManager的方法
            if (typeof window.chatManager.showMoreOptionsMenu === 'function') {
                window.chatManager.showMoreOptionsMenu(event);
                return;
            }
        }
        
        // 回退方案：直接显示下拉菜单
        console.log('⚠️ Using fallback method to show more options dropdown');
        event.stopPropagation();
        
        const dropdown = document.getElementById('moreOptionsDropdown');
        const menu = document.getElementById('moreOptionsMenu');
        
        if (!dropdown || !menu) {
            console.error('❌ Dropdown elements not found');
            return;
        }

        // 生成菜单选项
        menu.innerHTML = `
            <div class="dropdown-item" data-action="exportChatHistory">
                <span class="dropdown-item-icon">📄</span>
                <span class="dropdown-item-text">导出聊天记录</span>
            </div>
            <div class="dropdown-item" data-action="clearChatHistory">
                <span class="dropdown-item-icon">🗑️</span>
                <span class="dropdown-item-text">清空聊天记录</span>
            </div>
            <div class="dropdown-item" data-action="shareChatRoom">
                <span class="dropdown-item-icon">🔗</span>
                <span class="dropdown-item-text">分享聊天室</span>
            </div>
            <div class="dropdown-item danger" data-action="deleteChatRoom">
                <span class="dropdown-item-icon">❌</span>
                <span class="dropdown-item-text">删除聊天室</span>
            </div>
        `;

        // 绑定点击事件
        menu.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                this.handleMoreOptionAction(action);
                this.hideMoreOptionsDropdown();
            });
        });

        // 计算位置
        const button = event.target;
        const rect = button.getBoundingClientRect();
        
        menu.style.position = 'fixed';
        menu.style.top = `${rect.bottom + 5}px`;
        menu.style.right = `${window.innerWidth - rect.right}px`;

        // 显示下拉菜单
        dropdown.style.display = 'block';

        // 点击外部关闭
        setTimeout(() => {
            document.addEventListener('click', this.hideMoreOptionsDropdown.bind(this), { once: true });
        }, 100);
    }
    
    // 处理更多选项动作
    handleMoreOptionAction(action) {
        console.log(`🎯 App handling action: ${action}`);
        
        switch (action) {
            case 'exportChatHistory':
                this.exportChatHistory();
                break;
            case 'clearChatHistory':
                this.clearChatHistory();
                break;
            case 'shareChatRoom':
                this.shareChatRoom();
                break;
            case 'deleteChatRoom':
                this.deleteChatRoom();
                break;
            default:
                console.warn('Unknown action:', action);
        }
    }

    // 导出聊天记录
    exportChatHistory() {
        this.hideMoreOptionsDropdown();
        showNotification('导出功能开发中...', 'info');
    }

    // 清空聊天记录
    clearChatHistory() {
        this.hideMoreOptionsDropdown();
        if (confirm('确定要清空所有聊天记录吗？此操作不可撤销。')) {
            showNotification('清空功能开发中...', 'info');
        }
    }

    // 分享聊天室
    shareChatRoom() {
        this.hideMoreOptionsDropdown();
        showNotification('分享功能开发中...', 'info');
    }

    // 删除聊天室
    deleteChatRoom() {
        this.hideMoreOptionsDropdown();
        if (confirm('确定要删除当前聊天室吗？此操作不可撤销。')) {
            showNotification('删除功能开发中...', 'info');
        }
    }

    // 隐藏更多选项下拉菜单
    hideMoreOptionsDropdown() {
        const dropdown = document.getElementById('moreOptionsDropdown');
        if (dropdown) {
            dropdown.classList.remove('show');
            dropdown.style.display = 'none';
        }
    }

    // 获取应用程序状态
    getAppState() {
        return {
            initialized: this.initialized,
            currentRoomId: this.chatManager?.currentRoomId,
            roomsCount: this.chatManager?.rooms.length || 0,
            wsConnected: this.wsManager?.isConnected() || false
        };
    }
}

// 全局函数
window.editAgent = function(agentId) {
    console.log('Edit agent:', agentId);
    showNotification('编辑功能开发中...', 'info');
};

window.removeAgent = function(agentId) {
    if (confirm('确定要删除这个Agent吗？')) {
        console.log('Remove agent:', agentId);
        showNotification('删除功能开发中...', 'info');
    }
};

// 应用程序实例
let app;

// DOM加载完成后初始化应用程序
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM Content Loaded');
    
    app = new MultiAIApp();
    window.app = app;
    
    await app.initialize();
});

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    if (app && app.wsManager) {
        app.wsManager.close();
    }
});

// 全局错误处理
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    // 可以选择显示错误通知或发送错误报告
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    // 可以选择显示错误通知或发送错误报告
});

// 导出主应用类
window.MultiAIApp = MultiAIApp;
