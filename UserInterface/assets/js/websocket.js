// WebSocket连接管理模块

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000;
        this.messageHandlers = new Map();
        this.lastServerRestartId = null; // 追踪服务器重启ID
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
            return true;
        } else {
            console.error('WebSocket not connected');
            showNotification('连接已断开，请刷新页面重试', 'error');
            return false;
        }
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
        console.log('Received WebSocket message:', messageType, data);

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
    // 处理新消息 - 只处理Agent回复，忽略用户消息
    console.log('💬 Processing new_message:', data);
    if (!handlerFound && window.chatManager) {
        try {
            // 如果当前选中的房间是消息来源房间，显示消息
            if (window.chatManager.currentRoomId === data.room_id) {
                const message = data.message;
                
                // 只处理非用户消息（Agent回复、系统消息等）
                if (message.sender !== 'user') {
                    const messageData = {
                        room_id: data.room_id,
                        sender: message.sender || 'System',
                        content: message.content || '',
                        timestamp: message.timestamp || new Date().toISOString(),
                        message_id: message.id || message.message_id || `ws_${Date.now()}`,
                        sender_type: message.sender_type || message.message_type || 'system',
                        agent_name: message.sender
                    };
                    
                    console.log('📝 Displaying agent message:', messageData);
                    window.chatManager.displayMessage(messageData);
                } else {
                    console.log('🚫 Ignoring user message from WebSocket (already displayed locally)');
                }
            }
            console.log('✅ New message processed successfully');
        } catch (error) {
            console.error('❌ Error processing new message:', error);
        }
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
