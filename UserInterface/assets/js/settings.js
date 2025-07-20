// 设置管理模块

class SettingsManager {
    constructor() {
        this.settings = this.getDefaultSettings();
        this.loadSettings();
    }

    // 默认设置
    getDefaultSettings() {
        return {
            models: {
                default_platform: 'aihubmix',
                platforms: {
                    openai: {
                        api_key: '',
                        api_base: 'https://api.openai.com/v1',
                        available_models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                        enabled_models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                        default_model: 'gpt-4'
                    },
                    aihubmix: {
                        api_key: '',
                        api_base: 'https://aihubmix.com/v1',
                        available_models: ['gpt-4o-mini', 'gpt-4o-search-preview', 'gpt-4o-mini-search-preview'],
                        enabled_models: ['gpt-4o-mini', 'gpt-4o-search-preview', 'gpt-4o-mini-search-preview'],
                        default_model: 'gpt-4o-mini'
                    },
                    zhipu: {
                        api_key: '',
                        api_base: 'https://open.bigmodel.cn/api/paas/v4',
                        available_models: ['glm-4', 'glm-4-plus', 'glm-3-turbo'],
                        enabled_models: ['glm-4', 'glm-4-plus', 'glm-3-turbo'],
                        default_model: 'glm-4'
                    }
                }
            },
            features: {
                proactive_chat: {
                    enabled: false,
                    monitoring_interval: 5,
                    confidence_threshold: 0.8,
                    max_suggestions_per_hour: 3
                },
                ui: {
                    theme: 'light'
                }
            }
        };
    }

    // 加载设置
    async loadSettings() {
        try {
            // 从localStorage加载
            const saved = localStorage.getItem('multiai_settings');
            if (saved) {
                this.settings = { ...this.settings, ...JSON.parse(saved) };
            }

            // 从后端加载
            const response = await fetch('/api/settings');
            if (response.ok) {
                const serverSettings = await response.json();
                console.log('📋 Server settings loaded:', serverSettings);
                
                // 检查返回的数据结构
                if (serverSettings && serverSettings.data && serverSettings.data.settings) {
                    console.log('✅ Using settings from server response data.settings');
                    this.settings = { ...this.settings, ...serverSettings.data.settings };
                } else if (serverSettings && serverSettings.settings) {
                    console.log('✅ Using settings from server response settings');
                    this.settings = { ...this.settings, ...serverSettings.settings };
                } else if (serverSettings && serverSettings.data) {
                    console.log('✅ Using settings from server response data');
                    this.settings = { ...this.settings, ...serverSettings.data };
                } else {
                    console.log('✅ Using entire server response as settings');
                    this.settings = { ...this.settings, ...serverSettings };
                }
                
                console.log('📋 Final merged settings:', this.settings);
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    // 保存设置
    saveSettings(newSettings = null) {
        if (newSettings) {
            this.settings = { ...this.settings, ...newSettings };
        }
        localStorage.setItem('multiai_settings', JSON.stringify(this.settings));
    }

    // 获取设置
    getSettings() {
        return this.settings;
    }

    // 同步到后端
    async syncToServer() {
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.settings)
            });
            
            if (response.ok) {
                const result = await response.json();
                return result.success;
            }
        } catch (error) {
            console.error('Error syncing settings:', error);
        }
        return false;
    }

    // 初始化设置界面
    initializeSettingsUI() {
        this.initializeModelSettings();
        this.initializeFeatureSettings();
        this.initializeDataManagement();
        this.bindSettingsEvents();
    }

    // 初始化模型设置
    initializeModelSettings() {
        const settings = this.getSettings();
        
        // 设置默认平台
        const defaultPlatformSelect = document.getElementById('defaultPlatformSelect');
        if (defaultPlatformSelect) {
            defaultPlatformSelect.value = settings.models.default_platform;
        }

        // 设置各平台配置
        Object.keys(settings.models.platforms).forEach(platform => {
            const config = settings.models.platforms[platform];
            
            // API Key
            const apiKeyInput = document.getElementById(`${platform}ApiKey`);
            if (apiKeyInput) {
                apiKeyInput.value = config.api_key || '';
            }
            
            // API Base
            const apiBaseInput = document.getElementById(`${platform}ApiBase`);
            if (apiBaseInput) {
                apiBaseInput.value = config.api_base || '';
            }
            
            // 默认模型
            const defaultModelSelect = document.getElementById(`${platform}DefaultModel`);
            if (defaultModelSelect) {
                defaultModelSelect.value = config.default_model || '';
            }
            
            // 可用模型复选框
            const modelCheckboxes = document.getElementById(`${platform}Models`);
            if (modelCheckboxes) {
                const checkboxes = modelCheckboxes.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(checkbox => {
                    checkbox.checked = config.available_models.includes(checkbox.value);
                });
            }
        });
    }

    // 初始化功能设置
    initializeFeatureSettings() {
        const settings = this.getSettings();
        
        // 主动聊天设置
        const proactiveChatEnabled = document.getElementById('proactiveChatEnabled');
        if (proactiveChatEnabled) {
            proactiveChatEnabled.checked = settings.features.proactive_chat.enabled;
        }
        
        const monitoringInterval = document.getElementById('monitoringInterval');
        const intervalValue = document.getElementById('intervalValue');
        if (monitoringInterval && intervalValue) {
            monitoringInterval.value = settings.features.proactive_chat.monitoring_interval;
            intervalValue.textContent = settings.features.proactive_chat.monitoring_interval;
        }
        
        const confidenceThreshold = document.getElementById('confidenceThreshold');
        const confidenceValue = document.getElementById('confidenceValue');
        if (confidenceThreshold && confidenceValue) {
            confidenceThreshold.value = settings.features.proactive_chat.confidence_threshold;
            confidenceValue.textContent = settings.features.proactive_chat.confidence_threshold;
        }
        
        const maxSuggestionsPerHour = document.getElementById('maxSuggestionsPerHour');
        if (maxSuggestionsPerHour) {
            maxSuggestionsPerHour.value = settings.features.proactive_chat.max_suggestions_per_hour;
        }
        
        // 主题设置
        const defaultTheme = document.getElementById('defaultTheme');
        if (defaultTheme) {
            defaultTheme.value = settings.features.ui.theme;
        }
    }

    // 初始化数据管理
    initializeDataManagement() {
        // 计算存储大小
        const storageSize = document.getElementById('storageSize');
        if (storageSize) {
            const size = JSON.stringify(this.settings).length;
            storageSize.textContent = `${(size / 1024).toFixed(2)} KB`;
        }
        
        // 最后更新时间
        const lastUpdate = document.getElementById('lastUpdate');
        if (lastUpdate) {
            const updateTime = localStorage.getItem('multiai_settings_updated');
            lastUpdate.textContent = updateTime ? new Date(updateTime).toLocaleString() : '未知';
        }
    }

    // 绑定设置事件
    bindSettingsEvents() {
        // 滑块值更新
        const monitoringInterval = document.getElementById('monitoringInterval');
        const intervalValue = document.getElementById('intervalValue');
        if (monitoringInterval && intervalValue) {
            monitoringInterval.addEventListener('input', () => {
                intervalValue.textContent = monitoringInterval.value;
            });
        }
        
        const confidenceThreshold = document.getElementById('confidenceThreshold');
        const confidenceValue = document.getElementById('confidenceValue');
        if (confidenceThreshold && confidenceValue) {
            confidenceThreshold.addEventListener('input', () => {
                confidenceValue.textContent = confidenceThreshold.value;
            });
        }
        
        // 测试按钮
        document.querySelectorAll('.test-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const platform = e.target.dataset.platform;
                this.testPlatformConnection(platform, e.target);
            });
        });
        
        // 导出配置
        const exportConfigBtn = document.getElementById('exportConfigBtn');
        if (exportConfigBtn) {
            exportConfigBtn.addEventListener('click', () => this.exportConfig());
        }
        
        // 导入配置
        const importConfigBtn = document.getElementById('importConfigBtn');
        const importConfigFile = document.getElementById('importConfigFile');
        if (importConfigBtn && importConfigFile) {
            importConfigBtn.addEventListener('click', () => importConfigFile.click());
            importConfigFile.addEventListener('change', (e) => this.importConfig(e));
        }
        
        // 重置设置
        const resetSettingsBtn = document.getElementById('resetSettingsBtn');
        if (resetSettingsBtn) {
            resetSettingsBtn.addEventListener('click', () => this.resetSettings());
        }
    }

    // 测试平台连接
    async testPlatformConnection(platform, button) {
        const originalText = button.textContent;
        button.textContent = '测试中...';
        button.disabled = true;
        
        try {
            const apiKey = document.getElementById(`${platform}ApiKey`).value;
            const apiBase = document.getElementById(`${platform}ApiBase`).value;
            
            if (!apiKey) {
                showNotification('请先输入API Key', 'warning');
                return;
            }
            
            const response = await fetch('/api/test_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    platform: platform,
                    api_key: apiKey,
                    api_base: apiBase
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(`${platform} 连接测试成功`, 'success');
            } else {
                showNotification(`${platform} 连接测试失败: ${result.message}`, 'error');
            }
        } catch (error) {
            showNotification(`连接测试出错: ${error.message}`, 'error');
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    // 导出配置
    exportConfig() {
        const config = this.getSettings();
        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `multiai_config_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        showNotification('配置已导出', 'success');
    }

    // 导入配置
    importConfig(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const config = JSON.parse(e.target.result);
                this.settings = { ...this.getDefaultSettings(), ...config };
                this.saveSettings();
                this.initializeSettingsUI();
                showNotification('配置导入成功', 'success');
            } catch (error) {
                showNotification('配置文件格式错误', 'error');
            }
        };
        reader.readAsText(file);
    }

    // 重置设置
    resetSettings() {
        if (confirm('确定要重置所有设置吗？此操作不可撤销。')) {
            this.settings = this.getDefaultSettings();
            this.saveSettings();
            this.initializeSettingsUI();
            showNotification('设置已重置', 'success');
        }
    }

    // 保存当前设置
    saveCurrentSettings() {
        const newSettings = this.collectSettingsFromUI();
        this.saveSettings(newSettings);
        localStorage.setItem('multiai_settings_updated', new Date().toISOString());
        return newSettings;
    }

    // 从UI收集设置
    collectSettingsFromUI() {
        const settings = { ...this.settings };
        
        // 收集模型设置
        const defaultPlatform = document.getElementById('defaultPlatformSelect')?.value;
        if (defaultPlatform) {
            settings.models.default_platform = defaultPlatform;
        }
        
        // 收集平台配置
        Object.keys(settings.models.platforms).forEach(platform => {
            const apiKey = document.getElementById(`${platform}ApiKey`)?.value;
            const apiBase = document.getElementById(`${platform}ApiBase`)?.value;
            const defaultModel = document.getElementById(`${platform}DefaultModel`)?.value;
            
            if (apiKey !== undefined) settings.models.platforms[platform].api_key = apiKey;
            if (apiBase !== undefined) settings.models.platforms[platform].api_base = apiBase;
            if (defaultModel !== undefined) settings.models.platforms[platform].default_model = defaultModel;
            
            // 收集可用模型
            const modelCheckboxes = document.getElementById(`${platform}Models`);
            if (modelCheckboxes) {
                const availableModels = [];
                modelCheckboxes.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
                    availableModels.push(checkbox.value);
                });
                settings.models.platforms[platform].available_models = availableModels;
                // 同时更新enabled_models，保持与available_models一致
                settings.models.platforms[platform].enabled_models = [...availableModels];
            }
        });
        
        // 收集功能设置
        const proactiveChatEnabled = document.getElementById('proactiveChatEnabled')?.checked;
        const monitoringInterval = document.getElementById('monitoringInterval')?.value;
        const confidenceThreshold = document.getElementById('confidenceThreshold')?.value;
        const maxSuggestionsPerHour = document.getElementById('maxSuggestionsPerHour')?.value;
        const defaultTheme = document.getElementById('defaultTheme')?.value;
        
        if (proactiveChatEnabled !== undefined) settings.features.proactive_chat.enabled = proactiveChatEnabled;
        if (monitoringInterval !== undefined) settings.features.proactive_chat.monitoring_interval = parseInt(monitoringInterval);
        if (confidenceThreshold !== undefined) settings.features.proactive_chat.confidence_threshold = parseFloat(confidenceThreshold);
        if (maxSuggestionsPerHour !== undefined) settings.features.proactive_chat.max_suggestions_per_hour = parseInt(maxSuggestionsPerHour);
        if (defaultTheme !== undefined) settings.features.ui.theme = defaultTheme;
        
        return settings;
    }
}

// 全局导出
window.SettingsManager = SettingsManager;
