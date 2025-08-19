// 模态框管理器

/**
 * 模态框管理器类
 * 统一管理所有模态框，确保它们之间不会相互干扰
 */
class ModalManager {
    constructor() {
        this.activeModals = new Set();
        this.initialize();
    }
    
    /**
     * 初始化模态框管理器
     */
    initialize() {
        console.log('🏗️ 初始化模态框管理器...');
        
        // 确保所有模态框元素存在
        this.ensureModalElements();
        
        // 绑定ESC键关闭所有模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });
        
        console.log('✅ 模态框管理器初始化完成');
    }
    
    /**
     * 确保所有必要的模态框元素存在
     */
    ensureModalElements() {
        // 确保设置模态框存在
        this.ensureSettingsModal();
        
        // 确保Agent信息模态框存在
        this.ensureAgentInfoModal();
        
        // 确保更多选项下拉菜单存在
        this.ensureMoreOptionsDropdown();
    }
    
    /**
     * 确保设置模态框存在
     */
    ensureSettingsModal() {
        let settingsModal = document.getElementById('settingsModal');
        if (!settingsModal) {
            console.log('⚠️ 创建缺失的设置模态框元素');
            // 设置模态框的HTML结构较为复杂，通常应该在HTML中定义
            // 这里我们只创建一个基本结构
            settingsModal = document.createElement('div');
            settingsModal.id = 'settingsModal';
            settingsModal.className = 'modal-overlay';
            settingsModal.style.display = 'none';
            settingsModal.innerHTML = `
                <div class="settings-modal">
                    <div class="modal-header">
                        <h3>设置</h3>
                        <button class="close-btn" id="closeSettingsModal">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="tabs">
                            <button class="tab-btn active" data-tab="models">模型设置</button>
                            <button class="tab-btn" data-tab="features">功能设置</button>
                            <button class="tab-btn" data-tab="data">数据管理</button>
                        </div>
                        <div class="tab-content active" id="modelsTab">
                            <p>模型设置内容将在初始化时填充</p>
                        </div>
                        <div class="tab-content" id="featuresTab">
                            <p>功能设置内容将在初始化时填充</p>
                        </div>
                        <div class="tab-content" id="dataTab">
                            <p>数据管理内容将在初始化时填充</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="cancel-btn" id="cancelSettingsBtn">取消</button>
                        <button class="action-btn" id="saveSettingsBtn">保存</button>
                    </div>
                </div>
            `;
            document.body.appendChild(settingsModal);
            
            // 绑定关闭按钮事件
            const closeBtn = document.getElementById('closeSettingsModal');
            const cancelBtn = document.getElementById('cancelSettingsBtn');
            const saveBtn = document.getElementById('saveSettingsBtn');
            
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.hideModal('settingsModal'));
            }
            
            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => this.hideModal('settingsModal'));
            }
            
            if (saveBtn) {
                saveBtn.addEventListener('click', () => {
                    if (window.app) {
                        window.app.saveSettings();
                    }
                });
            }
            
            // 点击外部关闭
            settingsModal.addEventListener('click', (e) => {
                if (e.target === settingsModal) {
                    this.hideModal('settingsModal');
                }
            });
            
            // 标签页切换
            const tabBtns = settingsModal.querySelectorAll('.tab-btn');
            tabBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const tabName = e.target.dataset.tab;
                    this.switchSettingsTab(tabName);
                });
            });
        }
    }
    
    /**
     * 确保Agent信息模态框存在
     */
    ensureAgentInfoModal() {
        let agentInfoModal = document.getElementById('agentInfoModal');
        if (!agentInfoModal) {
            console.log('⚠️ 创建缺失的Agent信息模态框元素');
            agentInfoModal = document.createElement('div');
            agentInfoModal.id = 'agentInfoModal';
            agentInfoModal.className = 'modal-overlay';
            agentInfoModal.style.display = 'none';
            agentInfoModal.innerHTML = `
                <div class="agent-info-modal">
                    <div class="modal-header">
                        <h3>Agent信息管理</h3>
                        <button class="close-btn" id="closeAgentInfoModal">×</button>
                    </div>
                    <div class="modal-body" id="agentInfoContent">
                        <div class="loading-placeholder">
                            <div class="loading-spinner"></div>
                            <p>加载Agent信息中...</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="action-btn" id="addNewAgentBtn">添加Agent</button>
                        <button class="cancel-btn" id="closeAgentInfoBtn">关闭</button>
                    </div>
                </div>
            `;
            document.body.appendChild(agentInfoModal);
            
            // 绑定关闭按钮事件
            const closeBtn1 = document.getElementById('closeAgentInfoModal');
            const closeBtn2 = document.getElementById('closeAgentInfoBtn');
            
            if (closeBtn1) {
                closeBtn1.addEventListener('click', () => this.hideModal('agentInfoModal'));
            }
            
            if (closeBtn2) {
                closeBtn2.addEventListener('click', () => this.hideModal('agentInfoModal'));
            }
            
            // 点击外部关闭
            agentInfoModal.addEventListener('click', (e) => {
                if (e.target === agentInfoModal) {
                    this.hideModal('agentInfoModal');
                }
            });
        }
    }
    
    /**
     * 确保更多选项下拉菜单存在
     */
    ensureMoreOptionsDropdown() {
        let moreOptionsDropdown = document.getElementById('moreOptionsDropdown');
        if (!moreOptionsDropdown) {
            console.log('⚠️ 创建缺失的更多选项下拉菜单元素');
            moreOptionsDropdown = document.createElement('div');
            moreOptionsDropdown.id = 'moreOptionsDropdown';
            moreOptionsDropdown.className = 'dropdown-overlay';
            moreOptionsDropdown.style.display = 'none';
            moreOptionsDropdown.innerHTML = `
                <div class="dropdown-menu" id="moreOptionsMenu">
                    <!-- 更多选项菜单项将动态生成 -->
                </div>
            `;
            document.body.appendChild(moreOptionsDropdown);
        }
    }
    
    /**
     * 显示指定的模态框
     * @param {string} modalId - 模态框的ID
     * @returns {boolean} - 是否成功显示
     */
    showModal(modalId) {
        console.log(`🔍 尝试显示模态框: ${modalId}`);
        
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error(`❌ 找不到模态框元素: ${modalId}`);
            return false;
        }
        
        try {
            // 显示模态框 - 使用多种方式确保显示
            modal.style.display = 'flex';
            modal.style.visibility = 'visible';
            modal.style.opacity = '1';
            modal.classList.remove('hidden');
            modal.classList.add('show');
            
            // 强制重排以确保样式生效
            modal.offsetHeight;
            
            // 添加到活动模态框集合
            this.activeModals.add(modalId);
            
            console.log(`✅ 模态框 ${modalId} 显示成功`);
            return true;
        } catch (error) {
            console.error(`❌ 显示模态框 ${modalId} 时出错:`, error);
            return false;
        }
    }
    
    /**
     * 隐藏指定的模态框
     * @param {string} modalId - 模态框的ID
     * @returns {boolean} - 是否成功隐藏
     */
    hideModal(modalId) {
        console.log(`🔍 尝试隐藏模态框: ${modalId}`);
        
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error(`❌ 找不到模态框元素: ${modalId}`);
            return false;
        }
        
        try {
            // 隐藏模态框 - 使用多种方式确保隐藏
            modal.classList.remove('show');
            modal.classList.add('hidden');
            modal.style.display = 'none';
            modal.style.visibility = 'hidden';
            modal.style.opacity = '0';
            
            // 从活动模态框集合中移除
            this.activeModals.delete(modalId);
            
            console.log(`✅ 模态框 ${modalId} 隐藏成功`);
            return true;
        } catch (error) {
            console.error(`❌ 隐藏模态框 ${modalId} 时出错:`, error);
            return false;
        }
    }
    
    /**
     * 切换设置标签页
     * @param {string} tabName - 标签页名称
     */
    switchSettingsTab(tabName) {
        // 更新标签按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');

        // 更新标签内容
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`)?.classList.add('active');
    }
    
    /**
     * 关闭所有模态框
     */
    closeAllModals() {
        console.log('🔒 关闭所有模态框');
        
        // 复制活动模态框集合，因为在迭代过程中会修改集合
        const activeModals = [...this.activeModals];
        
        // 关闭每个活动的模态框
        activeModals.forEach(modalId => {
            this.hideModal(modalId);
        });
        
        // 额外检查，确保所有模态框都被隐藏
        document.querySelectorAll('.modal-overlay, .dropdown-overlay').forEach(modal => {
            modal.style.display = 'none';
            modal.classList.remove('show');
        });
        
        console.log('✅ 所有模态框已关闭');
    }
    
    /**
     * 检查模态框是否存在
     * @param {string} modalId - 模态框的ID
     * @returns {boolean} - 模态框是否存在
     */
    hasModal(modalId) {
        return !!document.getElementById(modalId);
    }
    
    /**
     * 检查模态框是否处于活动状态
     * @param {string} modalId - 模态框的ID
     * @returns {boolean} - 模态框是否处于活动状态
     */
    isModalActive(modalId) {
        return this.activeModals.has(modalId);
    }
}

// 全局导出
window.ModalManager = ModalManager;
