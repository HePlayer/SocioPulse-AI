// 聊天室操作管理器
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
            
            // 获取当前配置的默认平台和模型
            const settings = window.settingsManager?.getSettings();
            let defaultPlatform = 'zhipu';
            let defaultModel = 'glm-4-flash-250414';
            
            if (settings && settings.models) {
                defaultPlatform = settings.models.default_platform || 'zhipu';
                const platformConfig = settings.models.platforms[defaultPlatform];
                if (platformConfig) {
                    defaultModel = platformConfig.default_model || 'glm-4-flash-250414';
                }
            }
            
            // 获取平台显示名称
            const platformDisplayNames = {
                'openai': 'OpenAI',
                'aihubmix': 'AiHubMix', 
                'zhipu': '智谱AI',
                'zhipuai': '智谱AI'
            };
            const platformDisplayName = platformDisplayNames[defaultPlatform] || defaultPlatform.toUpperCase();
            
            return {
                success: true,
                agents: [
                    {
                        id: 'agent_1',
                        name: '智能助手1',
                        role: '通用助手',
                        model: defaultModel,
                        platform: defaultPlatform,
                        platform_display: platformDisplayName,
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
        
        if (!modal || !content) {
            console.error('❌ Agent info modal elements not found');
            return;
        }
        
        console.log('👤 Displaying agent info modal...');
        
        // 使用ModalManager显示模态框（如果可用）
        if (window.modalManager && window.modalManager.showModal) {
            console.log('✅ Using ModalManager to show agent info modal');
            window.modalManager.showModal('agentInfoModal');
        } else {
            // 回退方案：直接显示模态框
            console.log('⚠️ Using fallback method to show agent info modal');
            modal.style.display = 'flex';
            modal.style.visibility = 'visible';
            modal.style.opacity = '1';
            modal.classList.add('show');
            modal.classList.remove('hidden');
        }
        
        // 渲染Agent信息
        this.renderAgentInfo(content, agentData);
        
        // 绑定模态框事件
        this.bindAgentInfoEvents();
        
        console.log('✅ Agent info modal displayed successfully');
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
            // 关闭按钮 - 使用简单直接的方法绑定事件
            const closeBtn1 = document.getElementById('closeAgentInfoModal');
            const closeBtn2 = document.getElementById('closeAgentInfoBtn');
            const addBtn = document.getElementById('addNewAgentBtn');
            
            // 直接绑定事件，不使用复杂的DOM操作
            if (closeBtn1) {
                closeBtn1.onclick = () => {
                    console.log('❌ Close agent info modal (button 1)');
                    this.hideAgentInfoModal();
                };
                console.log('✅ Close button 1 bound');
            }
            
            if (closeBtn2) {
                closeBtn2.onclick = () => {
                    console.log('❌ Close agent info modal (button 2)');
                    this.hideAgentInfoModal();
                };
                console.log('✅ Close button 2 bound');
            }
            
            if (addBtn) {
                addBtn.onclick = () => {
                    console.log('➕ Add new agent button clicked');
                    this.addNewAgent();
                };
                console.log('✅ Add agent button bound');
            }
            
            // Agent操作按钮 - 使用事件委托
            const agentContainer = document.getElementById('agentInfoContent');
            if (agentContainer) {
                agentContainer.onclick = (e) => {
                    if (e.target.classList.contains('agent-action-btn')) {
                        const action = e.target.dataset.action;
                        const agentId = e.target.dataset.agentId;
                        console.log(`🎯 Agent action: ${action} for agent: ${agentId}`);
                        this.handleAgentAction(action, agentId);
                    }
                };
                console.log('✅ Agent action buttons bound via delegation');
            }
            
            // 点击外部关闭 - 简化版
            const modal = document.getElementById('agentInfoModal');
            if (modal) {
                modal.onclick = (e) => {
                    if (e.target === modal) {
                        console.log('❌ Close agent info modal (modal click)');
                        this.hideAgentInfoModal();
                    }
                };
                console.log('✅ Modal outside click bound');
            }
            
            console.log('✅ Agent Info Modal events bound successfully');
        } catch (error) {
            console.error('❌ Error binding agent info events:', error);
        }
    }
    
    hideAgentInfoModal() {
        console.log('❌ Hiding agent info modal...');
        
        try {
            // 使用ModalManager隐藏模态框（如果可用）
            if (window.modalManager && window.modalManager.hideModal) {
                console.log('✅ Using ModalManager to hide agent info modal');
                window.modalManager.hideModal('agentInfoModal');
                return;
            }
            
            // 回退方案：直接隐藏模态框
            const modal = document.getElementById('agentInfoModal');
            if (!modal) {
                console.warn('⚠️ Agent info modal not found for hiding');
                return;
            }
            
            console.log('⚠️ Using fallback method to hide agent info modal');
            
            // 使用标准的隐藏方法，不破坏DOM结构
            modal.classList.remove('show');
            modal.classList.add('hidden');
            modal.style.display = 'none';
            modal.style.visibility = 'hidden';
            modal.style.opacity = '0';
            
            // 恢复body滚动
            document.body.style.overflow = 'auto';
            document.body.style.paddingRight = '0';
            
            console.log('✅ Agent info modal hidden successfully');
            
        } catch (error) {
            console.error('❌ Error in hideAgentInfoModal:', error);
            
            // 简单的错误恢复
            try {
                const modal = document.getElementById('agentInfoModal');
                if (modal) {
                    modal.style.display = 'none';
                }
                document.body.style.overflow = 'auto';
                console.log('✅ Emergency modal hide completed');
            } catch (recoveryError) {
                console.error('❌ Emergency recovery failed:', recoveryError);
            }
        }
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
        
        if (!dropdown || !menu) {
            console.error('❌ More options dropdown elements not found');
            return;
        }
        
        console.log('⋮ Displaying more options menu...');
        
        // 计算菜单位置
        const rect = event.target.getBoundingClientRect();
        
        // 设置菜单位置 - 确保正确显示
        menu.style.position = 'fixed';
        menu.style.top = `${rect.bottom + 5}px`;
        menu.style.right = `${window.innerWidth - rect.right}px`;
        menu.style.zIndex = '9999';
        
        // 渲染菜单项
        this.renderMoreOptionsMenu(menu);
        
        // 显示下拉菜单
        dropdown.style.display = 'block';
        dropdown.style.visibility = 'visible';
        dropdown.style.opacity = '1';
        dropdown.classList.add('show');
        dropdown.classList.remove('hidden');
        
        console.log('✅ More options menu displayed');
        
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
        console.log('❌ Hiding more options menu...');
        
        const dropdown = document.getElementById('moreOptionsDropdown');
        if (dropdown) {
            dropdown.classList.remove('show');
            dropdown.classList.add('hidden');
            dropdown.style.display = 'none';
            dropdown.style.visibility = 'hidden';
            dropdown.style.opacity = '0';
            console.log('✅ More options menu hidden');
        } else {
            console.warn('⚠️ More options dropdown not found for hiding');
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

// 全局导出
window.ChatRoomActionManager = ChatRoomActionManager;
