// WebSocket连接管理模块

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000;
        this.messageHandlers = new Map();
        this.lastServerRestartId = null; // 追踪服务器重启ID

        // 🔧 CRITICAL FIX: 添加房间重连管理
        this.lastJoinedRoom = null;
        this.roomJoinRetries = new Map(); // {roomId: retryCount}
        this.maxRoomJoinRetries = 3;
    }

    // 连接WebSocket
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // 修复WebSocket URL - 使用正确的主机地址
        const host = window.location.host || 'localhost:8000';
        const wsUrl = `${protocol}//${host}/ws`;

        console.log('🔌 Connecting to WebSocket:', wsUrl);

        // 🔧 增强修复：在连接前就强制清空状态
        this.forceCleanupFrontendState('before_connect');

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;

            // 🔧 增强修复：连接后再次强制清空（双重保险）
            this.forceCleanupFrontendState('after_connect');

            // 获取最新房间列表
            this.send({ type: 'get_rooms' });

            // 🔧 CRITICAL FIX: 自动重新加入上次的房间
            this.autoRejoinLastRoom();
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.attemptReconnect();
        };
    }

    // 🔧 新增：强制清空前端状态的方法
    forceCleanupFrontendState(context = '') {
        console.log(`🧹 Force cleaning frontend state [${context}]`);

        try {
            // 清空ChatManager状态
            if (window.chatManager) {
                console.log('📋 Clearing ChatManager state...');
                window.chatManager.rooms = [];
                window.chatManager.currentRoomId = null;

                // 清空UI
                try {
                    window.chatManager.updateRoomsList([]);
                    window.chatManager.showInitialWelcome();
                    console.log('✅ ChatManager UI cleared successfully');
                } catch (uiError) {
                    console.warn('⚠️ UI clearing failed, but state cleared:', uiError);
                }
            }

            // 清空任何可能的本地存储（如果有的话）
            try {
                // 注意：这里不清空设置，只清空房间相关数据
                const keys = Object.keys(localStorage);
                keys.forEach(key => {
                    if (key.includes('room') || key.includes('chat')) {
                        localStorage.removeItem(key);
                        console.log(`🗑️ Removed localStorage key: ${key}`);
                    }
                });
            } catch (storageError) {
                console.warn('⚠️ localStorage cleanup failed:', storageError);
            }

            // 强制垃圾回收相关变量（如果浏览器支持）
            if (window.gc && typeof window.gc === 'function') {
                window.gc();
                console.log('♻️ Triggered garbage collection');
            }

            console.log(`✅ Frontend state cleanup completed [${context}]`);

        } catch (error) {
            console.error(`❌ Error during frontend state cleanup [${context}]:`, error);
        }
    }

    // 尝试重连
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

            // 🔧 增强修复：重连前也强制清空状态
            this.forceCleanupFrontendState('before_reconnect');

            setTimeout(() => this.connect(), this.reconnectInterval);
        } else {
            console.error('Max reconnection attempts reached');
            showNotification('连接已断开，请刷新页面重试', 'error');
        }
    }

    // 发送消息
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));

            // 🔧 CRITICAL FIX: 记录房间加入请求
            if (data.type === 'join_room' && data.room_id) {
                this.lastJoinedRoom = data.room_id;
                console.log('📝 记录最后加入的房间:', data.room_id);
            }

            return true;
        } else {
            console.error('WebSocket not connected');
            showNotification('连接已断开，请刷新页面重试', 'error');
            return false;
        }
    }

    // 🚀 新增：处理讨论框架的实时事件
    handleDiscussionFrameworkEvent(eventData) {
        if (!window.chatManager) return;

        console.log('📡 处理讨论框架事件:', eventData);

        switch (eventData.type) {
            case 'discussion_started':
                window.chatManager.handleDiscussionStateChange('running');
                break;
            case 'discussion_ended':
            case 'discussion_stopped':
                window.chatManager.handleDiscussionStateChange('stopped');
                break;
            case 'discussion_paused':
                console.log('⏸️ 讨论已暂停');
                break;
            case 'discussion_resumed':
                console.log('▶️ 讨论已恢复');
                break;
        }
    }

    // 🔧 CRITICAL FIX: 自动重新加入上次的房间
    autoRejoinLastRoom() {
        if (this.lastJoinedRoom && window.chatManager && window.chatManager.currentRoomId) {
            const currentRoom = window.chatManager.currentRoomId;
            console.log('🔄 WebSocket重连后自动重新加入房间:', currentRoom);

            // 重置重试计数
            this.roomJoinRetries.delete(currentRoom);

            // 发送join_room消息
            setTimeout(() => {
                this.send({
                    type: 'join_room',
                    room_id: currentRoom
                });
                console.log('📤 自动重连：发送join_room消息');
            }, 500); // 延迟500ms确保连接稳定
        }
    }

    // 🔧 CRITICAL FIX: 房间加入重试逻辑
    retryRoomJoin(roomId) {
        const retryCount = this.roomJoinRetries.get(roomId) || 0;

        if (retryCount < this.maxRoomJoinRetries) {
            this.roomJoinRetries.set(roomId, retryCount + 1);

            console.log(`🔄 重试加入房间 ${roomId} (第${retryCount + 1}次)`);

            setTimeout(() => {
                this.send({
                    type: 'join_room',
                    room_id: roomId
                });
            }, 1000 * (retryCount + 1)); // 递增延迟

            return true;
        } else {
            console.error(`❌ 房间 ${roomId} 加入重试次数已达上限`);
            showNotification('加入房间失败，请手动重试', 'error');
            this.roomJoinRetries.delete(roomId);
            return false;
        }
    }

    // 🔒 安全转义 + 换行格式化
    sanitizeAndFormatContent(text) {
        const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;'
        }[c]));
        // 先转义，再把换行替换为 <br>
        return esc(text).replace(/\r?\n/g, '<br>');
    }

    // 📦 标准化后端 new_message 消息（兼容两种形态）
    normalizeIncomingMessage(data) {
        const m = data && data.message ? data.message : {};
        const sender = m.sender || data.sender || 'agent';
        const agentName = data.agent_name || m.agent_name || ((sender !== 'user' && sender !== 'system') ? sender : 'Agent');
        return {
            room_id: data.room_id,
            sender: sender || 'system',
            agent_name: agentName,
            content: this.sanitizeAndFormatContent((data.content ?? m.content) ?? ''),
            timestamp: data.timestamp || m.timestamp || new Date().toISOString(),
            message_id: data.message_id || m.id || m.message_id || `ws_${Date.now()}`,
            sender_type: m.sender_type || m.message_type || 'text',
            source: 'websocket',
            isLocal: false,
            _broadcast_fallback: data._broadcast_fallback === true
        };
    }


    // 注册消息处理器
    registerHandler(messageType, handler) {
        if (!this.messageHandlers.has(messageType)) {
            this.messageHandlers.set(messageType, []);
        }
        this.messageHandlers.get(messageType).push(handler);
    }

    // 处理WebSocket消息 - 增强版
    handleMessage(data) {
        const messageType = data.type;
        console.log('📨 WebSocket消息接收:', {
            type: data.type,
            messageType: messageType,
            room_id: data.room_id,
            timestamp: new Date().toLocaleTimeString(),
            data: data
        });

        // 调用注册的处理器
        let handlerFound = false;
        if (this.messageHandlers.has(messageType)) {
            handlerFound = true;
            this.messageHandlers.get(messageType).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in message handler for ${messageType}:`, error);
                }
            });
        }

        // 🚀 新增：讨论框架事件处理
        switch (messageType) {
            case 'DISCUSSION_FRAMEWORK_STARTED':
                console.log('🚀 讨论框架启动:', data);
                if (window.chatManager && data.room_id === window.chatManager.currentRoomId) {
                    console.log('🎯 触发讨论状态变化: running');
                    window.chatManager.handleDiscussionStateChange('running');
                }
                break;

            case 'discussion_started':
                console.log('🎯 讨论开始事件:', data);
                if (window.chatManager && data.room_id === window.chatManager.currentRoomId) {
                    console.log('🎯 触发讨论状态变化: running');
                    window.chatManager.handleDiscussionStateChange('running');
                }
                break;

            case 'discussion_ended':
            case 'discussion_stopped':
                console.log('🛑 讨论结束事件:', data);
                if (window.chatManager && data.room_id === window.chatManager.currentRoomId) {
                    console.log('🎯 触发讨论状态变化: stopped');
                    window.chatManager.handleDiscussionStateChange('stopped');
                }
                break;

            case 'discussion_paused':
                console.log('⏸️ 讨论暂停事件:', data);
                if (window.chatManager && data.room_id === window.chatManager.currentRoomId) {
                    console.log('🎯 触发讨论状态变化: paused');
                    // 暂停事件不改变按钮状态，因为用户已经点击了停止
                }
                break;

            case 'event':
                // 处理讨论框架的实时事件
                if (data.data && data.data.type) {
                    this.handleDiscussionFrameworkEvent(data.data);
                }
                break;
        }

        // 默认消息处理
        switch (messageType) {
            case 'connection':
                console.log('Connected with ID:', data.connection_id);

                // 🔧 服务器重启检测
                if (data.server_restart_id) {
                    console.log('🔄 Server restart ID detected:', data.server_restart_id);

                    if (this.lastServerRestartId && this.lastServerRestartId !== data.server_restart_id) {
                        // 服务器重启了！强制清空前端状态
                        console.log('🚨 Server restart detected! Previous ID:', this.lastServerRestartId, 'New ID:', data.server_restart_id);
                        this.forceCleanupFrontendState('server_restart_detected');
                        showNotification('检测到服务器重启，已自动刷新状态', 'info');
                    } else if (!this.lastServerRestartId) {
                        console.log('🆕 First connection, storing server restart ID');
                    }

                    // 更新记录的重启ID
                    this.lastServerRestartId = data.server_restart_id;
                }
                break;
            case 'error':
                console.error('Server error:', data.message);

                // 🔧 CRITICAL FIX: 检查是否为房间相关错误，尝试重试
                if (data.message && (data.message.includes('Room') && data.message.includes('not found')) ||
                    data.message.includes('join_room')) {
                    console.log('🔄 检测到房间相关错误，尝试重新加入...');
                    const currentRoom = window.chatManager?.currentRoomId;
                    if (currentRoom) {
                        this.retryRoomJoin(currentRoom);
                    }
                }

                // 智能处理房间状态错误
                if ((data.error_code === 'ROOM_NOT_FOUND' && data.action === 'cleanup_required') ||
                    (data.error_code === 'ROOM_INVALID' && data.action === 'room_cleaned')) {

                    console.log('🧹 Room state error detected, triggering cleanup for room:', data.room_id);
                    console.log('Error type:', data.error_code, 'Action:', data.action);

                    // 通知ChatManager清理无效房间
                    if (window.chatManager) {
                        try {
                            // 从本地房间列表中移除无效房间
                            window.chatManager.rooms = window.chatManager.rooms.filter(room => room.id !== data.room_id);

                            // 如果当前选中的是无效房间，切换到其他房间或显示欢迎页面
                            if (window.chatManager.currentRoomId === data.room_id) {
                                window.chatManager.currentRoomId = null;

                                if (window.chatManager.rooms.length > 0) {
                                    // 选择第一个可用房间
                                    window.chatManager.selectRoom(window.chatManager.rooms[0].id);
                                    console.log('🎯 Auto-switched to available room:', window.chatManager.rooms[0].room_name);
                                } else {
                                    // 显示欢迎页面
                                    window.chatManager.showInitialWelcome();
                                    console.log('🏠 Showing welcome page - no rooms available');
                                }
                            }

                            // 更新房间列表UI
                            window.chatManager.updateRoomsList(window.chatManager.rooms);

                            // 显示友好的用户提示
                            const message = data.error_code === 'ROOM_INVALID'
                                ? '聊天室状态异常已自动修复，请重新创建聊天室'
                                : '已自动清理无效的聊天室';
                            showNotification(message, 'info');
                            console.log('✅ Room cleanup completed successfully');
                        } catch (error) {
                            console.error('❌ Error during room cleanup:', error);
                            showNotification('清理聊天室时出错', 'warning');
                        }
                    }
                } else {
                    showNotification('服务器错误: ' + data.message, 'error');
                }
                break;
            case 'rooms_list':
                // 确保房间列表消息被处理
                if (!handlerFound && window.chatManager) {
                    console.log('📋 Handling rooms_list message directly');
                    try {
                        window.chatManager.updateRoomsList(data.rooms);
                        console.log('✅ Rooms list updated successfully');
                    } catch (error) {
                        console.error('❌ Error updating rooms list:', error);
                    }
                }
                break;
            case 'room_joined':
                // 🔧 CRITICAL FIX: 处理join_room响应，添加重试逻辑
                console.log('✅ 房间加入响应:', data);

                if (data.room_id) {
                    console.log(`✅ 成功加入房间: ${data.room_id}`);

                    // 清除重试计数
                    this.roomJoinRetries.delete(data.room_id);

                    // 验证当前房间ID匹配
                    if (window.chatManager && window.chatManager.currentRoomId === data.room_id) {
                        console.log('✅ 房间ID匹配，连接已注册到服务器');
                        showNotification('已加入房间，可以开始对话', 'success');
                    } else {
                        console.warn('⚠️ 房间ID不匹配:', {
                            response_room: data.room_id,
                            current_room: window.chatManager?.currentRoomId
                        });
                    }
                } else {
                    console.error('❌ 加入房间失败:', data);

                    // 🔧 CRITICAL FIX: 尝试重试加入房间
                    const currentRoom = window.chatManager?.currentRoomId;
                    if (currentRoom) {
                        const retrySuccess = this.retryRoomJoin(currentRoom);
                        if (!retrySuccess) {
                            showNotification('加入房间失败，请手动重试', 'error');
                        }
                    } else {
                        showNotification('加入房间失败，请重试', 'error');
                    }
                }
                break;
            case 'room_created':
                // 确保房间创建消息被处理 - 增强版
                console.log('🏗️ Processing room_created message:', data);

                if (data.success) {
                    // 显示成功通知
                    showNotification(`聊天室 "${data.room_name || '新聊天室'}" 创建成功`, 'success');

                    // 如果有ChatManager且数据完整，立即更新房间列表
                    if (window.chatManager && data.room_id && data.room_name) {
                        console.log('✅ Immediately updating rooms list with new room');
                        try {
                            // 创建新房间对象
                            const newRoom = {
                                id: data.room_id,
                                room_id: data.room_id,
                                room_name: data.room_name,
                                agent_count: data.agents ? data.agents.length : 1,
                                last_message: '暂无消息'
                            };

                            // 立即添加到房间列表（如果还没有的话）
                            if (!window.chatManager.rooms.find(r => r.id === data.room_id)) {
                                window.chatManager.rooms.push(newRoom);
                                window.chatManager.updateRoomsList(window.chatManager.rooms);
                                console.log('📋 New room added to local list immediately');
                            }

                            // 选择新创建的聊天室
                            window.chatManager.selectRoom(data.room_id);
                            console.log('🎯 Auto-selected new room:', data.room_id);

                        } catch (error) {
                            console.error('❌ Error handling immediate room update:', error);
                        }
                    }

                    // 无论如何都请求最新的房间列表（确保数据一致性）
                    if (!handlerFound) {
                        setTimeout(() => {
                            console.log('🔄 Requesting updated rooms list for consistency');
                            this.send({ type: 'get_rooms' });
                        }, 100); // 短延迟以避免竞争条件
                    }
                } else {
                    // 创建失败
                    const errorMsg = data.message || '创建聊天室失败';
                    console.error('❌ Room creation failed:', errorMsg);
                    showNotification('创建失败: ' + errorMsg, 'error');
                }
                break;
case 'new_message':
    // 🔧 使用标准化流程处理新消息
    console.log('💬 Processing new_message - STANDARDIZED:');
    console.log('  📦 完整消息数据:', JSON.stringify(data, null, 2));

    if (!handlerFound && window.chatManager) {
        try {
            const isRoomMatch = window.chatManager.currentRoomId === data.room_id;
            const isFallbackBroadcast = data._broadcast_fallback === true;

            if (isRoomMatch || (isFallbackBroadcast && data.room_id === window.chatManager.currentRoomId)) {
                const normalized = this.normalizeIncomingMessage(data);

                // 只显示非用户消息，避免与本地用户消息重复
                if (normalized.sender === 'user') {
                    console.log('🚫 忽略用户消息 (已在本地显示)');
                    break;
                }

                console.log('🧰 标准化后的消息数据:', JSON.stringify(normalized, null, 2));
                window.chatManager.displayMessage(normalized);
                console.log('✅ 标准化消息已发送到chatManager');
            } else {
                console.log('🚫 消息被过滤（房间不匹配）');
            }
            console.log('✅ New message processed successfully');
        } catch (error) {
            console.error('❌ Error processing new message:', error);
            console.error('❌ Error stack:', error.stack);
        }
    } else {
        console.warn('⚠️ 消息处理跳过:');
        console.warn('  handlerFound:', handlerFound);
        console.warn('  window.chatManager:', !!window.chatManager);
    }
    break;
            case 'message_sent':
                // 处理消息发送确认 - 只处理错误，不显示Agent回复（Agent回复由new_message处理）
                console.log('📤 Processing message_sent:', data);
                if (!handlerFound) {
                    try {
                        if (data.success) {
                            // 消息发送成功，但不在这里显示Agent回复
                            console.log('✅ Message sent successfully, waiting for agent response via new_message');
                        } else {
                            // 显示错误消息
                            showNotification('消息发送失败: ' + (data.error || data.message || '未知错误'), 'error');
                            console.log('❌ Message sending failed:', data.error || data.message);
                        }
                    } catch (error) {
                        console.error('❌ Error processing message sent confirmation:', error);
                    }
                }
                break;
            default:
                console.log('Unhandled message type:', messageType);
        }
    }

    // 检查连接状态
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    // 关闭连接
    close() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// 全局导出
window.WebSocketManager = WebSocketManager;
