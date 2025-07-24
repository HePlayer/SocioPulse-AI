/**
 * 主存储管理器
 * 统一管理IndexedDB、localStorage和内存缓存
 */

class StorageManager {
    constructor() {
        this.indexedDB = new IndexedDBManager();
        this.localStorage = new LocalStorageManager();
        this.memoryCache = new MemoryCache();
        this.eventBus = new EventBus();
        
        this.initialized = false;
        this.enabled = true;
        this.fallbackMode = false;
        
        // 配置选项
        this.config = {
            enableIndexedDB: true,
            enableLocalStorage: true,
            enableMemoryCache: true,
            batchSaveEnabled: true,
            batchSaveDelay: 100, // 100ms延迟批量保存
            maxRetries: 3
        };

        // 批量保存队列
        this.saveQueue = [];
        this.batchTimer = null;
        this.isProcessingBatch = false;

        // 统计信息
        this.stats = {
            totalSaves: 0,
            totalLoads: 0,
            cacheHits: 0,
            cacheMisses: 0,
            errors: 0,
            batchSaves: 0
        };
    }

    /**
     * 初始化存储管理器
     * @returns {Promise<boolean>} 是否初始化成功
     */
    async initialize() {
        if (this.initialized) {
            return true;
        }

        console.log('🚀 初始化存储管理器...');

        try {
            // 检测浏览器支持
            const support = this.detectBrowserSupport();
            console.log('浏览器支持情况:', support);

            // 初始化IndexedDB
            if (this.config.enableIndexedDB && support.indexedDB) {
                try {
                    await this.indexedDB.initialize();
                    console.log('✅ IndexedDB初始化成功');
                } catch (error) {
                    console.warn('⚠️ IndexedDB初始化失败，禁用IndexedDB:', error);
                    this.config.enableIndexedDB = false;
                }
            }

            // 检查localStorage支持
            if (this.config.enableLocalStorage && !support.localStorage) {
                console.warn('⚠️ localStorage不可用，禁用localStorage缓存');
                this.config.enableLocalStorage = false;
            }

            // 设置错误处理
            this.setupErrorHandling();

            // 设置事件监听
            this.setupEventListeners();

            this.initialized = true;
            this.eventBus.emit('storageInitialized', {
                support,
                config: this.config
            });

            console.log('✅ 存储管理器初始化完成');
            return true;

        } catch (error) {
            console.error('❌ 存储管理器初始化失败:', error);
            this.fallbackMode = true;
            this.stats.errors++;
            return false;
        }
    }

    /**
     * 保存消息（主要入口）
     * @param {Object} message - 消息对象
     * @returns {Promise<Object>} 保存后的消息对象
     */
    async saveMessage(message) {
        if (!this.enabled) {
            return message;
        }

        try {
            // 验证和标准化消息数据
            const validatedMessage = MessageModel.validate(message);
            
            // 立即存储到内存缓存
            if (this.config.enableMemoryCache) {
                this.memoryCache.addMessage(validatedMessage);
                this.stats.cacheHits++;
            }

            // 更新localStorage缓存
            if (this.config.enableLocalStorage) {
                this.localStorage.updateRecentMessages(validatedMessage);
            }

            // 添加到批量保存队列或立即保存
            if (this.config.batchSaveEnabled) {
                this.addToBatchQueue(validatedMessage);
            } else {
                await this.saveToIndexedDB(validatedMessage);
            }

            // 更新房间活动时间
            await this.updateRoomActivity(validatedMessage.roomId);

            // 触发事件
            this.eventBus.emit('messageSaved', validatedMessage);
            this.stats.totalSaves++;

            return validatedMessage;

        } catch (error) {
            console.error('保存消息失败:', error);
            this.handleSaveError(message, error);
            throw error;
        }
    }

    /**
     * 批量保存消息
     * @param {Array} messages - 消息数组
     * @returns {Promise<number>} 成功保存的消息数量
     */
    async saveMessages(messages) {
        if (!Array.isArray(messages) || messages.length === 0) {
            return 0;
        }

        let successCount = 0;

        try {
            // 验证所有消息
            const validatedMessages = messages.map(msg => MessageModel.validate(msg));

            // 批量添加到内存缓存
            if (this.config.enableMemoryCache) {
                successCount += this.memoryCache.addMessages(validatedMessages);
            }

            // 批量更新localStorage
            if (this.config.enableLocalStorage) {
                this.localStorage.updateRecentMessagesBatch(validatedMessages);
            }

            // 批量保存到IndexedDB
            if (this.config.enableIndexedDB) {
                const dbSaveCount = await this.indexedDB.saveMessages(validatedMessages);
                successCount = Math.max(successCount, dbSaveCount);
            }

            // 触发批量保存事件
            this.eventBus.emit('messagesBatchSaved', {
                count: successCount,
                messages: validatedMessages
            });

            this.stats.totalSaves += successCount;
            this.stats.batchSaves++;

            return successCount;

        } catch (error) {
            console.error('批量保存消息失败:', error);
            this.stats.errors++;
            return successCount;
        }
    }

    /**
     * 加载房间消息
     * @param {string} roomId - 房间ID
     * @param {number} limit - 限制数量
     * @param {number} offset - 偏移量
     * @returns {Promise<Array>} 消息数组
     */
    async loadRoomMessages(roomId, limit = 50, offset = 0) {
        if (!roomId) {
            return [];
        }

        try {
            this.stats.totalLoads++;

            // 1. 优先从内存缓存获取
            if (this.config.enableMemoryCache) {
                const cachedMessages = this.memoryCache.getRoomMessages(roomId, limit, offset);
                if (cachedMessages.length > 0) {
                    this.stats.cacheHits++;
                    console.log(`从内存缓存加载 ${cachedMessages.length} 条消息`);
                    return cachedMessages;
                }
            }

            // 2. 从localStorage快速缓存获取
            let messages = [];
            if (this.config.enableLocalStorage) {
                const recentMessages = this.localStorage.getRecentMessages(roomId);
                if (recentMessages.length > 0) {
                    messages = recentMessages;
                    
                    // 预加载到内存缓存
                    if (this.config.enableMemoryCache) {
                        this.memoryCache.addMessages(messages);
                    }
                    
                    console.log(`从localStorage缓存加载 ${messages.length} 条消息`);
                }
            }

            // 3. 从IndexedDB获取完整历史
            if (this.config.enableIndexedDB) {
                try {
                    const dbMessages = await this.indexedDB.getMessagesByRoom(roomId, limit, offset);
                    
                    if (dbMessages.length > 0) {
                        // 合并并去重消息
                        const allMessages = this.mergeAndDeduplicateMessages(messages, dbMessages);
                        
                        // 更新缓存
                        if (this.config.enableMemoryCache) {
                            this.memoryCache.addMessages(allMessages);
                        }
                        
                        if (this.config.enableLocalStorage) {
                            this.localStorage.updateRecentMessagesBatch(allMessages);
                        }
                        
                        messages = allMessages;
                        console.log(`从IndexedDB加载 ${dbMessages.length} 条消息，合并后共 ${messages.length} 条`);
                    }
                } catch (error) {
                    console.warn('从IndexedDB加载消息失败:', error);
                    this.stats.errors++;
                }
            }

            // 应用分页
            const pagedMessages = messages.slice(offset, offset + limit);
            
            if (pagedMessages.length === 0) {
                this.stats.cacheMisses++;
            } else {
                this.stats.cacheHits++;
            }

            // 触发加载完成事件
            this.eventBus.emit('messagesLoaded', {
                roomId,
                count: pagedMessages.length,
                total: messages.length
            });

            return pagedMessages;

        } catch (error) {
            console.error('加载房间消息失败:', error);
            this.stats.errors++;
            return [];
        }
    }

    /**
     * 删除房间及其所有数据
     * @param {string} roomId - 房间ID
     * @returns {Promise<boolean>} 是否成功删除
     */
    async deleteRoom(roomId) {
        if (!roomId) {
            return false;
        }

        try {
            let success = true;

            // 从内存缓存删除
            if (this.config.enableMemoryCache) {
                this.memoryCache.clearRoom(roomId);
            }

            // 从localStorage删除
            if (this.config.enableLocalStorage) {
                this.localStorage.clearRoomCache(roomId);
            }

            // 从IndexedDB删除
            if (this.config.enableIndexedDB) {
                try {
                    await this.indexedDB.deleteRoom(roomId);
                } catch (error) {
                    console.error('从IndexedDB删除房间失败:', error);
                    success = false;
                }
            }

            // 触发删除事件
            this.eventBus.emit('roomDeleted', { roomId, success });

            console.log(`房间 ${roomId} 删除${success ? '成功' : '部分失败'}`);
            return success;

        } catch (error) {
            console.error('删除房间失败:', error);
            this.stats.errors++;
            return false;
        }
    }

    /**
     * 搜索消息
     * @param {string} query - 搜索关键词
     * @param {string} roomId - 房间ID（可选）
     * @param {number} limit - 限制数量
     * @returns {Promise<Array>} 匹配的消息
     */
    async searchMessages(query, roomId = null, limit = 20) {
        if (!query) {
            return [];
        }

        try {
            let results = [];

            // 1. 先在内存缓存中搜索
            if (this.config.enableMemoryCache) {
                const cacheResults = this.memoryCache.searchMessages(query, roomId, limit);
                results = results.concat(cacheResults);
            }

            // 2. 在IndexedDB中搜索更多结果
            if (this.config.enableIndexedDB && results.length < limit) {
                try {
                    const dbResults = await this.indexedDB.searchMessages(
                        query, 
                        roomId, 
                        limit - results.length
                    );
                    
                    // 合并结果并去重
                    results = this.mergeAndDeduplicateMessages(results, dbResults);
                } catch (error) {
                    console.warn('IndexedDB搜索失败:', error);
                }
            }

            // 按相关性和时间排序
            results.sort((a, b) => {
                // 简单的相关性评分：关键词出现次数
                const scoreA = (a.content.toLowerCase().match(new RegExp(query.toLowerCase(), 'g')) || []).length;
                const scoreB = (b.content.toLowerCase().match(new RegExp(query.toLowerCase(), 'g')) || []).length;
                
                if (scoreA !== scoreB) {
                    return scoreB - scoreA; // 相关性高的在前
                }
                
                // 相关性相同时按时间排序
                return new Date(b.timestamp) - new Date(a.timestamp);
            });

            return results.slice(0, limit);

        } catch (error) {
            console.error('搜索消息失败:', error);
            this.stats.errors++;
            return [];
        }
    }

    /**
     * 添加到批量保存队列
     * @param {Object} message - 消息对象
     * @private
     */
    addToBatchQueue(message) {
        this.saveQueue.push(message);
        
        // 设置延迟批量处理
        if (!this.batchTimer) {
            this.batchTimer = setTimeout(() => {
                this.processBatchQueue();
            }, this.config.batchSaveDelay);
        }
    }

    /**
     * 处理批量保存队列
     * @private
     */
    async processBatchQueue() {
        if (this.isProcessingBatch || this.saveQueue.length === 0) {
            return;
        }

        this.isProcessingBatch = true;
        this.batchTimer = null;

        const messagesToSave = [...this.saveQueue];
        this.saveQueue = [];

        try {
            if (this.config.enableIndexedDB) {
                await this.indexedDB.saveMessages(messagesToSave);
                console.log(`批量保存 ${messagesToSave.length} 条消息到IndexedDB`);
            }
        } catch (error) {
            console.error('批量保存失败:', error);
            this.stats.errors++;
            
            // 失败的消息重新加入队列
            this.saveQueue.unshift(...messagesToSave);
        } finally {
            this.isProcessingBatch = false;
            
            // 如果队列中还有消息，继续处理
            if (this.saveQueue.length > 0) {
                this.batchTimer = setTimeout(() => {
                    this.processBatchQueue();
                }, this.config.batchSaveDelay);
            }
        }
    }

    /**
     * 保存到IndexedDB
     * @param {Object} message - 消息对象
     * @private
     */
    async saveToIndexedDB(message) {
        if (!this.config.enableIndexedDB) {
            return;
        }

        try {
            await this.indexedDB.saveMessage(message);
        } catch (error) {
            console.error('保存到IndexedDB失败:', error);
            this.stats.errors++;
            throw error;
        }
    }

    /**
     * 更新房间活动时间
     * @param {string} roomId - 房间ID
     * @private
     */
    async updateRoomActivity(roomId) {
        if (!this.config.enableIndexedDB) {
            return;
        }

        try {
            // 获取现有房间信息
            let room = await this.indexedDB.getRoom(roomId);
            
            if (!room) {
                // 创建新房间记录
                room = RoomModel.create({
                    roomId: roomId,
                    roomName: `房间 ${roomId.substring(0, 8)}`,
                    lastActivity: new Date().toISOString(),
                    messageCount: 1
                });
            } else {
                // 更新现有房间
                room.lastActivity = new Date().toISOString();
                room.messageCount = (room.messageCount || 0) + 1;
            }

            await this.indexedDB.saveRoom(room);

        } catch (error) {
            console.warn('更新房间活动时间失败:', error);
        }
    }

    /**
     * 合并并去重消息
     * @param {Array} existing - 现有消息
     * @param {Array} newMessages - 新消息
     * @returns {Array} 合并后的消息
     * @private
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

        // 转换为数组并按时间排序
        const merged = Array.from(messageMap.values());
        merged.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        return merged;
    }

    /**
     * 检测浏览器支持
     * @returns {Object} 支持情况
     * @private
     */
    detectBrowserSupport() {
        return {
            indexedDB: 'indexedDB' in window,
            localStorage: (() => {
                try {
                    const test = '__storage_test__';
                    localStorage.setItem(test, test);
                    localStorage.removeItem(test);
                    return true;
                } catch (e) {
                    return false;
                }
            })(),
            webWorker: 'Worker' in window
        };
    }

    /**
     * 设置错误处理
     * @private
     */
    setupErrorHandling() {
        // 监听IndexedDB错误
        this.eventBus.on('indexedDBError', (error) => {
            console.error('IndexedDB错误:', error);
            this.stats.errors++;
            
            // 严重错误时切换到降级模式
            if (error.name === 'QuotaExceededError') {
                this.enableFallbackMode();
            }
        });

        // 监听localStorage错误
        this.eventBus.on('localStorageError', (error) => {
            console.error('localStorage错误:', error);
            this.stats.errors++;
        });
    }

    /**
     * 设置事件监听
     * @private
     */
    setupEventListeners() {
        // 页面卸载时保存待处理的消息
        window.addEventListener('beforeunload', () => {
            if (this.saveQueue.length > 0) {
                // 同步保存剩余消息
                this.processBatchQueue();
            }
        });

        // 页面可见性变化时的处理
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.saveQueue.length > 0) {
                // 页面隐藏时立即处理队列
                this.processBatchQueue();
            }
        });
    }

    /**
     * 启用降级模式
     * @private
     */
    enableFallbackMode() {
        console.warn('⚠️ 启用存储降级模式');
        this.fallbackMode = true;
        this.config.enableIndexedDB = false;
        this.config.batchSaveEnabled = false;
        
        this.eventBus.emit('fallbackModeEnabled');
    }

    /**
     * 处理保存错误
     * @param {Object} message - 原始消息
     * @param {Error} error - 错误对象
     * @private
     */
    handleSaveError(message, error) {
        this.stats.errors++;
        
        console.error('消息保存错误:', {
            messageId: message.id,
            error: error.message,
            stack: error.stack
        });

        // 触发错误事件
        this.eventBus.emit('saveError', {
            message,
            error,
            timestamp: new Date().toISOString()
        });
    }

    /**
     * 获取统计信息
     * @returns {Promise<Object>} 统计信息
     */
    async getStats() {
        const baseStats = { ...this.stats };

        try {
            // 获取各组件的统计信息
            if (this.config.enableMemoryCache) {
                baseStats.memoryCache = this.memoryCache.getStats();
            }

            if (this.config.enableLocalStorage) {
                baseStats.localStorage = this.localStorage.getStats();
            }

            if (this.config.enableIndexedDB) {
                baseStats.indexedDB = await this.indexedDB.getStats();
            }

            baseStats.config = this.config;
            baseStats.initialized = this.initialized;
            baseStats.fallbackMode = this.fallbackMode;
            baseStats.queueSize = this.saveQueue.length;

            return baseStats;

        } catch (error) {
            console.error('获取统计信息失败:', error);
            return { ...baseStats, error: error.message };
        }
    }

    /**
     * 清空所有存储数据
     * @returns {Promise<boolean>} 是否成功
     */
    async clearAllData() {
        try {
            let success = true;

            // 清空内存缓存
            if (this.config.enableMemoryCache) {
                this.memoryCache.clear();
            }

            // 清空localStorage
            if (this.config.enableLocalStorage) {
                this.localStorage.clearAllCache();
            }

            // 清空IndexedDB
            if (this.config.enableIndexedDB) {
                const dbSuccess = await this.indexedDB.clearAllData();
                success = success && dbSuccess;
            }

            // 清空保存队列
            this.saveQueue = [];
            if (this.batchTimer) {
                clearTimeout(this.batchTimer);
                this.batchTimer = null;
            }

            // 重置统计信息
            this.stats = {
                totalSaves: 0,
                totalLoads: 0,
                cacheHits: 0,
                cacheMisses: 0,
                errors: 0,
                batchSaves: 0
            };

            this.eventBus.emit('allDataCleared', { success });
            console.log('✅ 所有存储数据已清空');

            return success;

        } catch (error) {
            console.error('清空数据失败:', error);
            return false;
        }
    }

    /**
     * 启用/禁用存储功能
     * @param {boolean} enabled - 是否启用
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        console.log(`存储功能已${enabled ? '启用' : '禁用'}`);
        
        this.eventBus.emit('storageToggled', { enabled });
    }

    /**
     * 获取调试信息
     * @returns {Promise<Object>} 调试信息
     */
    async debug() {
        try {
            const stats = await this.getStats();
            
            return {
                stats,
                config: this.config,
                state: {
                    initialized: this.initialized,
                    enabled: this.enabled,
                    fallbackMode: this.fallbackMode,
                    queueSize: this.saveQueue.length,
                    isProcessingBatch: this.isProcessingBatch
                },
                components: {
                    memoryCache: this.config.enableMemoryCache ? this.memoryCache.debug() : null,
                    localStorage: this.config.enableLocalStorage ? this.localStorage.debug() : null,
                    indexedDB: this.config.enableIndexedDB ? await this.indexedDB.debug() : null
                },
                events: this.eventBus.debug()
            };

        } catch (error) {
            return {
                error: error.message,
                initialized: this.initialized
            };
        }
    }
}

// 创建全局存储管理器实例
const globalStorageManager = new StorageManager();

// 导出类和全局实例
window.StorageManager = StorageManager;
window.globalStorageManager = globalStorageManager;

console.log('✅ 主存储管理器已加载');
