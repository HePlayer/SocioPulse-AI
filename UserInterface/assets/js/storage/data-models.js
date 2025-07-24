/**
 * 数据模型定义
 * 定义消息、房间等数据结构的验证和创建方法
 */

// 消息数据模型
class MessageModel {
    /**
     * 验证消息数据结构 - 修复版：确保Agent身份信息完整保存
     * @param {Object} message - 消息对象
     * @returns {Object} 验证后的消息对象
     */
    static validate(message) {
        if (!message || typeof message !== 'object') {
            throw new Error('消息数据必须是对象');
        }

        const validated = {
            id: message.id || this.generateId(),
            roomId: message.roomId || message.room_id,
            sender: message.sender,
            content: message.content || '',
            timestamp: message.timestamp || new Date().toISOString(),
            messageType: message.messageType || message.message_type || 'text'
        };

        // 验证必填字段
        if (!validated.roomId) {
            throw new Error('消息必须包含房间ID');
        }

        if (!validated.sender) {
            throw new Error('消息必须包含发送者信息');
        }

        // Agent消息的特殊处理 - 确保Agent身份信息完整保存
        if (validated.sender === 'agent' || message.agentName || message.agent_name) {
            // 确保sender正确设置为agent
            validated.sender = 'agent';
            
            // 保存Agent名字 - 支持多种字段名
            validated.agentName = message.agentName || message.agent_name || 'Agent';
            validated.agent_name = validated.agentName; // 同时保存两种格式
            
            // 保存Agent ID
            validated.senderId = message.senderId || message.sender_id || validated.agentName;
            validated.sender_id = validated.senderId; // 同时保存两种格式
            
            console.log('💾 Agent消息身份信息保存:', {
                sender: validated.sender,
                agentName: validated.agentName,
                agent_name: validated.agent_name,
                senderId: validated.senderId
            });
        }

        // 用户消息的处理
        if (validated.sender === 'user') {
            validated.senderId = 'user';
            validated.sender_id = 'user';
        }

        // 添加元数据
        validated.metadata = message.metadata || {};
        if (message.platform) validated.metadata.platform = message.platform;
        if (message.model) validated.metadata.model = message.model;

        // 添加消息来源标记，用于去重
        validated.source = message.source || 'websocket';
        validated.isLocal = message.isLocal || false;

        return validated;
    }

    /**
     * 创建标准化的消息对象
     * @param {Object} data - 原始消息数据
     * @returns {Object} 标准化的消息对象
     */
    static create(data) {
        return this.validate(data);
    }

    /**
     * 生成唯一ID
     * @returns {string} 唯一标识符
     */
    static generateId() {
        return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    }

    /**
     * 从WebSocket消息数据创建消息对象
     * @param {Object} wsData - WebSocket消息数据
     * @returns {Object} 标准化的消息对象
     */
    static fromWebSocketData(wsData) {
        const messageData = wsData.message || wsData;
        
        return this.create({
            id: messageData.id || this.generateId(),
            roomId: wsData.room_id || messageData.roomId,
            sender: messageData.sender,
            agentName: wsData.agent_name || messageData.agent_name,
            senderId: messageData.sender_id,
            content: messageData.content,
            timestamp: messageData.timestamp,
            messageType: messageData.message_type || messageData.messageType || 'text',
            metadata: messageData.metadata || {}
        });
    }
}

// 房间数据模型
class RoomModel {
    /**
     * 验证房间数据结构
     * @param {Object} room - 房间对象
     * @returns {Object} 验证后的房间对象
     */
    static validate(room) {
        if (!room || typeof room !== 'object') {
            throw new Error('房间数据必须是对象');
        }

        const validated = {
            roomId: room.roomId || room.room_id || room.id,
            roomName: room.roomName || room.room_name || '未命名房间',
            agents: Array.isArray(room.agents) ? room.agents : [],
            createdAt: room.createdAt || room.created_at || new Date().toISOString(),
            lastActivity: room.lastActivity || room.last_activity || new Date().toISOString(),
            messageCount: room.messageCount || room.message_count || 0,
            settings: room.settings || {}
        };

        // 验证必填字段
        if (!validated.roomId) {
            throw new Error('房间必须包含ID');
        }

        // 设置默认的聊天类型
        if (!validated.settings.chatType) {
            validated.settings.chatType = validated.agents.length > 1 ? 'group' : 'single';
        }

        return validated;
    }

    /**
     * 创建标准化的房间对象
     * @param {Object} data - 原始房间数据
     * @returns {Object} 标准化的房间对象
     */
    static create(data) {
        return this.validate(data);
    }

    /**
     * 从房间列表数据创建房间对象
     * @param {Object} roomData - 房间列表中的房间数据
     * @returns {Object} 标准化的房间对象
     */
    static fromRoomListData(roomData) {
        return this.create({
            roomId: roomData.id || roomData.room_id,
            roomName: roomData.room_name || roomData.name,
            agents: roomData.agents || [],
            messageCount: roomData.message_count || 0,
            lastMessage: roomData.last_message,
            agentCount: roomData.agent_count || 0
        });
    }
}

// 扩展数据模型
class ExtensionModel {
    /**
     * 验证扩展数据结构
     * @param {string} type - 数据类型
     * @param {string} roomId - 房间ID
     * @param {Object} data - 扩展数据
     * @returns {Object} 验证后的扩展数据对象
     */
    static validate(type, roomId, data) {
        if (!type || typeof type !== 'string') {
            throw new Error('扩展数据类型必须是字符串');
        }

        if (!roomId || typeof roomId !== 'string') {
            throw new Error('房间ID必须是字符串');
        }

        return {
            id: this.generateId(),
            type: type,
            roomId: roomId,
            data: data || {},
            timestamp: new Date().toISOString(),
            version: '1.0'
        };
    }

    /**
     * 创建扩展数据对象
     * @param {string} type - 数据类型
     * @param {string} roomId - 房间ID
     * @param {Object} data - 扩展数据
     * @returns {Object} 扩展数据对象
     */
    static create(type, roomId, data) {
        return this.validate(type, roomId, data);
    }

    /**
     * 生成唯一ID
     * @returns {string} 唯一标识符
     */
    static generateId() {
        return `ext_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    }
}

// 导出所有模型
window.MessageModel = MessageModel;
window.RoomModel = RoomModel;
window.ExtensionModel = ExtensionModel;

console.log('✅ 数据模型已加载');
