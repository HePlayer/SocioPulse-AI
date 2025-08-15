/**
 * 事件总线
 * 用于组件间通信的事件系统
 */

class EventBus {
    constructor() {
        this.events = {};
        this.maxListeners = 50; // 防止内存泄漏
    }

    /**
     * 注册事件监听器
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     * @param {Object} options - 选项
     */
    on(event, callback, options = {}) {
        if (typeof callback !== 'function') {
            throw new Error('回调函数必须是函数类型');
        }

        if (!this.events[event]) {
            this.events[event] = [];
        }

        // 检查监听器数量限制
        if (this.events[event].length >= this.maxListeners) {
            console.warn(`事件 "${event}" 的监听器数量已达到上限 (${this.maxListeners})`);
            return false;
        }

        const listener = {
            callback,
            once: options.once || false,
            priority: options.priority || 0
        };

        this.events[event].push(listener);

        // 按优先级排序（高优先级先执行）
        this.events[event].sort((a, b) => b.priority - a.priority);

        return true;
    }

    /**
     * 注册一次性事件监听器
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    once(event, callback) {
        return this.on(event, callback, { once: true });
    }

    /**
     * 触发事件
     * @param {string} event - 事件名称
     * @param {*} data - 事件数据
     * @returns {boolean} 是否有监听器处理了事件
     */
    emit(event, data) {
        if (!this.events[event] || this.events[event].length === 0) {
            return false;
        }

        const listeners = [...this.events[event]]; // 复制数组，避免在执行过程中被修改
        let hasHandlers = false;

        for (let i = 0; i < listeners.length; i++) {
            const listener = listeners[i];
            
            try {
                // 执行回调函数
                listener.callback(data, event);
                hasHandlers = true;

                // 如果是一次性监听器，执行后移除
                if (listener.once) {
                    this.off(event, listener.callback);
                }
            } catch (error) {
                console.error(`事件 "${event}" 的监听器执行出错:`, error);
            }
        }

        return hasHandlers;
    }

    /**
     * 移除事件监听器
     * @param {string} event - 事件名称
     * @param {Function} callback - 要移除的回调函数
     */
    off(event, callback) {
        if (!this.events[event]) {
            return false;
        }

        if (!callback) {
            // 如果没有指定回调函数，移除该事件的所有监听器
            delete this.events[event];
            return true;
        }

        const index = this.events[event].findIndex(listener => listener.callback === callback);
        if (index !== -1) {
            this.events[event].splice(index, 1);
            
            // 如果没有监听器了，删除事件
            if (this.events[event].length === 0) {
                delete this.events[event];
            }
            
            return true;
        }

        return false;
    }

    /**
     * 移除所有事件监听器
     */
    clear() {
        this.events = {};
    }

    /**
     * 获取事件的监听器数量
     * @param {string} event - 事件名称
     * @returns {number} 监听器数量
     */
    listenerCount(event) {
        return this.events[event] ? this.events[event].length : 0;
    }

    /**
     * 获取所有事件名称
     * @returns {string[]} 事件名称数组
     */
    eventNames() {
        return Object.keys(this.events);
    }

    /**
     * 异步触发事件
     * @param {string} event - 事件名称
     * @param {*} data - 事件数据
     * @returns {Promise<boolean>} 是否有监听器处理了事件
     */
    async emitAsync(event, data) {
        if (!this.events[event] || this.events[event].length === 0) {
            return false;
        }

        const listeners = [...this.events[event]];
        let hasHandlers = false;

        for (const listener of listeners) {
            try {
                // 支持异步回调函数
                await Promise.resolve(listener.callback(data, event));
                hasHandlers = true;

                // 如果是一次性监听器，执行后移除
                if (listener.once) {
                    this.off(event, listener.callback);
                }
            } catch (error) {
                console.error(`异步事件 "${event}" 的监听器执行出错:`, error);
            }
        }

        return hasHandlers;
    }

    /**
     * 创建命名空间事件总线
     * @param {string} namespace - 命名空间
     * @returns {Object} 命名空间事件总线
     */
    namespace(namespace) {
        const self = this;
        
        return {
            on(event, callback, options) {
                return self.on(`${namespace}:${event}`, callback, options);
            },
            
            once(event, callback) {
                return self.once(`${namespace}:${event}`, callback);
            },
            
            emit(event, data) {
                return self.emit(`${namespace}:${event}`, data);
            },
            
            emitAsync(event, data) {
                return self.emitAsync(`${namespace}:${event}`, data);
            },
            
            off(event, callback) {
                return self.off(`${namespace}:${event}`, callback);
            }
        };
    }

    /**
     * 调试信息
     * @returns {Object} 调试信息
     */
    debug() {
        const info = {
            totalEvents: Object.keys(this.events).length,
            totalListeners: 0,
            events: {}
        };

        for (const [event, listeners] of Object.entries(this.events)) {
            info.totalListeners += listeners.length;
            info.events[event] = {
                listenerCount: listeners.length,
                listeners: listeners.map(l => ({
                    once: l.once,
                    priority: l.priority
                }))
            };
        }

        return info;
    }
}

// 创建全局事件总线实例
const globalEventBus = new EventBus();

// 导出类和全局实例
window.EventBus = EventBus;
window.globalEventBus = globalEventBus;

console.log('✅ 事件总线已加载');
