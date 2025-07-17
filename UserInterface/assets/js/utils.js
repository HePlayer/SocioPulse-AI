// 工具函数模块

// 通知系统
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${getNotificationIcon(type)}</span>
            <span class="notification-message">${message}</span>
            <button class="notification-close">×</button>
        </div>
    `;
    
    // 添加样式（如果还没有）
    if (!document.querySelector('#notification-styles')) {
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 3000;
                min-width: 300px;
                max-width: 500px;
                background: var(--secondary-color);
                border-radius: 8px;
                box-shadow: 0 4px 12px var(--shadow);
                border-left: 4px solid;
                animation: slideInRight 0.3s ease;
            }
            
            .notification-success { border-left-color: #4CAF50; }
            .notification-error { border-left-color: #f44336; }
            .notification-warning { border-left-color: #ff9800; }
            .notification-info { border-left-color: var(--primary-color); }
            
            .notification-content {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 15px;
            }
            
            .notification-icon {
                font-size: 20px;
                flex-shrink: 0;
            }
            
            .notification-message {
                flex: 1;
                color: var(--text-color);
                line-height: 1.4;
            }
            
            .notification-close {
                background: none;
                border: none;
                color: var(--text-color);
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                opacity: 0.7;
                transition: all 0.3s ease;
            }
            
            .notification-close:hover {
                opacity: 1;
                background-color: var(--bg-color);
            }
            
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(styles);
    }
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 绑定关闭事件
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => hideNotification(notification));
    
    // 自动隐藏
    const duration = type === 'error' ? 8000 : 5000; // 错误消息显示更久
    setTimeout(() => hideNotification(notification), duration);
}

// 获取通知图标
function getNotificationIcon(type) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    return icons[type] || icons.info;
}

// 隐藏通知
function hideNotification(notification) {
    if (notification && notification.parentNode) {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
}

// 主题切换函数
async function toggleTheme() {
    window.currentTheme = window.currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', window.currentTheme);
    
    const themeToggle = document.querySelector('.theme-toggle');
    themeToggle.textContent = window.currentTheme === 'light' ? '🌙' : '☀️';
    
    // 保存主题偏好到localStorage（临时存储）
    localStorage.setItem('theme', window.currentTheme);
    
    // 重要：同步更新用户设置，确保主题偏好被持久化保存
    try {
        const settings = window.settingsManager.getSettings();
        settings.features.ui.theme = window.currentTheme;
        
        // 保存到本地设置
        window.settingsManager.saveSettings(settings);
        
        // 同步到后端
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            const result = await response.json();
            if (!result.success) {
                console.warn('Failed to sync theme to backend:', result.message);
            }
        } else {
            console.warn('Failed to sync theme to backend: HTTP', response.status);
        }
        
        // 如果设置面板是打开的，同步更新主题选择器
        const defaultThemeSelect = document.getElementById('defaultTheme');
        if (defaultThemeSelect && document.getElementById('settingsModal').classList.contains('show')) {
            defaultThemeSelect.value = window.currentTheme;
        }
        
    } catch (error) {
        console.error('Error syncing theme setting:', error);
        // 即使同步失败，界面主题切换仍然生效
    }
}

// 消息去重系统
class UtilsMessageDeduplicator {
    constructor() {
        this.displayedMessages = new Set(); // 已显示的消息ID集合
        this.recentUserMessages = []; // 最近发送的用户消息缓存
    }

    // 生成消息ID（基于内容的简化版）
    generateMessageId(message) {
        return `${message.sender}_${message.content}_${message.timestamp}`;
    }

    // 生成基于内容的去重ID（忽略时间戳差异）
    generateContentBasedId(message) {
        return `${message.sender}_${message.content}`;
    }

    // 检查是否是重复的用户消息
    isDuplicateUserMessage(message) {
        if (message.sender !== 'user') {
            return false;
        }
        
        const contentId = this.generateContentBasedId(message);
        const messageTime = new Date(message.timestamp).getTime();
        
        // 检查最近5分钟内是否有相同内容的消息
        const fiveMinutesAgo = messageTime - 5 * 60 * 1000;
        
        for (const recentMsg of this.recentUserMessages) {
            const recentTime = new Date(recentMsg.timestamp).getTime();
            const recentContentId = this.generateContentBasedId(recentMsg);
            
            // 如果内容相同且时间差在5分钟内，认为是重复消息
            if (recentContentId === contentId && recentTime >= fiveMinutesAgo) {
                const timeDiff = Math.abs(messageTime - recentTime);
                console.log(`🔍 Found potential duplicate: time diff = ${timeDiff}ms`);
                
                // 如果时间差在30秒内，很可能是重复消息
                if (timeDiff <= 30000) {
                    return true;
                }
            }
        }
        
        return false;
    }

    // 记录用户消息
    recordUserMessage(message) {
        if (message.sender === 'user') {
            this.recentUserMessages.push({
                content: message.content,
                timestamp: message.timestamp,
                sender: message.sender
            });
            
            // 只保留最近50条消息
            if (this.recentUserMessages.length > 50) {
                this.recentUserMessages = this.recentUserMessages.slice(-50);
            }
            
            console.log(`📝 Recorded user message, total cached: ${this.recentUserMessages.length}`);
        }
    }

    // 检查消息是否应该显示
    shouldDisplayMessage(message) {
        // 如果是本地生成的消息，始终显示（不进行去重）
        if (message.is_local === true) {
            console.log('✅ Local message, bypassing deduplication');
            return true;
        }
        
        // 生成消息唯一ID（基于时间戳的精确匹配）
        const messageId = this.generateMessageId(message);
        console.log('🔍 Generated message ID:', messageId);
        
        // 第一层检查：精确匹配（包含时间戳）
        if (this.displayedMessages.has(messageId)) {
            console.log('⚠️ Message already displayed (exact match), skipping:', messageId);
            return false;
        }
        
        // 第二层检查：用户消息的内容去重（智能去重）
        if (this.isDuplicateUserMessage(message)) {
            console.log('⚠️ Duplicate user message detected (content-based), skipping');
            return false;
        }
        
        // 记录用户消息到缓存
        this.recordUserMessage(message);
        
        // 标记消息为已显示
        this.displayedMessages.add(messageId);
        console.log('✅ Message marked as displayed:', messageId);
        
        return true;
    }

    // 重置去重系统（切换房间时调用）
    reset() {
        this.displayedMessages.clear();
        console.log('🧹 Cleared displayed messages for room switch');
    }
}

// 全局导出
window.showNotification = showNotification;
window.hideNotification = hideNotification;
window.toggleTheme = toggleTheme;
window.UtilsMessageDeduplicator = UtilsMessageDeduplicator;
