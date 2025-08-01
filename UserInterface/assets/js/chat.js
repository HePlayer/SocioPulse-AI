// 聊天管理模块

// 消息去重器类
class MessageDeduplicator {
    constructor() {
        this.processedMessageIds = new Set();
        this.lastMessageContent = null;
        this.lastMessageTimestamp = null;
    }
    
    // 重置去重器状态
    reset() {
        this.processedMessageIds.clear();
        this.lastMessageContent = null;
        this.lastMessageTimestamp = null;
    }
    
    // 检查消息是否应该显示
    shouldDisplayMessage(messageData) {
        // 如果是本地消息，始终显示
        if (messageData.is_local) {
            return true;
        }
        
        // 如果有消息ID，检查是否已处理过
        if (messageData.message_id) {
            if (this.processedMessageIds.has(messageData.message_id)) {
                return false;
            }
            this.processedMessageIds.add(messageData.message_id);
        }
        
        // 检查内容和时间戳是否与上一条消息相同（防止重复）
        const content = messageData.content;
        const timestamp = messageData.timestamp;
        
        if (content === this.lastMessageContent && 
            timestamp === this.lastMessageTimestamp) {
            return false;
        }
        
        // 更新最后一条消息的内容和时间戳
        this.lastMessageContent = content;
        this.lastMessageTimestamp = timestamp;
        
        return true;
    }
}

// 聊天室操作管理器接口
class ChatRoomActionManager {
    constructor(roomId, chatManager) {
        this.roomId = roomId;
        this.chatManager = chatManager;
        this.agentInfoModal = null;
        this.moreOptionsMenu = null;
    }
    
    // Agent信息接口
    async showAgentInfo() {
        console.log('📋 Opening Agent Info for room:', this.roomId);
        try {
            const agentData = await this.loadAgentInfo();
            this.displayAgentInfoModal(agentData);
        } catch (error) {
            console.error('❌ Failed to load agent info:', error);
            showNotification('加载Agent信息失败', 'error');
        }
    }
    
    async loadAgentInfo() {
        // 从后端获取Agent信息
        try {
            console.log(`🔍 Fetching agent info for room: ${this.roomId}`);
            
            // 使用相对路径，避免跨域问题
            const response = await fetch(`/api/rooms/${this.roomId}/agents`);
            
            if (!response.ok) {
                console.error(`❌ API error: ${response.status} ${response.statusText}`);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('✅ Agent data received:', data);
            return data;
        } catch (error) {
            console.error('❌ Failed to load agent info:', error);
            
            // 返回模拟数据，但在控制台中显示警告
            console.warn('⚠️ Using mock agent data due to API error');
            
            // 显示更友好的错误通知
            showNotification('无法加载Agent信息，显示模拟数据', 'warning');
            
            return {
                success: true,
                agents: [
                    {
                        id: 'agent_1',
                        name: '智能助手1',
                        role: '通用助手',
                        model: 'gpt-4o-mini',
                        platform: 'aihubmix',
                        status: 'online',
                        prompt: '你是一个友好、有帮助的AI助手。'
                    }
                ]
            };
        }
    }
    
    displayAgentInfoModal(agentData) {
        const modal = document.getElementById('agentInfoModal');
        const content = document.getElementById('agentInfoContent');
        
        if (!modal || !content) return;
        
        // 显示模态框
        modal.classList.add('show');
        
        // 渲染Agent信息
        this.renderAgentInfo(content, agentData);
        
        // 绑定模态框事件
        this.bindAgentInfoEvents();
    }
    
    renderAgentInfo(container, agentData) {
        if (!agentData.success || !agentData.agents.length) {
            container.innerHTML = `
                <div class="loading-placeholder">
                    <p>暂无Agent信息</p>
                </div>
            `;
            return;
        }
        
        const agentsHtml = agentData.agents.map(agent => `
            <div class="agent-item" data-agent-id="${agent.id}">
                <div class="agent-item-header">
                    <div class="agent-item-avatar">${agent.name.charAt(0).toUpperCase()}</div>
                    <div class="agent-item-info">
                        <div class="agent-item-name">${agent.name}</div>
                        <div class="agent-item-role">${agent.role}</div>
                        <div class="agent-item-model">${agent.model}</div>
                    </div>
                    <div class="agent-item-status">
                        <span class="status-indicator ${agent.status === 'online' ? '' : 'offline'}"></span>
                        ${agent.status === 'online' ? '在线' : '离线'}
                    </div>
                </div>
                <div class="agent-item-actions">
                    <button class="agent-action-btn edit" data-action="edit" data-agent-id="${agent.id}">编辑</button>
                    <button class="agent-action-btn remove" data-action="remove" data-agent-id="${agent.id}">移除</button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = `
            <div class="agent-list">
                ${agentsHtml}
            </div>
        `;
    }
    
    bindAgentInfoEvents() {
        console.log('🔄 Binding Agent Info Modal events...');
        
        try {
            // 关闭按钮 - 使用直接的方法绑定事件
            const closeBtn1 = document.getElementById('closeAgentInfoModal');
            const closeBtn2 = document.getElementById('closeAgentInfoBtn');
            const addBtn = document.getElementById('addNewAgentBtn');
            
            // 清除所有现有的事件监听器
            if (closeBtn1) {
                const newCloseBtn1 = closeBtn1.cloneNode(true);
                closeBtn1.parentNode.replaceChild(newCloseBtn1, closeBtn1);
                
                // 使用多种方式绑定事件，确保至少一种方式生效
                newCloseBtn1.onclick = () => {
                    console.log('❌ Close agent info modal (button 1)');
                    this.hideAgentInfoModal();
                };
                
                console.log('✅ Close button 1 bound');
            }
            
            if (closeBtn2) {
                const newCloseBtn2 = closeBtn2.cloneNode(true);
                closeBtn2.parentNode.replaceChild(newCloseBtn2, closeBtn2);
                
                // 使用多种方式绑定事件，确保至少一种方式生效
                newCloseBtn2.onclick = () => {
                    console.log('❌ Close agent info modal (button 2)');
                    this.hideAgentInfoModal();
                };
                
                console.log('✅ Close button 2 bound');
            }
            
            if (addBtn) {
                const newAddBtn = addBtn.cloneNode(true);
                addBtn.parentNode.replaceChild(newAddBtn, addBtn);
                
                newAddBtn.onclick = () => {
                    console.log('➕ Add new agent button clicked');
                    this.addNewAgent();
                };
                
                console.log('✅ Add agent button bound');
            }
            
            // Agent操作按钮
            const actionBtns = document.querySelectorAll('.agent-action-btn');
            actionBtns.forEach(btn => {
                const newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);
                
                newBtn.onclick = (e) => {
                    const action = newBtn.dataset.action;
                    const agentId = newBtn.dataset.agentId;
                    console.log(`🎯 Agent action: ${action} for agent: ${agentId}`);
                    this.handleAgentAction(action, agentId);
                };
            });
            console.log(`✅ ${actionBtns.length} action buttons bound`);
            
            // 点击外部关闭 - 超级增强版
            const modal = document.getElementById('agentInfoModal');
            if (modal) {
                // 确保模态框有正确的类和样式
                modal.classList.add('modal-overlay');
                
                // 创建一个透明的覆盖层，专门用于捕获点击事件
                let overlay = document.getElementById('modal-click-overlay');
                if (!overlay) {
                    overlay = document.createElement('div');
                    overlay.id = 'modal-click-overlay';
                    overlay.style.position = 'fixed';
                    overlay.style.top = '0';
                    overlay.style.left = '0';
                    overlay.style.right = '0';
                    overlay.style.bottom = '0';
                    overlay.style.zIndex = '1999'; // 比模态框低1
                    overlay.style.background = 'transparent';
                    document.body.appendChild(overlay);
                }
                
                // 绑定覆盖层的点击事件
                overlay.onclick = (e) => {
                    console.log('❌ Close agent info modal (overlay click)');
                    this.hideAgentInfoModal();
                };
                
                // 同时也绑定模态框自身的点击事件
                modal.onclick = (e) => {
                    if (e.target === modal) {
                        console.log('❌ Close agent info modal (direct modal click)');
                        this.hideAgentInfoModal();
                        e.stopPropagation(); // 阻止事件冒泡
                    }
                };
                
                // 阻止模态框内容的点击事件冒泡
                const modalContent = modal.querySelector('.agent-info-modal');
                if (modalContent) {
                    modalContent.onclick = (e) => {
                        e.stopPropagation(); // 阻止事件冒泡
                    };
                }
                
                console.log('✅ Modal outside click bound (super enhanced)');
            }
            
            console.log('✅ Agent Info Modal events bound successfully');
        } catch (error) {
            console.error('❌ Error binding agent info events:', error);
        }
    }
    
    hideAgentInfoModal() {
        console.log('❌ Hiding agent info modal...');
        
        try {
            // 获取模态框元素
            const modal = document.getElementById('agentInfoModal');
            if (!modal) {
                console.warn('⚠️ Agent info modal not found for hiding');
                return;
            }
            
            // 使用最直接的方式：立即移除DOM元素
            if (modal.parentNode) {
                // 先尝试隐藏
                modal.style.display = 'none';
                modal.style.visibility = 'hidden';
                modal.style.opacity = '0';
                modal.classList.add('hidden');
                modal.classList.remove('show');
                
                // 然后强制移除
                setTimeout(() => {
                    try {
                        if (modal.parentNode) {
                            modal.parentNode.removeChild(modal);
                            console.log('💥 Modal forcibly removed from DOM');
                        }
                    } catch (e) {
                        console.error('❌ Error removing modal:', e);
                    }
                }, 10);
            }
            
            // 移除可能的覆盖层
            const overlay = document.getElementById('modal-click-overlay');
            if (overlay && overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
            
            // 移除所有可能的模态框和覆盖层
            document.querySelectorAll('.modal-overlay, .modal-backdrop, .modal-container')
                .forEach(el => {
                    if (el.id !== 'agentInfoModal' && el.parentNode) {
                        el.parentNode.removeChild(el);
                    }
                });
            
            // 恢复body滚动
            document.body.style.overflow = 'auto';
            document.body.style.paddingRight = '0';
            
            // 清除可能的全局事件监听器
            document.removeEventListener('click', this.hideAgentInfoModal);
            document.removeEventListener('keydown', this.handleEscapeKey);
            
            // 重置状态标记
            this.agentInfoModalVisible = false;
            
            console.log('✅ Agent info modal hidden successfully');
            
            // 重新创建模态框元素以备后用
            setTimeout(() => {
                if (this.ensureModalElements) {
                    this.ensureModalElements();
                    console.log('🔄 Modal element recreated');
                }
            }, 100);
            
        } catch (error) {
            console.error('❌ Error in hideAgentInfoModal:', error);
            
            // 强制恢复机制 - 超级核选项
            try {
                // 移除所有可能的模态框和覆盖层
                document.querySelectorAll('.modal, .modal-overlay, .dropdown-overlay, .backdrop, .overlay, [id*="modal" i], [class*="modal" i]')
                    .forEach(el => {
                        try {
                            if (el.parentNode) {
                                el.parentNode.removeChild(el);
                            }
                        } catch (e) {
                            console.error('❌ Error removing element:', e);
                        }
                    });
                
                // 恢复body样式
                document.body.style.overflow = 'auto';
                document.body.style.paddingRight = '0';
                
                console.log('💥 Emergency DOM cleanup completed');
                
                // 重新创建模态框元素以备后用
                setTimeout(() => {
                    if (this.ensureModalElements) {
                        this.ensureModalElements();
                        console.log('🔄 Modal element recreated after error');
                    }
                }, 100);
            } catch (recoveryError) {
                console.error('❌ Recovery failed:', recoveryError);
                alert('界面出现问题，请刷新页面');
            }
        }
        
        // 最后的保险：使用CSS隐藏所有可能的模态框
        const style = document.createElement('style');
        style.textContent = `
            #agentInfoModal, .modal-overlay, .modal-backdrop, .modal-container {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
                z-index: -9999 !important;
            }
        `;
        document.head.appendChild(style);
        setTimeout(() => style.remove(), 500);
    }
    
    async handleAgentAction(action, agentId) {
        console.log(`🎯 Agent action: ${action} for agent: ${agentId}`);
        
        switch (action) {
            case 'edit':
                await this.editAgent(agentId);
                break;
            case 'remove':
                await this.removeAgent(agentId);
                break;
            default:
                console.warn('Unknown agent action:', action);
        }
    }
    
    async editAgent(agentId) {
        showNotification('编辑Agent功能开发中...', 'info');
    }
    
    async removeAgent(agentId) {
        if (confirm('确定要移除这个Agent吗？')) {
            showNotification('移除Agent功能开发中...', 'info');
        }
    }
    
    async addNewAgent() {
        showNotification('添加Agent功能开发中...', 'info');
    }
    
    // 更多选项接口
    showMoreOptions(event) {
        console.log('⚙️ Opening More Options for room:', this.roomId);
        this.displayMoreOptionsMenu(event);
    }
    
    displayMoreOptionsMenu(event) {
        const dropdown = document.getElementById('moreOptionsDropdown');
        const menu = document.getElementById('moreOptionsMenu');
        
        if (!dropdown || !menu) return;
        
        // 计算菜单位置
        const rect = event.target.getBoundingClientRect();
        menu.style.top = `${rect.bottom + 5}px`;
        menu.style.right = `${window.innerWidth - rect.right}px`;
        
        // 渲染菜单项
        this.renderMoreOptionsMenu(menu);
        
        // 显示下拉菜单
        dropdown.classList.add('show');
        
        // 点击外部关闭
        setTimeout(() => {
            document.addEventListener('click', this.hideMoreOptionsMenu.bind(this), { once: true });
        }, 100);
    }
    
    renderMoreOptionsMenu(container) {
        const menuItems = [
            { icon: '👥', text: 'Agent信息', action: 'showAgentInfo' },
            { icon: '📊', text: '聊天室统计', action: 'showStatistics' },
            { icon: '⚙️', text: '聊天室设置', action: 'editRoomSettings' },
            { icon: '📤', text: '导出聊天记录', action: 'exportChatHistory' },
            { icon: '🗑️', text: '清空聊天历史', action: 'clearChatHistory' },
            { icon: '🗂️', text: '备份聊天数据', action: 'backupChatData' },
            { icon: '🗃️', text: '删除聊天室', action: 'deleteRoom', danger: true }
        ];
        
        container.innerHTML = menuItems.map(item => `
            <div class="dropdown-item ${item.danger ? 'danger' : ''}" data-action="${item.action}">
                <span class="dropdown-item-icon">${item.icon}</span>
                <span class="dropdown-item-text">${item.text}</span>
            </div>
        `).join('');
        
        // 绑定点击事件
        container.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                this.handleMoreOptionAction(action);
                this.hideMoreOptionsMenu();
            });
        });
    }
    
    hideMoreOptionsMenu() {
        const dropdown = document.getElementById('moreOptionsDropdown');
        if (dropdown) {
            dropdown.classList.remove('show');
        }
    }
    
    // 预留接口：处理更多选项动作
    async handleMoreOptionAction(action) {
        console.log(`🎯 Executing action: ${action} for room: ${this.roomId}`);
        
        switch (action) {
            case 'showAgentInfo':
                await this.showAgentInfo();
                break;
            case 'showStatistics':
                await this.showRoomStatistics();
                break;
            case 'editRoomSettings':
                await this.editRoomSettings();
                break;
            case 'exportChatHistory':
                await this.exportChatHistory();
                break;
            case 'clearChatHistory':
                await this.clearChatHistory();
                break;
            case 'backupChatData':
                await this.backupChatData();
                break;
            case 'deleteRoom':
                await this.deleteRoom();
                break;
            default:
                console.warn('Unknown action:', action);
        }
    }
    
    // 预留接口实现
    async showRoomStatistics() {
        showNotification('聊天室统计功能开发中...', 'info');
    }
    
    async editRoomSettings() {
        showNotification('聊天室设置功能开发中...', 'info');
    }
    
    async exportChatHistory() {
        try {
            showNotification('正在导出聊天记录...', 'info');
            
            // 预留接口：从后端导出聊天记录
            const response = await fetch(`/api/rooms/${this.roomId}/export`);
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `chatroom_${this.roomId}_export_${new Date().toISOString().split('T')[0]}.json`;
                a.click();
                URL.revokeObjectURL(url);
                showNotification('聊天记录导出成功！', 'success');
            } else {
                throw new Error('导出失败');
            }
        } catch (error) {
            console.error('Export failed:', error);
            showNotification('导出聊天记录功能开发中...', 'info');
        }
    }
    
    async clearChatHistory() {
        if (confirm('确定要清空聊天历史吗？此操作不可撤销。')) {
            showNotification('清空聊天历史功能开发中...', 'info');
        }
    }
    
    async backupChatData() {
        showNotification('备份聊天数据功能开发中...', 'info');
    }
    
    async deleteRoom() {
        if (confirm('确定要删除这个聊天室吗？此操作不可撤销。')) {
            try {
                showNotification('正在删除聊天室...', 'info');
                
                // 发送删除房间请求
                const deleteData = {
                    type: 'delete_room',
                    room_id: this.roomId
                };
                
                if (window.wsManager && window.wsManager.send(deleteData)) {
                    console.log('✅ Delete room request sent successfully');
                } else {
                    throw new Error('发送删除请求失败');
                }
            } catch (error) {
                console.error('❌ Error deleting room:', error);
                showNotification('删除聊天室失败: ' + error.message, 'error');
            }
        }
    }
}

class ChatManager {
    constructor() {
        this.currentRoomId = null;
        this.rooms = [];
        this.messageDeduplicator = new MessageDeduplicator();
        this.messages = new Map(); // roomId -> messages[]
        this.lastMessageIds = new Map(); // roomId -> lastMessageId
    }

    // 初始化聊天管理器
    initialize() {
        this.bindEvents();
        this.setupWebSocketHandlers();
    }

    // 绑定事件
    bindEvents() {
        // 新建聊天按钮
        const addChatBtn = document.querySelector('.add-chat-btn');
        if (addChatBtn) {
            addChatBtn.addEventListener('click', () => this.showCreateRoomModal());
        }

        // 发送消息
        const sendBtn = document.querySelector('.send-btn');
        const messageInput = document.querySelector('.message-input');
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // 模态框事件
        this.bindModalEvents();
    }

    // 绑定模态框事件
    bindModalEvents() {
        // 创建聊天模态框
        const modal = document.getElementById('agentConfigModal');
        const closeBtn = document.getElementById('closeModal');
        const cancelBtn = document.getElementById('cancelBtn');
        const createBtn = document.getElementById('createRoomBtn');
        const addAgentBtn = document.getElementById('addAgentBtn');
        const chatTypeSelect = document.getElementById('chatTypeSelect');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideModal());
        }
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hideModal());
        }
        
        if (createBtn) {
            createBtn.addEventListener('click', () => this.createRoom());
        }
        
        if (addAgentBtn) {
            addAgentBtn.addEventListener('click', () => this.addAgentConfig());
        }
        
        if (chatTypeSelect) {
            chatTypeSelect.addEventListener('change', (e) => {
                this.updateAgentConfigVisibility(e.target.value);
            });
        }

        // 点击模态框外部关闭
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal();
                }
            });
        }
    }

    // 设置WebSocket处理器
    setupWebSocketHandlers() {
        if (window.wsManager) {
            window.wsManager.registerHandler('rooms_list', (data) => {
                this.updateRoomsList(data.rooms);
            });
            
            // 统一处理room_created消息，不区分大小写
            window.wsManager.registerHandler('room_created', (data) => {
                console.log('📣 Received room_created message:', data);
                this.onRoomCreated(data);
            });
            
            // 确保大写版本的ROOM_CREATED也能被处理
            window.wsManager.registerHandler('ROOM_CREATED', (data) => {
                console.log('📣 Received ROOM_CREATED message:', data);
                this.onRoomCreated(data);
            });
            
            window.wsManager.registerHandler('message', (data) => {
                this.onMessageReceived(data);
            });
            
            // 同时处理小写和大写版本的room_history消息类型
            window.wsManager.registerHandler('room_history', (data) => {
                this.loadRoomHistory(data);
            });
            
            window.wsManager.registerHandler('ROOM_HISTORY', (data) => {
                this.loadRoomHistory(data);
            });
            
            // 处理删除房间成功的消息
            window.wsManager.registerHandler('room_deleted', (data) => {
                this.onRoomDeleted(data);
            });
            
            window.wsManager.registerHandler('ROOM_DELETED', (data) => {
                this.onRoomDeleted(data);
            });
        }
    }

    // 显示创建房间模态框 - 使用模态框管理器
    showCreateRoomModal() {
        console.log('🏗️ 尝试显示创建聊天室模态框...');
        
        try {
            // 使用模态框管理器显示模态框
            if (window.modalManager && window.modalManager.showModal('agentConfigModal')) {
                console.log('✅ 使用模态框管理器显示创建聊天室模态框成功');
                
                // 重置表单并添加默认配置
                this.resetModalForm();
                this.addAgentConfig(); // 默认添加一个Agent配置
                
                return;
            }
            
            // 回退方案：直接显示模态框
            const modal = document.getElementById('agentConfigModal');
            if (!modal) {
                throw new Error('找不到创建聊天模态框元素');
            }
            
            // 确保模态框正确显示
            modal.style.display = 'flex';
            modal.style.visibility = 'visible';
            modal.style.opacity = '1';
            modal.classList.remove('hide');
            modal.classList.add('show');
            
            // 重置表单并添加默认配置
            this.resetModalForm();
            this.addAgentConfig();
            
            console.log('⚠️ 使用回退方法显示创建聊天室模态框');
            
        } catch (error) {
            console.error('❌ 显示创建聊天室模态框时出错:', error);
            showNotification('无法显示创建聊天对话框', 'error');
        }
    }

    // 隐藏模态框 - 使用模态框管理器
    hideModal() {
        console.log('❌ 隐藏创建聊天室模态框...');
        
        // 使用模态框管理器隐藏模态框
        if (window.modalManager) {
            window.modalManager.hideModal('agentConfigModal');
            console.log('✅ 使用模态框管理器隐藏创建聊天室模态框成功');
            return;
        }
        
        // 回退方案：直接隐藏模态框
        const modal = document.getElementById('agentConfigModal');
        if (modal) {
            modal.classList.remove('show');
            modal.style.display = 'none';
            console.log('⚠️ 使用回退方法隐藏创建聊天室模态框');
        } else {
            console.error('❌ 找不到创建聊天室模态框元素');
        }
    }

    // 重置模态框表单
    resetModalForm() {
        const roomNameInput = document.getElementById('roomNameInput');
        const chatTypeSelect = document.getElementById('chatTypeSelect');
        const agentsConfig = document.getElementById('agentsConfig');
        
        if (roomNameInput) roomNameInput.value = '';
        if (chatTypeSelect) chatTypeSelect.value = 'single';
        if (agentsConfig) agentsConfig.innerHTML = '';
        
        this.updateAgentConfigVisibility('single');
    }

    // 更新Agent配置可见性
    updateAgentConfigVisibility(chatType) {
        const addAgentBtn = document.getElementById('addAgentBtn');
        const agentsConfig = document.getElementById('agentsConfig');
        
        if (chatType === 'single') {
            if (addAgentBtn) addAgentBtn.style.display = 'none';
            // 确保只有一个Agent配置
            if (agentsConfig && agentsConfig.children.length > 1) {
                while (agentsConfig.children.length > 1) {
                    agentsConfig.removeChild(agentsConfig.lastChild);
                }
            }
        } else {
            if (addAgentBtn) addAgentBtn.style.display = 'block';
        }
    }

    // 添加Agent配置
    addAgentConfig() {
        const agentsConfig = document.getElementById('agentsConfig');
        const chatTypeSelect = document.getElementById('chatTypeSelect');
        
        if (!agentsConfig) return;
        
        const agentIndex = agentsConfig.children.length;
        const isGroupChat = chatTypeSelect?.value === 'group';
        
        const agentConfigItem = document.createElement('div');
        agentConfigItem.className = 'agent-config-item';
        agentConfigItem.innerHTML = `
            <div class="agent-header">
                <input type="text" class="agent-name" placeholder="Agent名称" value="Agent ${agentIndex + 1}">
                <input type="text" class="agent-role" placeholder="角色描述" value="${this.getDefaultRole(agentIndex)}">
                ${isGroupChat ? '<button type="button" class="remove-agent-btn">删除</button>' : ''}
            </div>
            <div class="agent-prompt">
                <label>系统提示词：</label>
                <textarea placeholder="输入Agent的系统提示词...">${this.getDefaultPrompt(agentIndex)}</textarea>
            </div>
            <div class="agent-model">
                <label>模型：</label>
                <select class="model-selector">
                    ${this.getModelOptions()}
                </select>
            </div>
        `;
        
        agentsConfig.appendChild(agentConfigItem);
        
        // 绑定删除按钮事件
        const removeBtn = agentConfigItem.querySelector('.remove-agent-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                agentsConfig.removeChild(agentConfigItem);
            });
        }
    }

    // 获取默认角色
    getDefaultRole(index) {
        const roles = ['助手', '专家', '顾问', '分析师', '创作者'];
        return roles[index % roles.length];
    }

    // 获取默认提示词
    getDefaultPrompt(index) {
        const prompts = [
            '你是一个有用的AI助手，请帮助用户解决问题。',
            '你是一个专业的技术专家，擅长解决技术问题。',
            '你是一个经验丰富的顾问，能够提供专业建议。',
            '你是一个数据分析师，擅长分析和解释数据。',
            '你是一个创意作者，善于创作和编写内容。'
        ];
        return prompts[index % prompts.length];
    }

    // 获取模型选项 - 严格版：只显示已配置API密钥的平台的模型
    getModelOptions() {
        const settings = window.settingsManager?.getSettings();
        if (!settings) {
            console.warn('⚠️ Settings not available, using default model option');
            return '<option value="gpt-4o-mini" data-platform="aihubmix">AiHubMix - GPT-4o Mini</option>';
        }
        
        const platforms = settings.models.platforms;
        const defaultPlatform = settings.models.default_platform || 'aihubmix';
        let options = '';
        
        console.log('🔧 Building model options (strict filtering)...');
        console.log('📋 Default platform:', defaultPlatform);
        console.log('🏢 Available platforms:', Object.keys(platforms));
        
        // 获取已配置API密钥的平台列表
        const configuredPlatforms = this.getConfiguredPlatforms(settings);
        console.log('🔑 Platforms with API keys:', configuredPlatforms);
        
        // 严格筛选：只显示已配置API密钥的平台的模型
        configuredPlatforms.forEach(platform => {
            const config = platforms[platform];
            const platformDisplayName = this.getPlatformDisplayName(platform);
            console.log(`✅ Adding models for platform: ${platformDisplayName}`);
            
            // 优先使用enabled_models，如果不存在则尝试使用available_models
            const enabledModels = config.enabled_models || config.available_models || [];
            
            if (enabledModels.length === 0) {
                console.warn(`⚠️ Platform ${platformDisplayName} has no enabled models`);
            }
            
            enabledModels.forEach(model => {
                const isDefaultModel = platform === defaultPlatform && model === config.default_model;
                const selected = isDefaultModel ? 'selected' : '';
                options += `<option value="${model}" data-platform="${platform}" ${selected}>${platformDisplayName} - ${model}</option>`;
                console.log(`  ➕ Added model: ${platformDisplayName} - ${model}`);
            });
        });
        
        // 如果没有任何模型，显示一个默认选项和警告
        if (!options) {
            options = '<option value="" data-platform="" disabled>请先在设置中配置API密钥</option>';
            console.warn('⚠️ No models found with configured API keys!');
        }
        
        return options;
    }
    
    // 获取平台显示名称
    getPlatformDisplayName(platform) {
        const displayNames = {
            'openai': 'OpenAI',
            'aihubmix': 'AiHubMix', 
            'zhipu': '智谱AI',
            'zhipuai': '智谱AI'
        };
        return displayNames[platform] || platform.toUpperCase();
    }

    // 创建房间 - 自动选择已配置API的平台模型
    createRoom() {
        console.log('🏗️ Creating new chat room with automatic platform selection...');
        
        const roomName = document.getElementById('roomNameInput')?.value.trim();
        const chatType = document.getElementById('chatTypeSelect')?.value;
        const agentsConfig = document.getElementById('agentsConfig');
        
        if (!roomName) {
            showNotification('请输入聊天室名称', 'warning');
            return;
        }
        
        if (!agentsConfig || agentsConfig.children.length === 0) {
            showNotification('请至少配置一个Agent', 'warning');
            return;
        }
        
        // 获取设置和已配置的平台
        const settings = window.settingsManager?.getSettings();
        if (!settings) {
            showNotification('无法获取设置信息，请刷新页面重试', 'error');
            return;
        }
        
        const configuredPlatforms = this.getConfiguredPlatforms(settings);
        console.log('✅ Configured platforms:', configuredPlatforms);
        
        if (configuredPlatforms.length === 0) {
            showNotification('请先在设置中配置至少一个平台的API密钥', 'error');
            return;
        }
        
        // 自动选择第一个已配置的平台和模型
        const defaultPlatform = configuredPlatforms[0];
        const platformConfig = settings.models.platforms[defaultPlatform];
        const defaultModel = platformConfig.default_model || platformConfig.enabled_models[0];
        
        console.log(`🔄 Auto-selecting platform: ${defaultPlatform}, model: ${defaultModel}`);
        
        // 收集Agent配置
        const agents = [];
        let hasInvalidConfig = false;
        
        Array.from(agentsConfig.children).forEach((item, index) => {
            const name = item.querySelector('.agent-name')?.value.trim();
            const role = item.querySelector('.agent-role')?.value.trim();
            const prompt = item.querySelector('textarea')?.value.trim();
            
            // 使用自动选择的平台和模型
            const platform = defaultPlatform;
            const model = defaultModel;
            
            console.log(`🔍 Configuring Agent ${index + 1}:`, { name, role, model, platform });
            
            // 验证必填字段
            if (!name || !prompt) {
                showNotification(`请完善Agent ${index + 1} 的配置信息`, 'warning');
                hasInvalidConfig = true;
                return;
            }
            
            // 添加到agents数组
            agents.push({
                name,
                role: role || '助手',
                prompt,
                model,
                platform
            });
            
            console.log(`✅ Agent ${index + 1} configuration completed`);
        });
        
        // 检查验证结果
        if (hasInvalidConfig) {
            return;
        }
        
        if (agents.length === 0) {
            showNotification('请完善Agent配置信息', 'warning');
            return;
        }
        
        console.log('✅ All agents configured successfully:', agents);
        
        // 发送创建房间请求
        const createData = {
            type: 'create_room',
            room_name: roomName,
            chat_type: chatType,
            agents: agents
        };
        
        console.log('📤 Sending create room request:', createData);
        
        if (window.wsManager && window.wsManager.send(createData)) {
            this.hideModal();
            showNotification('正在创建聊天室...', 'info');
            console.log('✅ Create room request sent successfully');
        } else {
            showNotification('创建失败，请检查网络连接', 'error');
            console.error('❌ Failed to send create room request');
        }
    }
    
    // 获取已配置API的平台列表
    getConfiguredPlatforms(settings) {
        const platforms = settings.models.platforms;
        console.log('🔍 Checking configured platforms with settings:', settings);
        
        // 检查是否有任何平台配置了API密钥
        const configuredPlatforms = Object.keys(platforms).filter(platform => {
            const config = platforms[platform];
            const isConfigured = config.api_key && config.api_key.trim() !== '';
            console.log(`🔍 Platform ${platform} API key configured: ${isConfigured}`);
            return isConfigured;
        });
        
        console.log('✅ Configured platforms:', configuredPlatforms);
        return configuredPlatforms;
    }

    // 房间创建成功回调 - 增强版
    onRoomCreated(data) {
        if (data.success) {
            showNotification(`聊天室 "${data.room_name}" 创建成功`, 'success');
            
            // 立即将新创建的聊天室添加到房间列表中
            if (data.room_id) {
                const newRoom = {
                    id: data.room_id,
                    room_id: data.room_id,
                    room_name: data.room_name,
                    agent_count: data.agents?.length || 1,
                    last_message: '暂无消息'
                };
                
                console.log('🏗️ 立即添加新创建的聊天室到列表:', newRoom);
                
                // 添加到本地房间列表
                this.rooms.push(newRoom);
                
                // 更新UI
                this.updateRoomsList(this.rooms);
                
                // 选择新创建的聊天室
                this.selectRoom(data.room_id);
            }
            
            // 同时也刷新房间列表，确保数据一致性
            setTimeout(() => {
                window.wsManager.send({ type: 'get_rooms' });
            }, 500); // 延迟500毫秒，确保服务器有时间处理
        } else {
            showNotification(`创建失败: ${data.message}`, 'error');
        }
    }

    // 更新房间列表
    updateRoomsList(rooms) {
        this.rooms = rooms;
        const chatItems = document.getElementById('chatItems');
        
        if (!chatItems) return;
        
        chatItems.innerHTML = '';
        
        rooms.forEach(room => {
            const chatItem = this.createChatItem(room);
            chatItems.appendChild(chatItem);
        });
        
        // 如果当前没有选中的房间，选择第一个
        if (!this.currentRoomId && rooms.length > 0) {
            this.selectRoom(rooms[0].id);
        }
    }

    // 创建聊天项
    createChatItem(room) {
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';
        chatItem.dataset.roomId = room.id;
        
        // 生成头像（使用房间名称的第一个字符）
        const roomName = room.room_name || room.name || '房间';
        const avatarText = roomName.charAt(0).toUpperCase();
        
        chatItem.innerHTML = `
            <div class="chat-avatar">${avatarText}</div>
            <div class="chat-info">
                <div class="chat-name">${roomName}</div>
                <div class="chat-preview">${room.last_message || '暂无消息'}</div>
            </div>
            ${room.unread_count > 0 ? '<div class="unread-indicator"></div>' : ''}
        `;
        
        // 绑定点击事件
        chatItem.addEventListener('click', () => {
            this.selectRoom(room.id);
        });
        
        return chatItem;
    }

    // 选择房间 - 修复版：添加join_room消息发送
    selectRoom(roomId) {
        console.log('🎯 选择房间:', roomId);

        // 更新UI状态
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });

        const selectedItem = document.querySelector(`[data-room-id="${roomId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }

        // 重置消息去重器
        this.messageDeduplicator.reset();

        this.currentRoomId = roomId;

        // 显示聊天区域
        this.showChatArea();

        // 🔧 CRITICAL FIX: 先发送join_room消息注册连接到房间
        console.log('📤 发送join_room消息:', roomId);
        const joinSuccess = window.wsManager.send({
            type: 'join_room',
            room_id: roomId
        });

        if (!joinSuccess) {
            console.error('❌ 发送join_room消息失败');
            showNotification('加入房间失败，请检查网络连接', 'error');
            return;
        }

        // 🔧 延迟发送历史消息请求，确保join_room先处理
        setTimeout(() => {
            console.log('📤 发送get_room_history消息:', roomId);
            const historySuccess = window.wsManager.send({
                type: 'get_room_history',
                room_id: roomId
            });

            if (!historySuccess) {
                console.error('❌ 发送get_room_history消息失败');
                showNotification('获取历史消息失败', 'warning');
            }
        }, 100); // 100ms延迟确保join_room先处理
    }

    // 显示聊天区域
    showChatArea() {
        const chatArea = document.getElementById('chatArea');
        const workspace = document.getElementById('workspace');
        
        if (chatArea) {
            chatArea.innerHTML = `
                <div class="chat-header">
                    <div class="chat-header-info">
                        <div class="chat-avatar">${this.getCurrentRoomName().charAt(0).toUpperCase()}</div>
                        <div>
                            <div class="chat-name">${this.getCurrentRoomName()}</div>
                            <div class="chat-status">在线</div>
                        </div>
                    </div>
                    <div class="chat-header-actions">
                        <button class="icon-btn" id="agentInfoBtn" title="Agent信息">👥</button>
                        <button class="icon-btn" id="moreOptionsBtn" title="更多选项">⋮</button>
                    </div>
                </div>
                <div class="messages-container" id="messagesContainer">
                    <!-- 消息将在这里显示 -->
                </div>
                <div class="input-container">
                    <div class="input-wrapper">
                        <textarea class="message-input" placeholder="输入消息..." rows="1"></textarea>
                        <button class="send-btn">➤</button>
                    </div>
                </div>
            `;
            
            // 创建操作管理器
            this.actionManager = new ChatRoomActionManager(this.currentRoomId, this);
            
            // 重新绑定事件
            this.bindChatAreaEvents();
        }
        
        if (workspace) {
            workspace.classList.remove('active');
        }
    }

    // 绑定聊天区域事件
    bindChatAreaEvents() {
        console.log('🔄 Binding chat area events...');
        
        const sendBtn = document.querySelector('.send-btn');
        const messageInput = document.querySelector('.message-input');
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
            console.log('✅ Send button event bound');
        } else {
            console.warn('⚠️ Send button not found');
        }
        
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // 自动调整输入框高度
            messageInput.addEventListener('input', () => {
                messageInput.style.height = 'auto';
                messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
            });
            
            console.log('✅ Message input events bound');
        } else {
            console.warn('⚠️ Message input not found');
        }
        
        // 立即绑定按钮事件，不使用延迟
        console.log('🔄 Binding header buttons immediately...');
        this.bindHeaderButtons();
        
        // 额外检查：直接获取按钮并添加事件
        console.log('🔍 Direct button check...');
        const agentInfoBtn = document.getElementById('agentInfoBtn');
        const moreOptionsBtn = document.getElementById('moreOptionsBtn');
        
        if (agentInfoBtn) {
            console.log('✅ Agent info button found directly');
            agentInfoBtn.onclick = (e) => {
                console.log('👤 Agent info button clicked directly');
                e.preventDefault();
                e.stopPropagation();
                this.showAgentInfoModal();
            };
        } else {
            console.warn('⚠️ Agent info button not found directly');
        }
        
        if (moreOptionsBtn) {
            console.log('✅ More options button found directly');
            moreOptionsBtn.onclick = (e) => {
                console.log('⋮ More options button clicked directly');
                e.preventDefault();
                e.stopPropagation();
                this.showMoreOptionsMenu(e);
            };
        } else {
            console.warn('⚠️ More options button not found directly');
        }
    }

    // 绑定头部按钮事件 - 简化版
    bindHeaderButtons() {
        // 获取按钮元素
        const agentInfoBtn = document.getElementById('agentInfoBtn');
        const moreOptionsBtn = document.getElementById('moreOptionsBtn');
        
        console.log('🔄 Binding header buttons...', { 
            agentInfoBtn: agentInfoBtn ? 'Found' : 'Not found', 
            moreOptionsBtn: moreOptionsBtn ? 'Found' : 'Not found'
        });
        
        // 确保模态框和下拉菜单元素存在
        this.ensureModalElements();
        
        // 移除所有现有的事件监听器并重新创建按钮
        if (agentInfoBtn) {
            const newAgentInfoBtn = agentInfoBtn.cloneNode(true);
            agentInfoBtn.parentNode.replaceChild(newAgentInfoBtn, agentInfoBtn);
            
            // 只绑定一次点击事件
            newAgentInfoBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('👤 Agent info button clicked');
                
                try {
                    if (this.actionManager) {
                        this.actionManager.showAgentInfo();
                    } else {
                        showNotification('Agent信息功能暂时不可用', 'warning');
                    }
                } catch (error) {
                    console.error('❌ Error showing agent info:', error);
                    showNotification('打开Agent信息失败', 'error');
                }
            });
            
            console.log('✅ Agent info button event bound successfully');
        }
        
        // 更多选项按钮事件
        if (moreOptionsBtn) {
            const newMoreOptionsBtn = moreOptionsBtn.cloneNode(true);
            moreOptionsBtn.parentNode.replaceChild(newMoreOptionsBtn, moreOptionsBtn);
            
            // 只绑定一次点击事件
            newMoreOptionsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('⋮ More options button clicked');
                
                try {
                    if (this.actionManager) {
                        // 直接显示下拉菜单，不依赖于actionManager
                        this.showMoreOptionsMenu(e);
                    } else {
                        showNotification('更多选项功能暂时不可用', 'warning');
                    }
                } catch (error) {
                    console.error('❌ Error showing more options:', error);
                    showNotification('打开更多选项失败', 'error');
                }
            });
            
            console.log('✅ More options button event bound successfully');
        }
    }
    
    // 清除元素上的所有事件监听器
    clearEventListeners(element) {
        if (!element) return;
        
        // 克隆并替换元素，移除所有事件监听器
        const newElement = element.cloneNode(true);
        if (element.parentNode) {
            element.parentNode.replaceChild(newElement, element);
        }
        
        return newElement;
    }
    
    // 显示Agent信息模态框 - 使用模态框管理器
    showAgentInfoModal() {
        console.log('📋 显示Agent信息模态框');
        
        try {
            // 使用模态框管理器显示模态框
            if (window.modalManager && window.modalManager.showModal('agentInfoModal')) {
                console.log('✅ 使用模态框管理器显示Agent信息模态框成功');
                
                // 如果有actionManager，尝试加载Agent信息
                if (this.actionManager) {
                    this.actionManager.loadAgentInfo().then(data => {
                        const content = document.getElementById('agentInfoContent');
                        if (content && data) {
                            this.actionManager.renderAgentInfo(content, data);
                        }
                    });
                }
                
                return;
            }
            
            // 回退方案：直接显示模态框
            const modal = document.getElementById('agentInfoModal');
            if (!modal) {
                // 确保模态框元素存在
                this.ensureModalElements();
                const newModal = document.getElementById('agentInfoModal');
                if (!newModal) {
                    throw new Error('找不到Agent信息模态框元素');
                }
                
                // 显示模态框
                newModal.style.display = 'flex';
                newModal.style.visibility = 'visible';
                newModal.style.opacity = '1';
                newModal.classList.add('show');
                
                console.log('⚠️ 使用回退方法显示Agent信息模态框');
                
                // 如果有actionManager，尝试加载Agent信息
                if (this.actionManager) {
                    this.actionManager.loadAgentInfo().then(data => {
                        const content = document.getElementById('agentInfoContent');
                        if (content && data) {
                            this.actionManager.renderAgentInfo(content, data);
                        }
                    });
                }
            }
        } catch (error) {
            console.error('❌ 显示Agent信息模态框时出错:', error);
            showNotification('无法显示Agent信息', 'error');
        }
    }
    
    // 确保模态框和下拉菜单元素存在
    ensureModalElements() {
        // 检查并创建Agent信息模态框
        let agentInfoModal = document.getElementById('agentInfoModal');
        if (!agentInfoModal) {
            console.log('⚠️ Creating missing agentInfoModal element');
            agentInfoModal = document.createElement('div');
            agentInfoModal.id = 'agentInfoModal';
            agentInfoModal.className = 'modal-overlay';
            agentInfoModal.style.display = 'none';
            agentInfoModal.innerHTML = `
                <div class="agent-info-modal">
                    <div class="modal-header">
                        <h3>Agent信息管理</h3>
                        <button class="close-btn" id="closeAgentInfoModal">×</button>
                    </div>
                    <div class="modal-body" id="agentInfoContent">
                        <div class="loading-placeholder">
                            <div class="loading-spinner"></div>
                            <p>加载Agent信息中...</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="action-btn" id="addNewAgentBtn">添加Agent</button>
                        <button class="cancel-btn" id="closeAgentInfoBtn">关闭</button>
                    </div>
                </div>
            `;
            document.body.appendChild(agentInfoModal);
            
            // 绑定关闭按钮事件
            const closeBtn1 = document.getElementById('closeAgentInfoModal');
            const closeBtn2 = document.getElementById('closeAgentInfoBtn');
            
            if (closeBtn1) {
                closeBtn1.addEventListener('click', () => this.hideAgentInfoModal());
            }
            
            if (closeBtn2) {
                closeBtn2.addEventListener('click', () => this.hideAgentInfoModal());
            }
            
            // 点击外部关闭
            agentInfoModal.addEventListener('click', (e) => {
                if (e.target === agentInfoModal) {
                    this.hideAgentInfoModal();
                }
            });
        }
        
        // 检查并创建更多选项下拉菜单
        let moreOptionsDropdown = document.getElementById('moreOptionsDropdown');
        if (!moreOptionsDropdown) {
            console.log('⚠️ Creating missing moreOptionsDropdown element');
            moreOptionsDropdown = document.createElement('div');
            moreOptionsDropdown.id = 'moreOptionsDropdown';
            moreOptionsDropdown.className = 'dropdown-overlay';
            moreOptionsDropdown.style.display = 'none';
            moreOptionsDropdown.innerHTML = `
                <div class="dropdown-menu" id="moreOptionsMenu">
                    <!-- 更多选项菜单项将动态生成 -->
                </div>
            `;
            document.body.appendChild(moreOptionsDropdown);
        }
    }
    
    // 显示更多选项菜单 - 简化版
    showMoreOptionsMenu(event) {
        console.log('📋 显示更多选项菜单');
        
        try {
            // 先移除可能存在的全局点击事件处理器
            document.removeEventListener('click', this.documentClickHandler);
            
            // 确保下拉菜单元素存在
            this.ensureModalElements();
            
            // 获取或创建下拉菜单元素
            let dropdown = document.getElementById('moreOptionsDropdown');
            if (!dropdown) {
                dropdown = document.createElement('div');
                dropdown.id = 'moreOptionsDropdown';
                dropdown.className = 'dropdown-overlay';
                dropdown.style.display = 'none';
                
                const menu = document.createElement('div');
                menu.id = 'moreOptionsMenu';
                menu.className = 'dropdown-menu';
                dropdown.appendChild(menu);
                
                document.body.appendChild(dropdown);
            }
            
            // 获取菜单内容元素
            const menu = document.getElementById('moreOptionsMenu');
            if (!menu) {
                throw new Error('找不到更多选项菜单内容元素');
            }
            
            // 计算菜单位置
            const rect = event.target.getBoundingClientRect();
            menu.style.position = 'fixed';
            menu.style.top = `${rect.bottom + 5}px`;
            menu.style.right = `${window.innerWidth - rect.right}px`;
            
            // 渲染菜单项
            this.renderMoreOptionsMenu(menu);
            
            // 显示下拉菜单
            dropdown.style.display = 'block';
            dropdown.classList.add('show');
            
            // 创建一次性点击外部关闭事件处理器
            this.documentClickHandler = (e) => {
                if (!menu.contains(e.target) && e.target.id !== 'moreOptionsBtn') {
                    this.hideMoreOptionsMenu();
                }
            };
            
            // 延迟添加事件监听器，避免立即触发
            setTimeout(() => {
                document.addEventListener('click', this.documentClickHandler);
            }, 100);
            
            console.log('✅ 更多选项菜单显示成功');
        } catch (error) {
            console.error('❌ 显示更多选项菜单时出错:', error);
            showNotification('无法显示更多选项菜单', 'error');
        }
    }
    
    // 渲染更多选项菜单
    renderMoreOptionsMenu(container) {
        const menuItems = [
            { icon: '👥', text: 'Agent信息', action: 'showAgentInfo' },
            { icon: '📊', text: '聊天室统计', action: 'showStatistics' },
            { icon: '⚙️', text: '聊天室设置', action: 'editRoomSettings' },
            { icon: '📤', text: '导出聊天记录', action: 'exportChatHistory' },
            { icon: '🗑️', text: '清空聊天历史', action: 'clearChatHistory' },
            { icon: '🗂️', text: '备份聊天数据', action: 'backupChatData' },
            { icon: '🗃️', text: '删除聊天室', action: 'deleteRoom', danger: true }
        ];
        
        container.innerHTML = menuItems.map(item => `
            <div class="dropdown-item ${item.danger ? 'danger' : ''}" data-action="${item.action}">
                <span class="dropdown-item-icon">${item.icon}</span>
                <span class="dropdown-item-text">${item.text}</span>
            </div>
        `).join('');
        
        // 绑定点击事件
        container.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                this.handleMoreOptionAction(action);
                this.hideMoreOptionsMenu();
            });
        });
    }
    
    // 隐藏更多选项菜单 - 简化版
    hideMoreOptionsMenu() {
        console.log('📋 隐藏更多选项菜单');
        
        try {
            // 移除全局点击事件处理器
            document.removeEventListener('click', this.documentClickHandler);
            
            // 获取下拉菜单元素
            const dropdown = document.getElementById('moreOptionsDropdown');
            if (dropdown) {
                // 隐藏下拉菜单而不是移除它
                dropdown.style.display = 'none';
                dropdown.classList.remove('show');
                console.log('✅ 更多选项菜单隐藏成功');
            } else {
                console.warn('⚠️ 找不到更多选项下拉菜单元素');
            }
        } catch (error) {
            console.error('❌ 隐藏更多选项菜单时出错:', error);
            
            // 简化的恢复机制
            try {
                const dropdowns = document.querySelectorAll('.dropdown-overlay');
                dropdowns.forEach(el => {
                    el.style.display = 'none';
                    el.classList.remove('show');
                });
            } catch (cleanupError) {
                console.error('❌ 恢复失败:', cleanupError);
            }
        }
    }
    
    // 隐藏Agent信息模态框 - 使用模态框管理器
    hideAgentInfoModal = () => {
        console.log('❌ 隐藏Agent信息模态框');
        
        // 使用模态框管理器隐藏模态框
        if (window.modalManager) {
            window.modalManager.hideModal('agentInfoModal');
            console.log('✅ 使用模态框管理器隐藏Agent信息模态框成功');
            return;
        }
        
        // 回退方案：直接隐藏模态框
        try {
            const modal = document.getElementById('agentInfoModal');
            if (modal) {
                modal.classList.remove('show');
                modal.style.display = 'none';
                console.log('⚠️ 使用回退方法隐藏Agent信息模态框');
            } else {
                console.warn('⚠️ 找不到Agent信息模态框元素');
            }
            
            // 移除可能的覆盖层
            const overlay = document.getElementById('modal-click-overlay');
            if (overlay && overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
            
            // 恢复body滚动
            document.body.style.overflow = 'auto';
            document.body.style.paddingRight = '0';
        } catch (error) {
            console.error('❌ 隐藏Agent信息模态框时出错:', error);
            
            // 紧急恢复机制
            try {
                document.querySelectorAll('.modal-overlay, .modal-backdrop, .modal-container')
                    .forEach(el => {
                        if (el.parentNode) {
                            el.parentNode.removeChild(el);
                        }
                    });
                
                document.body.style.overflow = 'auto';
                document.body.style.paddingRight = '0';
                
                console.log('💥 紧急DOM清理完成');
            } catch (recoveryError) {
                console.error('❌ 恢复失败:', recoveryError);
            }
        }
    }
    
    // 处理更多选项动作
    handleMoreOptionAction(action) {
        console.log(`🎯 Executing action: ${action} for room: ${this.currentRoomId}`);
        
        switch (action) {
            case 'showAgentInfo':
                if (this.actionManager) {
                    this.actionManager.showAgentInfo();
                } else {
                    showNotification('Agent信息功能暂时不可用', 'warning');
                }
                break;
            case 'showStatistics':
                showNotification('聊天室统计功能开发中...', 'info');
                break;
            case 'editRoomSettings':
                showNotification('聊天室设置功能开发中...', 'info');
                break;
            case 'exportChatHistory':
                showNotification('导出聊天记录功能开发中...', 'info');
                break;
            case 'clearChatHistory':
                if (confirm('确定要清空聊天历史吗？此操作不可撤销。')) {
                    showNotification('清空聊天历史功能开发中...', 'info');
                }
                break;
            case 'backupChatData':
                showNotification('备份聊天数据功能开发中...', 'info');
                break;
            case 'deleteRoom':
                this.deleteRoom();
                break;
            default:
                console.warn('Unknown action:', action);
        }
    }

    // 获取当前房间名称 - 统一使用room_name字段
    getCurrentRoomName() {
        const room = this.rooms.find(r => r.id === this.currentRoomId);
        return room ? (room.room_name || room.name || '未知房间') : '未知房间';
    }

    // 发送消息
    sendMessage() {
        const messageInput = document.querySelector('.message-input');
        if (!messageInput || !this.currentRoomId) return;
        
        const content = messageInput.value.trim();
        if (!content) return;
        
        // 发送消息到服务器
        const messageData = {
            type: 'send_message',
            room_id: this.currentRoomId,
            content: content
        };
        
        if (window.wsManager.send(messageData)) {
            // 清空输入框
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // 在本地UI中立即显示用户消息
            const userMessageData = {
                room_id: this.currentRoomId,
                sender: 'user',
                content: content,
                timestamp: new Date().toISOString(),
                message_id: `local_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
                is_local: true  // 标记为本地消息，避免去重
            };
            
            // 显示消息
            this.displayMessage(userMessageData);
            
            // 更新房间列表中的最后消息
            this.updateRoomLastMessage(this.currentRoomId, content);
            
            console.log('✅ User message sent and displayed locally:', content);
        }
    }

    // 消息接收回调
    onMessageReceived(data) {
        if (data.room_id === this.currentRoomId) {
            this.displayMessage(data);
        }
        
        // 更新房间列表中的最后消息
        this.updateRoomLastMessage(data.room_id, data.content);
    }

    // 加载房间历史消息
    loadRoomHistory(data) {
        if (data.room_id !== this.currentRoomId) return;
        
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer) return;
        
        messagesContainer.innerHTML = '';
        this.messageDeduplicator.reset();
        
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(message => {
                this.displayMessage(message, false);
            });
            
            // 滚动到底部
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    // 显示消息
    displayMessage(messageData, autoScroll = true) {
        // 使用去重系统检查
        if (!this.messageDeduplicator.shouldDisplayMessage(messageData)) {
            return;
        }
        
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer) return;
        
        const messageElement = this.createMessageElement(messageData);
        messagesContainer.appendChild(messageElement);
        
        if (autoScroll) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    // 创建消息元素
    createMessageElement(messageData) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${messageData.sender}`;
        
        const avatarText = messageData.sender === 'user' ? 'U' : 
                          (messageData.agent_name ? messageData.agent_name.charAt(0).toUpperCase() : 'A');
        
        const time = new Date(messageData.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatarText}</div>
            <div class="message-bubble">
                ${messageData.content}
                <div class="message-time">${time}</div>
            </div>
        `;
        
        return messageDiv;
    }

    // 更新房间最后消息
    updateRoomLastMessage(roomId, content) {
        const chatItem = document.querySelector(`[data-room-id="${roomId}"]`);
        if (chatItem) {
            const preview = chatItem.querySelector('.chat-preview');
            if (preview) {
                preview.textContent = content.length > 30 ? content.substring(0, 30) + '...' : content;
            }
        }
    }

    // 房间删除成功回调 - 智能房间选择逻辑
    onRoomDeleted(data) {
        if (data.success) {
            showNotification(`聊天室 "${data.room_name}" 已删除`, 'success');
            
            // 从本地房间列表中移除
            this.rooms = this.rooms.filter(room => room.id !== data.room_id);
            
            // 智能处理删除当前房间的情况
            if (this.currentRoomId === data.room_id) {
                this.currentRoomId = null;
                
                // 更新房间列表UI
                this.updateRoomsList(this.rooms);
                
                // 智能选择下一个房间
                if (this.rooms.length > 0) {
                    // 选择下一个可用的房间
                    const nextRoom = this.selectNextAvailableRoom(data.room_id);
                    if (nextRoom) {
                        this.selectRoom(nextRoom.id);
                        console.log('🎯 自动选择下一个房间:', nextRoom.room_name);
                    } else {
                        // 如果没有找到合适的房间，选择第一个
                        this.selectRoom(this.rooms[0].id);
                        console.log('🎯 选择第一个可用房间');
                    }
                } else {
                    // 没有房间了，显示初始欢迎页面
                    this.showInitialWelcome();
                    console.log('🏠 显示初始欢迎页面');
                }
            } else {
                // 删除的不是当前房间，只需要更新列表
                this.updateRoomsList(this.rooms);
            }
            
            console.log('✅ Room deleted successfully:', data.room_id);
        } else {
            showNotification(`删除失败: ${data.message}`, 'error');
        }
    }
    
    // 智能选择下一个可用房间
    selectNextAvailableRoom(deletedRoomId) {
        if (this.rooms.length === 0) return null;
        
        // 简单策略：选择第一个房间
        // 未来可以实现更智能的选择逻辑，比如：
        // - 选择最近活跃的房间
        // - 选择创建时间最新的房间
        // - 记住用户的房间切换历史
        return this.rooms[0];
    }
    
    // 显示初始欢迎页面（替代工作区）
    showInitialWelcome() {
        const chatArea = document.getElementById('chatArea');
        const workspace = document.getElementById('workspace');
        
        if (chatArea) {
            chatArea.innerHTML = `
                <div class="initial-welcome-container">
                    <div class="welcome-content">
                        <div class="welcome-icon">💬</div>
                        <h2>欢迎使用 SocioPulse AI</h2>
                        <p>您还没有创建任何聊天室</p>
                        <p>点击左侧的 "+" 按钮开始您的第一次对话</p>
                        <button class="welcome-create-btn" onclick="window.chatManager?.showCreateRoomModal()">
                            <span class="btn-icon">➕</span>
                            创建第一个聊天室
                        </button>
                    </div>
                </div>
            `;
        }
        
        // 隐藏工作区，显示欢迎页面
        if (workspace) {
            workspace.classList.remove('active');
        }
    }
    
    // 显示欢迎区域（当没有选中房间时）
    showWelcomeArea() {
        const chatArea = document.getElementById('chatArea');
        const workspace = document.getElementById('workspace');
        
        if (chatArea) {
            chatArea.innerHTML = '';
        }
        
        if (workspace) {
            workspace.classList.add('active');
        }
    }

    // 删除房间方法
    deleteRoom() {
        if (!this.currentRoomId) {
            showNotification('没有选中的聊天室', 'warning');
            return;
        }
        
        const roomName = this.getCurrentRoomName();
        
        if (confirm(`确定要删除聊天室 "${roomName}" 吗？此操作不可撤销。`)) {
            try {
                showNotification('正在删除聊天室...', 'info');
                
                // 发送删除房间请求
                const deleteData = {
                    type: 'delete_room',
                    room_id: this.currentRoomId
                };
                
                if (window.wsManager && window.wsManager.send(deleteData)) {
                    console.log('✅ Delete room request sent successfully');
                } else {
                    throw new Error('发送删除请求失败');
                }
            } catch (error) {
                console.error('❌ Error deleting room:', error);
                showNotification('删除聊天室失败: ' + error.message, 'error');
            }
        }
    }
}

// 全局导出
window.ChatManager = ChatManager;
