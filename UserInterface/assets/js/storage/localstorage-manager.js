/**
 * localStorage管理器
 * 提供快速缓存和配额管理功能
 */

class LocalStorageManager {
    constructor() {
        this.prefix = 'socioPulse_';
        this.maxRecentMessages = 100; // 每个房间最多缓存100条最近消息
        this.maxTotalSize = 5 * 1024 * 1024; // 5MB总限制
        this.compressionEnabled = true;
        this.stats = {
            reads: 0,
            writes: 0,
            errors: 0,
            quotaExceeded: 0
        };
    }

    /**
     * 更新最近消息缓存
     * @param {Object} message - 消息对象
     */
    updateRecentMessages(message) {
        if (!message || !message.roomId) {
            return false;
        }

        try {
            const key = `${this.prefix}recent_${message.roomId}`;
            let recentMessages = this.getItem(key) || [];

            // 检查是否已存在
            const existingIndex = recentMessages.findIndex(msg => msg.id === message.id);
            
            if (existingIndex === -1) {
                // 添加新消息
                recentMessages.push(message);
            } else {
                // 更新现有消息
                recentMessages[existingIndex] = message;
            }

            // 按时间戳排序
            recentMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

            // 保持最大数量限制
            if (recentMessages.length > this.maxRecentMessages) {
                recentMessages = recentMessages.slice(-this.maxRecentMessages);
            }

            this.setItem(key, recentMessages);
            return true;

        } catch (error) {
            console.warn('更新localStorage缓存失败:', error);
            this.stats.errors++;
            return false;
        }
    }

    /**
     * 批量更新消息缓存
     * @param {Array} messages - 消息数组
     */
    updateRecentMessagesBatch(messages) {
        if (!Array.isArray(messages)) {
            return false;
        }

        // 按房间分组
        const messagesByRoom = {};
        messages.forEach(message => {
            if (message.roomId) {
                if (!messagesByRoom[message.roomId]) {
                    messagesByRoom[message.roomId] = [];
                }
                messagesByRoom[message.roomId].push(message);
            }
        });

        let successCount = 0;
        
        // 为每个房间更新缓存
        Object.entries(messagesByRoom).forEach(([roomId, roomMessages]) => {
            try {
                const key = `${this.prefix}recent_${roomId}`;
                let existingMessages = this.getItem(key) || [];

                // 合并消息并去重
                const allMessages = this.mergeAndDeduplicateMessages(existingMessages, roomMessages);

                // 按时间戳排序并限制数量
                allMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                const limitedMessages = allMessages.slice(-this.maxRecentMessages);

                this.setItem(key, limitedMessages);
                successCount++;

            } catch (error) {
                console.warn(`更新房间 ${roomId} 的缓存失败:`, error);
                this.stats.errors++;
            }
        });

        return successCount;
    }

    /**
     * 获取最近消息
     * @param {string} roomId - 房间ID
     * @returns {Array} 消息数组
     */
    getRecentMessages(roomId) {
        if (!roomId) {
            return [];
        }

        const key = `${this.prefix}recent_${roomId}`;
        const messages = this.getItem(key) || [];
        this.stats.reads++;
        return messages;
    }

    /**
     * 清理房间缓存
     * @param {string} roomId - 房间ID
     */
    clearRoomCache(roomId) {
        if (!roomId) {
            return false;
        }

        try {
            const key = `${this.prefix}recent_${roomId}`;
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.warn('清理房间缓存失败:', error);
            this.stats.errors++;
            return false;
        }
    }

    /**
     * 保存房间信息
     * @param {Object} room - 房间对象
     */
    saveRoomInfo(room) {
        if (!room || !room.roomId) {
            return false;
        }

        try {
            const key = `${this.prefix}room_${room.roomId}`;
            const roomInfo = {
                roomId: room.roomId,
                roomName: room.roomName,
                agents: room.agents,
                lastActivity: room.lastActivity || new Date().toISOString(),
                messageCount: room.messageCount || 0,
                settings: room.settings || {},
                cachedAt: new Date().toISOString()
            };

            this.setItem(key, roomInfo);
            return true;

        } catch (error) {
            console.warn('保存房间信息失败:', error);
            this.stats.errors++;
            return false;
        }
    }

    /**
     * 获取房间信息
     * @param {string} roomId - 房间ID
     * @returns {Object|null} 房间信息
     */
    getRoomInfo(roomId) {
        if (!roomId) {
            return null;
        }

        const key = `${this.prefix}room_${roomId}`;
        return this.getItem(key);
    }

    /**
     * 保存用户设置
     * @param {string} settingKey - 设置键
     * @param {*} value - 设置值
     */
    saveSetting(settingKey, value) {
        try {
            const key = `${this.prefix}setting_${settingKey}`;
            this.setItem(key, {
                value: value,
                updatedAt: new Date().toISOString()
            });
            return true;
        } catch (error) {
            console.warn('保存设置失败:', error);
            this.stats.errors++;
            return false;
        }
    }

    /**
     * 获取用户设置
     * @param {string} settingKey - 设置键
     * @param {*} defaultValue - 默认值
     * @returns {*} 设置值
     */
    getSetting(settingKey, defaultValue = null) {
        const key = `${this.prefix}setting_${settingKey}`;
        const setting = this.getItem(key);
        return setting ? setting.value : defaultValue;
    }

    /**
     * 安全的存储操作
     * @param {string} key - 键
     * @param {*} value - 值
     */
    setItem(key, value) {
        try {
            const serialized = JSON.stringify(value);
            
            // 检查数据大小
            if (serialized.length > 1024 * 1024) { // 1MB单项限制
                console.warn(`数据过大，跳过存储: ${key}`);
                return false;
            }

            // 检查总存储大小
            if (this.getCurrentStorageSize() + serialized.length > this.maxTotalSize) {
                this.cleanupOldCache();
            }

            localStorage.setItem(key, serialized);
            this.stats.writes++;
            return true;

        } catch (error) {
            if (error.name === 'QuotaExceededError') {
                this.stats.quotaExceeded++;
                console.warn('localStorage配额超限，尝试清理缓存');
                
                if (this.cleanupOldCache()) {
                    // 清理后重试
                    try {
                        localStorage.setItem(key, JSON.stringify(value));
                        this.stats.writes++;
                        return true;
                    } catch (retryError) {
                        console.error('重试存储失败:', retryError);
                        return false;
                    }
                }
            } else {
                console.error('localStorage存储失败:', error);
                this.stats.errors++;
            }
            return false;
        }
    }

    /**
     * 安全的读取操作
     * @param {string} key - 键
     * @returns {*} 值
     */
    getItem(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (error) {
            console.warn('解析localStorage数据失败:', error);
            this.stats.errors++;
            // 删除损坏的数据
            localStorage.removeItem(key);
            return null;
        }
    }

    /**
     * 清理旧缓存
     * @returns {boolean} 是否成功清理
     */
    cleanupOldCache() {
        try {
            const keysToRemove = [];
            const now = Date.now();
            const maxAge = 7 * 24 * 60 * 60 * 1000; // 7天

            // 查找过期的缓存项
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                
                if (key && key.startsWith(this.prefix)) {
                    try {
                        const data = this.getItem(key);
                        
                        if (data && data.cachedAt) {
                            const cacheTime = new Date(data.cachedAt).getTime();
                            if (now - cacheTime > maxAge) {
                                keysToRemove.push(key);
                            }
                        } else if (key.includes('recent_')) {
                            // 对于没有时间戳的recent缓存，检查最后一条消息的时间
                            if (Array.isArray(data) && data.length > 0) {
                                const lastMessage = data[data.length - 1];
                                if (lastMessage.timestamp) {
                                    const messageTime = new Date(lastMessage.timestamp).getTime();
                                    if (now - messageTime > maxAge) {
                                        keysToRemove.push(key);
                                    }
                                }
                            }
                        }
                    } catch (error) {
                        // 损坏的数据也删除
                        keysToRemove.push(key);
                    }
                }
            }

            // 删除过期项
            keysToRemove.forEach(key => {
                localStorage.removeItem(key);
            });

            console.log(`清理了 ${keysToRemove.length} 个过期缓存项`);
            return keysToRemove.length > 0;

        } catch (error) {
            console.error('清理缓存失败:', error);
            return false;
        }
    }

    /**
     * 获取当前存储大小
     * @returns {number} 存储大小（字节）
     */
    getCurrentStorageSize() {
        let totalSize = 0;
        
        try {
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith(this.prefix)) {
                    const value = localStorage.getItem(key);
                    if (value) {
                        totalSize += key.length + value.length;
                    }
                }
            }
        } catch (error) {
            console.warn('计算存储大小失败:', error);
        }

        return totalSize;
    }

    /**
     * 合并并去重消息
     * @param {Array} existing - 现有消息
     * @param {Array} newMessages - 新消息
     * @returns {Array} 合并后的消息
     */
    mergeAndDeduplicateMessages(existing, newMessages) {
        const messageMap = new Map();

        // 添加现有消息
        existing.forEach(msg => {
            if (msg.id) {
                messageMap.set(msg.id, msg);
            }
        });

        // 添加新消息（会覆盖重复的）
        newMessages.forEach(msg => {
            if (msg.id) {
                messageMap.set(msg.id, msg);
            }
        });

        return Array.from(messageMap.values());
    }

    /**
     * 获取所有房间的缓存信息
     * @returns {Array} 房间缓存信息
     */
    getAllRoomCacheInfo() {
        const roomCaches = [];
        
        try {
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                
                if (key && key.startsWith(`${this.prefix}recent_`)) {
                    const roomId = key.replace(`${this.prefix}recent_`, '');
                    const messages = this.getItem(key) || [];
                    
                    roomCaches.push({
                        roomId: roomId,
                        messageCount: messages.length,
                        lastMessage: messages.length > 0 ? messages[messages.length - 1] : null,
                        cacheSize: JSON.stringify(messages).length
                    });
                }
            }
        } catch (error) {
            console.warn('获取房间缓存信息失败:', error);
        }

        return roomCaches;
    }

    /**
     * 清空所有缓存
     */
    clearAllCache() {
        try {
            const keysToRemove = [];
            
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith(this.prefix)) {
                    keysToRemove.push(key);
                }
            }

            keysToRemove.forEach(key => {
                localStorage.removeItem(key);
            });

            console.log(`清空了 ${keysToRemove.length} 个缓存项`);
            return true;

        } catch (error) {
            console.error('清空缓存失败:', error);
            return false;
        }
    }

    /**
     * 获取统计信息
     * @returns {Object} 统计信息
     */
    getStats() {
        const storageSize = this.getCurrentStorageSize();
        const roomCaches = this.getAllRoomCacheInfo();

        return {
            ...this.stats,
            storageSize: this.formatBytes(storageSize),
            storageSizeBytes: storageSize,
            maxSize: this.formatBytes(this.maxTotalSize),
            usagePercentage: ((storageSize / this.maxTotalSize) * 100).toFixed(2) + '%',
            roomCount: roomCaches.length,
            totalMessages: roomCaches.reduce((sum, room) => sum + room.messageCount, 0)
        };
    }

    /**
     * 格式化字节数
     * @param {number} bytes - 字节数
     * @returns {string} 格式化的字符串
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 调试信息
     * @returns {Object} 调试信息
     */
    debug() {
        return {
            stats: this.getStats(),
            roomCaches: this.getAllRoomCacheInfo(),
            settings: {
                prefix: this.prefix,
                maxRecentMessages: this.maxRecentMessages,
                maxTotalSize: this.formatBytes(this.maxTotalSize),
                compressionEnabled: this.compressionEnabled
            }
        };
    }
}

// 导出类
window.LocalStorageManager = LocalStorageManager;

console.log('✅ localStorage管理器已加载');
