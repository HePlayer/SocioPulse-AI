// 聊天管理模块

class ChatManager {
    constructor() {
        this.currentRoomId = null;
        this.rooms = [];
        this.messages = new Map(); // roomId -> messages[]
        this.lastMessageIds = new Map(); // roomId -> lastMessageId
    }

    // 初始化聊天管理器
    initialize() {
        this.bindEvents();
        this.setupWebSocketHandlers();
        this.setupSettingsListener();
    }
    
    // 设置监听器
    setupSettingsListener() {
        // 监听设置变更事件
        window.addEventListener('settingsChanged', (event) => {
            console.log('🔔 Received settings change notification:', event.detail);
            this.onSettingsChanged(event.detail.settings);
        });
    }
    
    // 处理设置变更
    onSettingsChanged(newSettings) {
        console.log('⚙️ Processing settings change in ChatManager...');
        
        // 更新当前打开的Agent配置模态框中的模型选项
        this.updateAgentConfigModelOptions();
        
        console.log('✅ Settings change processed in ChatManager');
    }
    
    // 更新Agent配置中的模型选项
    updateAgentConfigModelOptions() {
        const agentsConfig = document.getElementById('agentsConfig');
        if (!agentsConfig) return;
        
        console.log('🔄 Updating model options in Agent config...');
        
        // 获取新的模型选项HTML
        const newModelOptions = this.getModelOptions();
        
        // 更新所有Agent配置项中的模型选择器
        const modelSelectors = agentsConfig.querySelectorAll('.model-selector');
        modelSelectors.forEach((selector, index) => {
            const currentValue = selector.value;
            const currentPlatform = selector.options[selector.selectedIndex]?.dataset?.platform;
            
            // 更新选项
            selector.innerHTML = newModelOptions;
            
            // 尝试保持之前的选择（如果该选项仍然可用）
            let optionFound = false;
            for (let i = 0; i < selector.options.length; i++) {
                const option = selector.options[i];
                if (option.value === currentValue && option.dataset.platform === currentPlatform) {
                    selector.selectedIndex = i;
                    optionFound = true;
                    break;
                }
            }
            
            // 如果之前的选择不再可用，选择第一个有效选项
            if (!optionFound && selector.options.length > 0) {
                const firstValidOption = Array.from(selector.options).find(opt => opt.value && opt.dataset.platform);
                if (firstValidOption) {
                    selector.value = firstValidOption.value;
                }
            }
            
            console.log(`✅ Updated model selector ${index + 1}`);
        });
        
        console.log('✅ All model selectors updated');
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
        
        // 确保Agent名字正确设置
        const agentNameInput = agentConfigItem.querySelector('.agent-name');
        if (agentNameInput) {
            agentNameInput.value = `Agent ${agentIndex + 1}`;
        }
        
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

    // 获取模型选项 - 简化版：移除收费信息显示
    getModelOptions() {
        const settings = window.settingsManager?.getSettings();
        if (!settings) {
            console.warn('⚠️ Settings not available, using default model option');
            return '<option value="gpt-4o-mini" data-platform="aihubmix">AiHubMix - GPT-4o Mini</option>';
        }
        
        const platforms = settings.models.platforms;
        const defaultPlatform = settings.models.default_platform || 'aihubmix';
        let options = '';
        
        console.log('🔧 Building model options...');
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
                
                // 简化显示：只显示平台和模型名称，不显示收费信息
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


    // 创建房间 - 使用用户选择的模型和平台
    createRoom() {
        console.log('🏗️ Creating new chat room with user-selected models...');
        
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
        
        // 收集Agent配置 - 读取用户实际选择
        const agents = [];
        let hasInvalidConfig = false;
        
        Array.from(agentsConfig.children).forEach((item, index) => {
            const name = item.querySelector('.agent-name')?.value.trim();
            const role = item.querySelector('.agent-role')?.value.trim();
            const prompt = item.querySelector('textarea')?.value.trim();
            
            // 从模型选择器获取用户选择的平台和模型
            const modelSelector = item.querySelector('.model-selector');
            if (!modelSelector || modelSelector.selectedIndex === -1) {
                showNotification(`请为Agent ${index + 1} 选择模型`, 'warning');
                hasInvalidConfig = true;
                return;
            }
            
            const selectedOption = modelSelector.options[modelSelector.selectedIndex];
            const model = selectedOption.value;
            const platform = selectedOption.dataset.platform;
            
            console.log(`🔍 Configuring Agent ${index + 1}:`, { name, role, model, platform });
            
            // 验证必填字段
            if (!name || !prompt) {
                showNotification(`请完善Agent ${index + 1} 的配置信息`, 'warning');
                hasInvalidConfig = true;
                return;
            }
            
            // 验证模型选择
            if (!model || !platform) {
                showNotification(`Agent ${index + 1} 的模型选择无效，请重新选择`, 'warning');
                hasInvalidConfig = true;
                return;
            }
            
            // 验证平台是否已配置API密钥
            if (!configuredPlatforms.includes(platform)) {
                const platformDisplayName = this.getPlatformDisplayName(platform);
                showNotification(`平台 ${platformDisplayName} 未配置API密钥，请先在设置中配置`, 'error');
                hasInvalidConfig = true;
                return;
            }
            
            // 验证模型是否在平台的可用模型列表中
            const platformConfig = settings.models.platforms[platform];
            const enabledModels = platformConfig.enabled_models || [];
            if (!enabledModels.includes(model)) {
                const platformDisplayName = this.getPlatformDisplayName(platform);
                showNotification(`模型 ${model} 在平台 ${platformDisplayName} 中不可用`, 'error');
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
        
        console.log('✅ All agents configured with user selections:', agents);
        
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
                <div class="chat-preview">${room.last_message || ''}</div>
            </div>
            ${room.unread_count > 0 ? '<div class="unread-indicator"></div>' : ''}
        `;
        
        // 绑定点击事件
        chatItem.addEventListener('click', () => {
            this.selectRoom(room.id);
        });
        
        return chatItem;
    }

    // 选择房间
    selectRoom(roomId) {
        // 更新UI状态
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const selectedItem = document.querySelector(`[data-room-id="${roomId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
        
        this.currentRoomId = roomId;
        
        // 显示聊天区域
        this.showChatArea();
        
        // 请求房间历史消息
        window.wsManager.send({
            type: 'get_room_history',
            room_id: roomId
        });
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
            
            // 创建操作管理器 - 使用分离的ChatRoomActionManager
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
        
        // 绑定头部按钮事件
        this.bindHeaderButtons();
    }

    // 绑定头部按钮事件 - 增强版，多重绑定策略
    bindHeaderButtons() {
        console.log('🔄 Enhanced header buttons binding...');
        
        // 使用延迟绑定确保DOM元素完全渲染
        setTimeout(() => {
            this.performHeaderButtonsBinding();
        }, 50);
        
        // 使用requestAnimationFrame确保DOM更新完成
        requestAnimationFrame(() => {
            this.performHeaderButtonsBinding();
        });
    }
    
    // 执行实际的按钮绑定
    performHeaderButtonsBinding() {
        const agentInfoBtn = document.getElementById('agentInfoBtn');
        const moreOptionsBtn = document.getElementById('moreOptionsBtn');
        
        console.log('🎯 Performing button binding...', { 
            agentInfoBtn: agentInfoBtn ? 'Found' : 'Not found', 
            moreOptionsBtn: moreOptionsBtn ? 'Found' : 'Not found',
            actionManager: this.actionManager ? 'Available' : 'Not available'
        });
        
        // Agent信息按钮 - 多重绑定策略
        if (agentInfoBtn && !agentInfoBtn.hasAttribute('data-chat-manager-bound')) {
            // 方法1：标准事件监听器
            agentInfoBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('👤 Agent info button clicked (ChatManager binding)');
                this.handleAgentInfoClick();
            });
            
            // 方法2：直接onclick属性（备用）
            agentInfoBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('👤 Agent info button clicked (onclick backup)');
                this.handleAgentInfoClick();
            };
            
            // 标记已绑定，避免重复绑定
            agentInfoBtn.setAttribute('data-chat-manager-bound', 'true');
            console.log('✅ Agent info button binding completed');
        }
        
        // 更多选项按钮 - 多重绑定策略
        if (moreOptionsBtn && !moreOptionsBtn.hasAttribute('data-chat-manager-bound')) {
            // 方法1：标准事件监听器
            moreOptionsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('⋮ More options button clicked (ChatManager binding)');
                this.handleMoreOptionsClick(e);
            });
            
            // 方法2：直接onclick属性（备用）
            moreOptionsBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('⋮ More options button clicked (onclick backup)');
                this.handleMoreOptionsClick(e);
            };
            
            // 标记已绑定，避免重复绑定
            moreOptionsBtn.setAttribute('data-chat-manager-bound', 'true');
            console.log('✅ More options button binding completed');
        }
    }
    
    // 处理Agent信息按钮点击
    handleAgentInfoClick() {
        console.log('👤 ChatManager处理Agent信息按钮点击...');
        
        try {
            if (this.actionManager) {
                console.log('✅ 使用ActionManager.showAgentInfo');
                this.actionManager.showAgentInfo();
            } else {
                console.log('⚠️ ActionManager不可用，尝试重新初始化');
                this.reinitializeActionManager();
                
                // 重试一次
                if (this.actionManager) {
                    this.actionManager.showAgentInfo();
                } else {
                    console.log('❌ 无法初始化ActionManager，使用应用级别备用方法');
                    if (window.app && window.app.showAgentInfoModal) {
                        window.app.showAgentInfoModal();
                    } else {
                        showNotification('Agent信息功能暂时不可用，请刷新页面重试', 'warning');
                    }
                }
            }
        } catch (error) {
            console.error('❌ 处理Agent信息按钮时出错:', error);
            showNotification('无法显示Agent信息', 'error');
        }
    }
    
    // 处理更多选项按钮点击
    handleMoreOptionsClick(event) {
        console.log('⋮ ChatManager处理更多选项按钮点击...');
        
        try {
            if (this.actionManager) {
                console.log('✅ 使用ActionManager.showMoreOptions');
                this.actionManager.showMoreOptions(event);
            } else {
                console.log('⚠️ ActionManager不可用，尝试重新初始化');
                this.reinitializeActionManager();
                
                // 重试一次
                if (this.actionManager) {
                    this.actionManager.showMoreOptions(event);
                } else {
                    console.log('❌ 无法初始化ActionManager，使用应用级别备用方法');
                    if (window.app && window.app.showMoreOptionsDropdown) {
                        window.app.showMoreOptionsDropdown(event);
                    } else {
                        showNotification('更多选项功能暂时不可用，请刷新页面重试', 'warning');
                    }
                }
            }
        } catch (error) {
            console.error('❌ 处理更多选项按钮时出错:', error);
            showNotification('无法显示更多选项', 'error');
        }
    }
    
    // 重新初始化ActionManager
    reinitializeActionManager() {
        console.log('🔄 重新初始化ActionManager...');
        
        try {
            if (this.currentRoomId && window.ChatRoomActionManager) {
                this.actionManager = new ChatRoomActionManager(this.currentRoomId, this);
                console.log('✅ ActionManager重新初始化成功');
                return true;
            } else {
                console.error('❌ 无法重新初始化ActionManager: 缺少必要依赖');
                return false;
            }
        } catch (error) {
            console.error('❌ 重新初始化ActionManager时出错:', error);
            return false;
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
        // 🔍 详细调试：记录完整的WebSocket消息结构
        console.log('🔍 WebSocket消息接收调试:');
        console.log('📦 完整消息数据:', JSON.stringify(data, null, 2));
        console.log('📋 消息类型:', data.type);
        console.log('🏠 房间ID:', data.room_id);
        
        // 特别关注Agent消息的结构
        if (data.message && data.message.sender === 'agent') {
            console.log('🤖 Agent消息结构分析:');
            console.log('  - data.agent_name:', data.agent_name);
            console.log('  - data.message.agent_name:', data.message.agent_name);
            console.log('  - data.message:', JSON.stringify(data.message, null, 2));
        }
        
        if (data.room_id === this.currentRoomId) {
            this.displayMessage(data);
        }
        
        // 更新房间列表中的最后消息
        this.updateRoomLastMessage(data.room_id, data.content || (data.message && data.message.content));
    }

    // 加载房间历史消息
    loadRoomHistory(data) {
        if (data.room_id !== this.currentRoomId) return;
        
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer) return;
        
        messagesContainer.innerHTML = '';
        
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(message => {
                this.displayMessage(message, false);
            });
            
            // 滚动到底部
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    // 显示消息 - 简化版，无去重
    displayMessage(messageData, autoScroll = true) {
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
        messageDiv.className = `message ${messageData.sender || (messageData.message && messageData.message.sender)}`;
        
        // 🔍 调试：记录消息数据结构用于Agent名字获取
        console.log('🎯 createMessageElement 调试:');
        console.log('  - messageData.sender:', messageData.sender);
        console.log('  - messageData.message?.sender:', messageData.message?.sender);
        console.log('  - messageData.agent_name:', messageData.agent_name);
        console.log('  - messageData.message?.agent_name:', messageData.message?.agent_name);
        
        // 确定实际的sender
        const actualSender = messageData.sender || (messageData.message && messageData.message.sender);
        
        // 增强的Agent名字获取策略 - 确保数据一致性
        let agentName = 'Agent'; // 默认值
        if (actualSender === 'agent') {
            // 多重策略获取Agent名字，优先使用最可靠的来源
            agentName = messageData.agent_name || 
                       (messageData.message && messageData.message.agent_name) ||
                       this.getAgentNameFromContext(messageData) || // 从上下文获取
                       'Agent';
            
            // 数据清理：如果获取到的是"agent"，尝试从其他来源获取
            if (agentName === 'agent') {
                agentName = this.tryGetCorrectAgentName(messageData) || 'Agent';
            }
            
            console.log('🤖 Agent名字获取结果:', agentName);
        }
        
        const avatarText = actualSender === 'user' ? 'U' : 
                          (agentName ? agentName.charAt(0).toUpperCase() : 'A');
        
        // 获取消息内容和时间戳
        const content = messageData.content || (messageData.message && messageData.message.content) || '';
        const timestamp = messageData.timestamp || (messageData.message && messageData.message.timestamp) || new Date().toISOString();
        
        const time = new Date(timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        if (actualSender === 'agent') {
            // Agent消息：显示头像+名字+气泡
            const displayName = agentName; // 完整显示Agent名字
                
            messageDiv.innerHTML = `
                <div class="message-header">
                    <div class="message-avatar">${avatarText}</div>
                    <div class="agent-name">${displayName}</div>
                </div>
                <div class="message-bubble">
                    ${content}
                    <div class="message-time">${time}</div>
                </div>
            `;
            
            console.log('✅ Agent消息创建完成，显示名字:', displayName);
        } else {
            // 用户消息：保持原有结构
            messageDiv.innerHTML = `
                <div class="message-avatar">${avatarText}</div>
                <div class="message-bubble">
                    ${content}
                    <div class="message-time">${time}</div>
                </div>
            `;
        }
        
        return messageDiv;
    }

    // 从上下文获取Agent名字 - 新增辅助方法
    getAgentNameFromContext(messageData) {
        try {
            // 从房间信息中获取Agent名字
            const currentRoom = this.rooms.find(r => r.id === messageData.room_id);
            if (currentRoom && currentRoom.agents) {
                const agent = currentRoom.agents.find(a => a.id === messageData.sender_id);
                return agent ? agent.name : null;
            }
            return null;
        } catch (error) {
            console.warn('获取上下文Agent名字时出错:', error);
            return null;
        }
    }

    // 尝试获取正确的Agent名字 - 新增辅助方法
    tryGetCorrectAgentName(messageData) {
        try {
            // 策略1：从消息的嵌套结构中获取
            if (messageData.message && messageData.message.agent_name && messageData.message.agent_name !== 'agent') {
                return messageData.message.agent_name;
            }
            
            // 策略2：从sender_id推断Agent名字
            if (messageData.sender_id && messageData.sender_id !== 'agent') {
                // 如果sender_id是UUID格式，尝试从房间配置中查找
                const currentRoom = this.rooms.find(r => r.id === messageData.room_id);
                if (currentRoom && currentRoom.agents) {
                    const agent = currentRoom.agents.find(a => a.id === messageData.sender_id);
                    if (agent && agent.name) {
                        return agent.name;
                    }
                }
            }
            
            // 策略3：使用默认的Agent编号
            return 'Agent 1'; // 比"agent"更友好的默认值
        } catch (error) {
            console.warn('尝试获取正确Agent名字时出错:', error);
            return null;
        }
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
    
    // 显示初始欢迎页面（替代工作区） - 统一版本
    showInitialWelcome() {
        const chatArea = document.getElementById('chatArea');
        const workspace = document.getElementById('workspace');
        
        if (chatArea) {
            chatArea.innerHTML = `
                <div class="empty-state" id="emptyState">
                    <div class="initial-welcome-container">
                        <div class="welcome-content">
                            <div class="welcome-icon">💬</div>
                            <h2>欢迎使用 SocioPulse AI</h2>
                            <p>您还没有创建任何聊天室</p>
                            <p>点击左侧的"+"按钮开始您的第一次对话</p>
                            <button class="welcome-create-btn" onclick="window.chatManager?.showCreateRoomModal()">
                                <span class="btn-icon">➕</span>
                                创建第一个聊天室
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // 隐藏工作区，显示欢迎页面
        if (workspace) {
            workspace.classList.remove('active');
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
