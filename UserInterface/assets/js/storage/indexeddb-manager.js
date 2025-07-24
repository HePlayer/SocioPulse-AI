/**
 * IndexedDB管理器
 * 提供持久化存储和高级查询功能
 */

class IndexedDBManager {
    constructor() {
        this.dbName = 'SocioPulseDB';
        this.version = 1;
        this.db = null;
        this.isInitialized = false;
        this.initPromise = null;
        this.stats = {
            reads: 0,
            writes: 0,
            deletes: 0,
            errors: 0
        };
    }

    /**
     * 初始化数据库
     * @returns {Promise<IDBDatabase>} 数据库实例
     */
    async initialize() {
        if (this.isInitialized && this.db) {
            return this.db;
        }

        if (this.initPromise) {
            return this.initPromise;
        }

        this.initPromise = new Promise((resolve, reject) => {
            // 检查浏览器支持
            if (!('indexedDB' in window)) {
                reject(new Error('浏览器不支持IndexedDB'));
                return;
            }

            const request = indexedDB.open(this.dbName, this.version);

            request.onerror = () => {
                console.error('IndexedDB打开失败:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                this.isInitialized = true;
                
                // 设置错误处理
                this.db.onerror = (event) => {
                    console.error('IndexedDB错误:', event.target.error);
                    this.stats.errors++;
                };

                console.log('✅ IndexedDB初始化成功');
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                console.log('升级IndexedDB数据库...');
                this.createObjectStores(db);
            };
        });

        return this.initPromise;
    }

    /**
     * 创建对象存储
     * @param {IDBDatabase} db - 数据库实例
     */
    createObjectStores(db) {
        try {
            // 创建消息存储
            if (!db.objectStoreNames.contains('messages')) {
                const messageStore = db.createObjectStore('messages', { keyPath: 'id' });
                
                // 创建索引
                messageStore.createIndex('roomId', 'roomId', { unique: false });
                messageStore.createIndex('timestamp', 'timestamp', { unique: false });
                messageStore.createIndex('sender', 'sender', { unique: false });
                messageStore.createIndex('roomId_timestamp', ['roomId', 'timestamp'], { unique: false });
                
                console.log('创建消息存储和索引');
            }

            // 创建房间存储
            if (!db.objectStoreNames.contains('rooms')) {
                const roomStore = db.createObjectStore('rooms', { keyPath: 'roomId' });
                
                // 创建索引
                roomStore.createIndex('createdAt', 'createdAt', { unique: false });
                roomStore.createIndex('lastActivity', 'lastActivity', { unique: false });
                roomStore.createIndex('roomName', 'roomName', { unique: false });
                
                console.log('创建房间存储和索引');
            }

            // 创建设置存储
            if (!db.objectStoreNames.contains('settings')) {
                const settingsStore = db.createObjectStore('settings', { keyPath: 'key' });
                console.log('创建设置存储');
            }

            // 创建扩展数据存储
            if (!db.objectStoreNames.contains('extensions')) {
                const extStore = db.createObjectStore('extensions', { keyPath: 'id' });
                
                // 创建索引
                extStore.createIndex('type', 'type', { unique: false });
                extStore.createIndex('roomId', 'roomId', { unique: false });
                extStore.createIndex('timestamp', 'timestamp', { unique: false });
                
                console.log('创建扩展数据存储和索引');
            }

        } catch (error) {
            console.error('创建对象存储失败:', error);
            throw error;
        }
    }

    /**
     * 保存消息
     * @param {Object} message - 消息对象
     * @returns {Promise<string>} 消息ID
     */
    async saveMessage(message) {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readwrite');
            const store = transaction.objectStore('messages');

            // 确保消息有时间戳
            if (!message.timestamp) {
                message.timestamp = new Date().toISOString();
            }

            const request = store.put(message); // 使用put而不是add，允许更新

            request.onsuccess = () => {
                this.stats.writes++;
                resolve(request.result);
            };

            request.onerror = () => {
                this.stats.errors++;
                console.error('保存消息失败:', request.error);
                reject(request.error);
            };

            transaction.onerror = () => {
                this.stats.errors++;
                console.error('消息保存事务失败:', transaction.error);
                reject(transaction.error);
            };
        });
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

        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readwrite');
            const store = transaction.objectStore('messages');
            
            let successCount = 0;
            let errorCount = 0;

            const saveNext = (index) => {
                if (index >= messages.length) {
                    if (errorCount > 0) {
                        console.warn(`批量保存完成，成功: ${successCount}, 失败: ${errorCount}`);
                    }
                    this.stats.writes += successCount;
                    this.stats.errors += errorCount;
                    resolve(successCount);
                    return;
                }

                const message = messages[index];
                if (!message.timestamp) {
                    message.timestamp = new Date().toISOString();
                }

                const request = store.put(message);
                
                request.onsuccess = () => {
                    successCount++;
                    saveNext(index + 1);
                };

                request.onerror = () => {
                    errorCount++;
                    console.warn(`保存消息失败 (${index}):`, request.error);
                    saveNext(index + 1);
                };
            };

            transaction.onerror = () => {
                this.stats.errors++;
                reject(transaction.error);
            };

            saveNext(0);
        });
    }

    /**
     * 获取房间消息
     * @param {string} roomId - 房间ID
     * @param {number} limit - 限制数量
     * @param {number} offset - 偏移量
     * @returns {Promise<Array>} 消息数组
     */
    async getMessagesByRoom(roomId, limit = 50, offset = 0) {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readonly');
            const store = transaction.objectStore('messages');
            const index = store.index('roomId_timestamp');

            const messages = [];
            let count = 0;
            let skipped = 0;

            // 使用复合索引进行高效查询
            const range = IDBKeyRange.bound([roomId, ''], [roomId, '\uffff']);
            const request = index.openCursor(range);

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                
                if (cursor && count < limit) {
                    if (skipped >= offset) {
                        messages.push(cursor.value);
                        count++;
                    } else {
                        skipped++;
                    }
                    cursor.continue();
                } else {
                    this.stats.reads++;
                    // 按时间戳排序（确保顺序正确）
                    messages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                    resolve(messages);
                }
            };

            request.onerror = () => {
                this.stats.errors++;
                console.error('查询房间消息失败:', request.error);
                reject(request.error);
            };
        });
    }

    /**
     * 获取房间最新消息
     * @param {string} roomId - 房间ID
     * @param {number} count - 消息数量
     * @returns {Promise<Array>} 最新消息数组
     */
    async getRecentMessagesByRoom(roomId, count = 10) {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readonly');
            const store = transaction.objectStore('messages');
            const index = store.index('roomId_timestamp');

            const messages = [];
            const range = IDBKeyRange.bound([roomId, ''], [roomId, '\uffff']);
            
            // 倒序遍历获取最新消息
            const request = index.openCursor(range, 'prev');

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                
                if (cursor && messages.length < count) {
                    messages.unshift(cursor.value); // 插入到数组开头保持时间顺序
                    cursor.continue();
                } else {
                    this.stats.reads++;
                    resolve(messages);
                }
            };

            request.onerror = () => {
                this.stats.errors++;
                reject(request.error);
            };
        });
    }

    /**
     * 删除房间的所有消息
     * @param {string} roomId - 房间ID
     * @returns {Promise<number>} 删除的消息数量
     */
    async deleteMessagesByRoom(roomId) {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readwrite');
            const store = transaction.objectStore('messages');
            const index = store.index('roomId');

            let deleteCount = 0;
            const range = IDBKeyRange.only(roomId);
            const request = index.openCursor(range);

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                
                if (cursor) {
                    cursor.delete();
                    deleteCount++;
                    cursor.continue();
                } else {
                    this.stats.deletes += deleteCount;
                    console.log(`删除了房间 ${roomId} 的 ${deleteCount} 条消息`);
                    resolve(deleteCount);
                }
            };

            request.onerror = () => {
                this.stats.errors++;
                reject(request.error);
            };
        });
    }

    /**
     * 保存房间信息
     * @param {Object} room - 房间对象
     * @returns {Promise<string>} 房间ID
     */
    async saveRoom(room) {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['rooms'], 'readwrite');
            const store = transaction.objectStore('rooms');

            // 更新最后活动时间
            room.lastActivity = new Date().toISOString();

            const request = store.put(room);

            request.onsuccess = () => {
                this.stats.writes++;
                resolve(request.result);
            };

            request.onerror = () => {
                this.stats.errors++;
                reject(request.error);
            };
        });
    }

    /**
     * 获取房间信息
     * @param {string} roomId - 房间ID
     * @returns {Promise<Object|null>} 房间对象
     */
    async getRoom(roomId) {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['rooms'], 'readonly');
            const store = transaction.objectStore('rooms');
            const request = store.get(roomId);

            request.onsuccess = () => {
                this.stats.reads++;
                resolve(request.result || null);
            };

            request.onerror = () => {
                this.stats.errors++;
                reject(request.error);
            };
        });
    }

    /**
     * 获取所有房间
     * @returns {Promise<Array>} 房间数组
     */
    async getAllRooms() {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['rooms'], 'readonly');
            const store = transaction.objectStore('rooms');
            const request = store.getAll();

            request.onsuccess = () => {
                this.stats.reads++;
                resolve(request.result || []);
            };

            request.onerror = () => {
                this.stats.errors++;
                reject(request.error);
            };
        });
    }

    /**
     * 删除房间
     * @param {string} roomId - 房间ID
     * @returns {Promise<boolean>} 是否成功删除
     */
    async deleteRoom(roomId) {
        await this.ensureInitialized();

        try {
            // 先删除房间的所有消息
            await this.deleteMessagesByRoom(roomId);

            // 再删除房间信息
            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction(['rooms'], 'readwrite');
                const store = transaction.objectStore('rooms');
                const request = store.delete(roomId);

                request.onsuccess = () => {
                    this.stats.deletes++;
                    resolve(true);
                };

                request.onerror = () => {
                    this.stats.errors++;
                    reject(request.error);
                };
            });

        } catch (error) {
            console.error('删除房间失败:', error);
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
    async searchMessages(query, roomId = null, limit = 50) {
        await this.ensureInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readonly');
            const store = transaction.objectStore('messages');
            
            const results = [];
            const searchTerm = query.toLowerCase();

            let request;
            if (roomId) {
                // 在指定房间搜索
                const index = store.index('roomId');
                request = index.openCursor(IDBKeyRange.only(roomId));
            } else {
                // 在所有消息中搜索
                request = store.openCursor();
            }

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                
                if (cursor && results.length < limit) {
                    const message = cursor.value;
                    
                    // 检查消息内容是否包含搜索词
                    if (message.content && 
                        message.content.toLowerCase().includes(searchTerm)) {
                        results.push(message);
                    }
                    
                    cursor.continue();
                } else {
                    this.stats.reads++;
                    // 按时间戳排序
                    results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                    resolve(results);
                }
            };

            request.onerror = () => {
                this.stats.errors++;
                reject(request.error);
            };
        });
    }

    /**
     * 获取数据库统计信息
     * @returns {Promise<Object>} 统计信息
     */
    async getStats() {
        await this.ensureInitialized();

        try {
            const messageCount = await this.getObjectStoreCount('messages');
            const roomCount = await this.getObjectStoreCount('rooms');

            return {
                ...this.stats,
                messageCount,
                roomCount,
                dbName: this.dbName,
                version: this.version,
                isInitialized: this.isInitialized
            };
        } catch (error) {
            console.error('获取统计信息失败:', error);
            return { ...this.stats, error: error.message };
        }
    }

    /**
     * 获取对象存储的记录数量
     * @param {string} storeName - 存储名称
     * @returns {Promise<number>} 记录数量
     */
    async getObjectStoreCount(storeName) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.count();

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * 清空所有数据
     * @returns {Promise<boolean>} 是否成功
     */
    async clearAllData() {
        await this.ensureInitialized();

        try {
            const storeNames = ['messages', 'rooms', 'settings', 'extensions'];
            
            for (const storeName of storeNames) {
                await new Promise((resolve, reject) => {
                    const transaction = this.db.transaction([storeName], 'readwrite');
                    const store = transaction.objectStore(storeName);
                    const request = store.clear();

                    request.onsuccess = () => resolve();
                    request.onerror = () => reject(request.error);
                });
            }

            console.log('✅ 已清空所有IndexedDB数据');
            return true;

        } catch (error) {
            console.error('清空数据失败:', error);
            return false;
        }
    }

    /**
     * 确保数据库已初始化
     * @private
     */
    async ensureInitialized() {
        if (!this.isInitialized) {
            await this.initialize();
        }
    }

    /**
     * 关闭数据库连接
     */
    close() {
        if (this.db) {
            this.db.close();
            this.db = null;
            this.isInitialized = false;
            console.log('IndexedDB连接已关闭');
        }
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
                database: {
                    name: this.dbName,
                    version: this.version,
                    initialized: this.isInitialized,
                    objectStores: this.db ? Array.from(this.db.objectStoreNames) : []
                },
                browser: {
                    indexedDBSupport: 'indexedDB' in window,
                    userAgent: navigator.userAgent
                }
            };
        } catch (error) {
            return {
                error: error.message,
                initialized: this.isInitialized
            };
        }
    }
}

// 导出类
window.IndexedDBManager = IndexedDBManager;

console.log('✅ IndexedDB管理器已加载');
