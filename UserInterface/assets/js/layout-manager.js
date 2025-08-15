/**
 * 聊天布局管理器
 * 负责动态计算和优化聊天窗口的布局，确保消息能够完全显示
 */
class ChatLayoutManager {
    constructor() {
        this.inputHeight = 0;
        this.headerHeight = 0;
        this.topBarHeight = 60;
        this.isInitialized = false;
        
        console.log('📐 ChatLayoutManager 初始化');
    }
    
    /**
     * 计算并应用最优布局
     */
    optimizeLayout() {
        try {
            const chatArea = document.querySelector('.chat-area');
            const messagesContainer = document.getElementById('messagesContainer');
            const inputContainer = document.querySelector('.input-container');
            const chatHeader = document.querySelector('.chat-header');
            
            if (!chatArea || !messagesContainer || !inputContainer) {
                console.log('⚠️ 布局元素未找到，跳过优化');
                return;
            }
            
            // 获取实际高度
            this.headerHeight = chatHeader ? chatHeader.offsetHeight : 0;
            this.inputHeight = inputContainer.offsetHeight;
            
            // 计算消息容器的最优高度
            const availableHeight = window.innerHeight - this.topBarHeight - this.headerHeight - this.inputHeight;
            
            // 应用计算结果 - 确保消息容器有正确的高度
            messagesContainer.style.maxHeight = `${availableHeight}px`;
            messagesContainer.style.height = `${availableHeight}px`;
            
            console.log('📏 布局优化完成:', {
                availableHeight,
                inputHeight: this.inputHeight,
                headerHeight: this.headerHeight,
                windowHeight: window.innerHeight
            });
            
            // 优化后滚动到底部
            this.scrollToBottom();
            
        } catch (error) {
            console.error('❌ 布局优化失败:', error);
        }
    }
    
    /**
     * 监听输入框高度变化
     */
    observeInputHeight() {
        const inputContainer = document.querySelector('.input-container');
        const messageInput = document.querySelector('.message-input');
        
        if (!inputContainer || !messageInput) {
            console.log('⚠️ 输入框元素未找到');
            return;
        }
        
        // 监听输入框内容变化
        messageInput.addEventListener('input', () => {
            // 延迟执行，等待高度变化完成
            setTimeout(() => {
                const newHeight = inputContainer.offsetHeight;
                if (Math.abs(newHeight - this.inputHeight) > 5) { // 避免微小变化触发
                    console.log('📝 输入框高度变化:', this.inputHeight, '->', newHeight);
                    this.inputHeight = newHeight;
                    this.optimizeLayout();
                }
            }, 10);
        });
        
        // 监听窗口大小变化
        window.addEventListener('resize', () => {
            console.log('🔄 窗口大小变化，重新优化布局');
            setTimeout(() => {
                this.optimizeLayout();
            }, 100);
        });
        
        console.log('👁️ 输入框高度监听已启动');
    }
    
    /**
     * 优化的滚动到底部方法
     */
    scrollToBottom() {
        setTimeout(() => {
            const messagesContainer = document.getElementById('messagesContainer');
            if (messagesContainer) {
                // 滚动到真正的底部
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
                // 确保最后一条消息完全可见
                const lastMessage = messagesContainer.querySelector('.message:last-child');
                if (lastMessage) {
                    lastMessage.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'end',
                        inline: 'nearest'
                    });
                }
                
                console.log('⬇️ 滚动到底部完成');
            }
        }, 50);
    }
    
    /**
     * 检查消息是否完全可见
     */
    isMessageFullyVisible(messageElement) {
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer || !messageElement) return false;
        
        const containerRect = messagesContainer.getBoundingClientRect();
        const messageRect = messageElement.getBoundingClientRect();
        
        return (
            messageRect.top >= containerRect.top &&
            messageRect.bottom <= containerRect.bottom
        );
    }
    
    /**
     * 确保指定消息可见
     */
    ensureMessageVisible(messageElement) {
        if (!messageElement) return;
        
        if (!this.isMessageFullyVisible(messageElement)) {
            messageElement.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest',
                inline: 'nearest'
            });
            console.log('👁️ 确保消息可见');
        }
    }
    
    /**
     * 初始化布局管理
     */
    initialize() {
        if (this.isInitialized) {
            console.log('⚠️ 布局管理器已初始化');
            return;
        }
        
        console.log('🚀 初始化布局管理器');
        
        // 初始布局优化
        setTimeout(() => {
            this.optimizeLayout();
            this.observeInputHeight();
            this.isInitialized = true;
            console.log('✅ 布局管理器初始化完成');
        }, 100);
    }
    
    /**
     * 重置布局管理器
     */
    reset() {
        this.isInitialized = false;
        console.log('🔄 布局管理器已重置');
    }
    
    /**
     * 获取布局信息
     */
    getLayoutInfo() {
        const messagesContainer = document.getElementById('messagesContainer');
        const inputContainer = document.querySelector('.input-container');
        const chatHeader = document.querySelector('.chat-header');
        
        return {
            windowHeight: window.innerHeight,
            topBarHeight: this.topBarHeight,
            headerHeight: chatHeader ? chatHeader.offsetHeight : 0,
            inputHeight: inputContainer ? inputContainer.offsetHeight : 0,
            messagesHeight: messagesContainer ? messagesContainer.offsetHeight : 0,
            messagesScrollHeight: messagesContainer ? messagesContainer.scrollHeight : 0,
            messagesScrollTop: messagesContainer ? messagesContainer.scrollTop : 0
        };
    }
    
    /**
     * 调试信息
     */
    debugLayout() {
        const info = this.getLayoutInfo();
        console.table(info);
        return info;
    }
}

// 导出布局管理器
window.ChatLayoutManager = ChatLayoutManager;

console.log('📐 ChatLayoutManager 类已加载');
