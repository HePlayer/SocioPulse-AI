/**
 * 内存缓存管理器
 * 实现LRU缓存策略，提供高速的消息访问
 */

class MemoryCache {
    constructor(maxSize = 1000) {
        this.maxSize = maxSize;
        this.cache = new Map(); // 全局消息缓存 messageId -> message
        this.roomMessages = new Map(); // 房间消息列表 roomId -> messages[]
        this.accessOrder = new Map(); // 访问顺序记录 messageId -> timestamp
        this.stats = {
            hits: 0,
            misses: 0,
            evictions: 0
        };
    }

    /**
     * 添加消息到缓存
     * @param {Object} message - 消息对象
     */
    addMessage(message) {
        if (!message || !message.id || !message.roomId) {
            console.warn('无效的消息数据，跳过缓存');
            return false;
        }

        try {
            // 添加到全局缓存
            this.cache.set(message.id, message);
            this.accessOrder.set(message.id, Date.now());

            // 添加到房间消息列表
            if (!this.roomMessages.has(message.roomId)) {
                this.roomMessages.set(message.roomId, []);
            }

            const roomMsgs = this.roomMessages.get(message.roomId);
            
            // 检查是否已存在（避免重复）
            const existingIndex = roomMsgs.findIndex(msg => msg.id === message.id);
            if (existingIndex === -1) {
                roomMsgs.push(message);
                
                // 按时间戳排序
                roomMsgs.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            } else {
                // 更新现有消息
                roomMsgs[existingIndex] = message;
            }

            // 维护缓存大小
            this.maintainCacheSize();

            return true;
        } catch (error) {
            console.error('添加消息到缓存失败:', error);
            return false;
        }
    }

    /**
     * 批量添加消息
     * @param {Array} messages - 消息数组
     */
    addMessages(messages) {
        if (!Array.isArray(messages)) {
            return false;
        }

        let successCount = 0;
        messages.forEach(message => {
            if (this.addMessage(message)) {
                successCount++;
            }
        });

        return successCount;
    }

    /**
     * 获取单个消息
     * @param {string} messageId - 消息ID
     * @returns {Object|null} 消息对象
     */
    getMessage(messageId) {
        if (this.cache.has(messageId)) {
            this.stats.hits++;
            this.accessOrder.set(messageId, Date.now()); // 更新访问时间
            return this.cache.get(messageId);
        }

        this.stats.misses++;
        return null;
    }

    /**
     * 获取房间的所有消息
     * @param {string} roomId - 房间ID
     * @param {number} limit - 限制数量
     * @param {number} offset - 偏移量
     * @returns {Array} 消息数组
     */
    getRoomMessages(roomId, limit = 50, offset = 0) {
        if (!this.roomMessages.has(roomId)) {
            this.stats.misses++;
            return [];
        }

        this.stats.hits++;
        const messages = this.roomMessages.get(roomId);
        
        // 应用分页
        const start = Math.max(0, offset);
        const end = limit > 0 ? start + limit : messages.length;
        
        return messages.slice(start, end);
    }

    /**
     * 获取房间的最新消息
     * @param {string} roomId - 房间ID
     * @param {number} count - 消息数量
     * @returns {Array} 最新消息数组
     */
    getRecentRoomMessages(roomId, count = 10) {
        if (!this.roomMessages.has(roomId)) {
            return [];
        }

        const messages = this.roomMessages.get(roomId);
        return messages.slice(-count); // 获取最后N条消息
    }

    /**
     * 清理房间缓存
     * @param {string} roomId - 房间ID
     */
    clearRoom(roomId) {
        if (!this.roomMessages.has(roomId)) {
            return false;
        }

        const messages = this.roomMessages.get(roomId);
        
        // 从全局缓存中移除消息
        messages.forEach(msg => {
            this.cache.delete(msg.id);
            this.accessOrder.delete(msg.id);
        });

        // 移除房间消息列表
        this.roomMessages.delete(roomId);

        return true;
    }

    /**
     * 删除单个消息
     * @param {string} messageId - 消息ID
     * @param {string} roomId - 房间ID（可选，用于优化）
     */
    deleteMessage(messageId, roomId = null) {
        // 从全局缓存删除
        const deleted = this.cache.delete(messageId);
        this.accessOrder.delete(messageId);

        // 从房间消息列表删除
        if (roomId && this.roomMessages.has(roomId)) {
            const messages = this.roomMessages.get(roomId);
            const index = messages.findIndex(msg => msg.id === messageId);
            if (index !== -1) {
                messages.splice(index, 1);
            }
        } else {
            // 如果没有指定房间ID，遍历所有房间
            for (const [rId, messages] of this.roomMessages.entries()) {
                const index = messages.findIndex(msg => msg.id === messageId);
                if (index !== -1) {
                    messages.splice(index, 1);
                    break;
                }
            }
        }

        return deleted;
    }

    /**
     * 维护缓存大小（LRU策略）
     */
    maintainCacheSize() {
        if (this.cache.size <= this.maxSize) {
            return;
        }

        // 获取最少使用的消息
        const sortedByAccess = Array.from(this.accessOrder.entries())
            .sort((a, b) => a[1] - b[1]); // 按访问时间排序

        const toEvict = sortedByAccess.slice(0, this.cache.size - this.maxSize);

        toEvict.forEach(([messageId]) => {
            const message = this.cache.get(messageId);
            if (message) {
                this.deleteMessage(messageId, message.roomId);
                this.stats.evictions++;
            }
        });
    }

    /**
     * 检查消息是否存在
     * @param {string} messageId - 消息ID
     * @returns {boolean} 是否存在
     */
    hasMessage(messageId) {
        return this.cache.has(messageId);
    }

    /**
     * 检查房间是否有缓存
     * @param {string} roomId - 房间ID
     * @returns {boolean} 是否有缓存
     */
    hasRoom(roomId) {
        return this.roomMessages.has(roomId);
    }

    /**
     * 获取房间消息数量
     * @param {string} roomId - 房间ID
     * @returns {number} 消息数量
     */
    getRoomMessageCount(roomId) {
        if (!this.roomMessages.has(roomId)) {
            return 0;
        }
        return this.roomMessages.get(roomId).length;
    }

    /**
     * 搜索消息
     * @param {string} query - 搜索关键词
     * @param {string} roomId - 房间ID（可选）
     * @param {number} limit - 限制数量
     * @returns {Array} 匹配的消息
     */
    searchMessages(query, roomId = null, limit = 20) {
        if (!query || typeof query !== 'string') {
            return [];
        }

        const searchTerm = query.toLowerCase();
        const results = [];

        const searchInMessages = (messages) => {
            return messages.filter(msg => {
                return msg.content && 
                       msg.content.toLowerCase().includes(searchTerm);
            });
        };

        if (roomId) {
            // 在指定房间搜索
            if (this.roomMessages.has(roomId)) {
                const roomResults = searchInMessages(this.roomMessages.get(roomId));
                results.push(...roomResults);
            }
        } else {
            // 在所有房间搜索
            for (const messages of this.roomMessages.values()) {
                const roomResults = searchInMessages(messages);
                results.push(...roomResults);
                
                if (results.length >= limit) {
                    break;
                }
            }
        }

        return results.slice(0, limit);
    }

    /**
     * 清空所有缓存
     */
    clear() {
        this.cache.clear();
        this.roomMessages.clear();
        this.accessOrder.clear();
        this.stats = {
            hits: 0,
            misses: 0,
            evictions: 0
        };
    }

    /**
     * 获取缓存统计信息
     * @returns {Object} 统计信息
     */
    getStats() {
        const totalRequests = this.stats.hits + this.stats.misses;
        const hitRate = totalRequests > 0 ? (this.stats.hits / totalRequests * 100).toFixed(2) : 0;

        return {
            ...this.stats,
            totalRequests,
            hitRate: `${hitRate}%`,
            cacheSize: this.cache.size,
            maxSize: this.maxSize,
            roomCount: this.roomMessages.size,
            memoryUsage: this.estimateMemoryUsage()
        };
    }

    /**
     * 估算内存使用量
     * @returns {string} 内存使用量（格式化字符串）
     */
    estimateMemoryUsage() {
        let totalSize = 0;
        
        // 估算消息数据大小
        for (const message of this.cache.values()) {
            totalSize += JSON.stringify(message).length * 2; // 粗略估算（UTF-16）
        }

        // 转换为可读格式
        if (totalSize < 1024) {
            return `${totalSize} B`;
        } else if (totalSize < 1024 * 1024) {
            return `${(totalSize / 1024).toFixed(2)} KB`;
        } else {
            return `${(totalSize / (1024 * 1024)).toFixed(2)} MB`;
        }
    }

    /**
     * 获取调试信息
     * @returns {Object} 调试信息
     */
    debug() {
        const roomInfo = {};
        for (const [roomId, messages] of this.roomMessages.entries()) {
            roomInfo[roomId] = {
                messageCount: messages.length,
                firstMessage: messages[0]?.timestamp,
                lastMessage: messages[messages.length - 1]?.timestamp
            };
        }

        return {
            stats: this.getStats(),
            rooms: roomInfo,
            recentAccess: Array.from(this.accessOrder.entries())
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([id, time]) => ({
                    messageId: id,
                    accessTime: new Date(time).toISOString()
                }))
        };
    }

    /**
     * 预热缓存
     * @param {Array} messages - 预加载的消息
     */
    preload(messages) {
        if (!Array.isArray(messages)) {
            return false;
        }

        console.log(`预加载 ${messages.length} 条消息到缓存`);
        return this.addMessages(messages);
    }
}

// 导出类
window.MemoryCache = MemoryCache;

console.log('✅ 内存缓存管理器已加载');
