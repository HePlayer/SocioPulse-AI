// WebSocket连接管理模块

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000;
        this.messageHandlers = new Map();
    }

    // 连接WebSocket
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // 修复WebSocket URL - 使用正确的主机地址
        const host = window.location.host || 'localhost:8000';
        const wsUrl = `${protocol}//${host}/ws`;
        
        console.log('🔌 Connecting to WebSocket:', wsUrl);
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            // 获取房间列表
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

    // 尝试重连
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
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
                break;
            case 'error':
                console.error('Server error:', data.message);
                showNotification('服务器错误: ' + data.message, 'error');
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
