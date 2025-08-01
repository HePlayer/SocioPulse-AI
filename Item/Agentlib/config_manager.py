"""
配置管理器
为AgentFactory提供统一的配置读取接口
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file_path: 配置文件路径，默认为项目根目录的config.yaml
        """
        self.config_file_path = config_file_path or self._find_config_file()
        self._config_cache: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        # 尝试多个可能的配置文件位置
        possible_paths = [
            "config.yaml",
            "../config.yaml",
            "../../config.yaml",
            os.path.join(os.path.dirname(__file__), "../../config.yaml")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果找不到配置文件，返回默认路径
        return "config.yaml"
    
    def _load_config(self):
        """加载配置文件"""
        import logging
        logger = logging.getLogger(f"{__name__}.ConfigManager")

        try:
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    self._config_cache = yaml.safe_load(f) or {}
                logger.info(f"Successfully loaded config from {self.config_file_path}")

                # 调试：打印模型配置
                if 'models' in self._config_cache:
                    models_config = self._config_cache['models']
                    logger.debug(f"Models config loaded: {list(models_config.keys())}")

                    if 'platforms' in models_config:
                        platforms = models_config['platforms']
                        logger.debug(f"Available platforms: {list(platforms.keys())}")

                        for platform, config in platforms.items():
                            has_api_key = bool(config.get('api_key', '').strip())
                            logger.debug(f"Platform '{platform}': API key {'configured' if has_api_key else 'NOT configured'}")
                    else:
                        logger.warning("No 'platforms' section found in models config")
                else:
                    logger.warning("No 'models' section found in config file")
            else:
                logger.warning(f"Config file not found: {self.config_file_path}")
                self._config_cache = {}
        except Exception as e:
            logger.error(f"Failed to load config file {self.config_file_path}: {e}")
            self._config_cache = {}
    
    def reload_config(self):
        """重新加载配置"""
        self._config_cache = None
        self._load_config()
    
    def get_config(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，支持点分隔的嵌套键，如 'models.openai.api_key'
            default: 默认值
            
        Returns:
            配置值
        """
        if self._config_cache is None:
            self._load_config()
        
        keys = key_path.split('.')
        value = self._config_cache
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_api_key(self, model_type: str) -> Optional[str]:
        """
        获取指定模型类型的API密钥

        Args:
            model_type: 模型类型（openai, aihubmix, zhipuai等）

        Returns:
            API密钥，如果未找到则返回None
        """
        import logging
        logger = logging.getLogger(f"{__name__}.ConfigManager")

        # 标准化模型类型名称
        normalized_type = self._normalize_model_type(model_type)
        logger.debug(f"Looking for API key for platform '{model_type}' (normalized: '{normalized_type}')")

        # 尝试多种配置路径
        possible_paths = [
            f"models.platforms.{normalized_type}.api_key",  # 新的配置结构
            f"models.{normalized_type}.api_key",
            f"api_keys.{normalized_type}",
            f"{normalized_type}.api_key",
            f"{normalized_type}_api_key"
        ]

        for path in possible_paths:
            api_key = self.get_config(path)
            if api_key and api_key.strip():  # 确保不是空字符串
                logger.debug(f"Found API key for '{normalized_type}' at config path: {path}")
                return api_key.strip()
            else:
                logger.debug(f"No API key found at config path: {path}")

        # 尝试从环境变量获取
        env_var_names = [
            f"{normalized_type.upper()}_API_KEY",
            f"API_KEY_{normalized_type.upper()}",
            f"{normalized_type.upper()}_KEY"
        ]

        for env_var in env_var_names:
            api_key = os.getenv(env_var)
            if api_key and api_key.strip():
                logger.debug(f"Found API key for '{normalized_type}' in environment variable: {env_var}")
                return api_key.strip()
            else:
                logger.debug(f"No API key found in environment variable: {env_var}")

        logger.warning(f"No API key found for platform '{model_type}' (normalized: '{normalized_type}')")
        logger.debug(f"Searched config paths: {possible_paths}")
        logger.debug(f"Searched environment variables: {env_var_names}")

        return None
    
    def get_platform_config(self, model_type: str) -> Dict[str, Any]:
        """
        获取平台配置
        
        Args:
            model_type: 模型类型
            
        Returns:
            平台配置字典
        """
        normalized_type = self._normalize_model_type(model_type)
        
        # 获取平台特定配置
        platform_config = self.get_config(f"models.{normalized_type}", {})
        
        # 如果没有找到，尝试其他路径
        if not platform_config:
            platform_config = self.get_config(f"platforms.{normalized_type}", {})
        
        return platform_config or {}
    
    def get_default_model(self, model_type: str) -> Optional[str]:
        """
        获取默认模型名称
        
        Args:
            model_type: 模型类型
            
        Returns:
            默认模型名称
        """
        platform_config = self.get_platform_config(model_type)
        return platform_config.get('default_model')
    
    def get_api_base(self, model_type: str) -> Optional[str]:
        """
        获取API基础URL
        
        Args:
            model_type: 模型类型
            
        Returns:
            API基础URL
        """
        platform_config = self.get_platform_config(model_type)
        return platform_config.get('api_base')
    
    def _normalize_model_type(self, model_type: str) -> str:
        """标准化模型类型名称"""
        # 处理常见的别名 - 统一使用zhipu作为标准标识符
        aliases = {
            'zhipuai': 'zhipu',  # zhipuai是zhipu的别名
            'openai-gpt': 'openai',
            'gpt': 'openai'
        }

        normalized = model_type.lower().strip()
        return aliases.get(normalized, normalized)
    
    def is_api_configured(self, model_type: str) -> bool:
        """
        检查指定模型类型是否已配置API密钥
        
        Args:
            model_type: 模型类型
            
        Returns:
            是否已配置
        """
        return self.get_api_key(model_type) is not None
    
    def get_available_platforms(self) -> List[str]:
        """
        获取所有已配置的平台列表
        
        Returns:
            已配置平台列表
        """
        platforms = []
        
        # 从配置文件中获取
        models_config = self.get_config('models', {})
        for platform in models_config.keys():
            if self.is_api_configured(platform):
                platforms.append(platform)
        
        # 检查环境变量中的配置
        common_platforms = ['openai', 'aihubmix', 'zhipu']  # 移除zhipuai别名，避免重复
        for platform in common_platforms:
            if platform not in platforms and self.is_api_configured(platform):
                platforms.append(platform)
        
        return platforms
    
    def validate_agent_config(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证Agent配置
        
        Args:
            agent_config: Agent配置字典
            
        Returns:
            验证结果，包含是否有效和错误信息
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查必需字段
        required_fields = ['name', 'role']
        for field in required_fields:
            if field not in agent_config or not agent_config[field]:
                result['valid'] = False
                result['errors'].append(f"Missing required field: {field}")
        
        # 检查平台配置
        if 'platform' in agent_config:
            platform = agent_config['platform']
            if not self.is_api_configured(platform):
                result['warnings'].append(f"Platform {platform} is not configured with API key")
        
        # 检查模型名称
        if 'model_name' in agent_config and 'platform' in agent_config:
            platform = agent_config['platform']
            model_name = agent_config['model_name']
            platform_config = self.get_platform_config(platform)
            
            # 这里可以添加更多的模型验证逻辑
            if platform_config and 'supported_models' in platform_config:
                supported_models = platform_config['supported_models']
                if model_name not in supported_models:
                    result['warnings'].append(f"Model {model_name} may not be supported by {platform}")
        
        return result
    
    def get_agent_factory_config(self) -> Dict[str, Any]:
        """
        获取AgentFactory的配置
        
        Returns:
            AgentFactory配置字典
        """
        return self.get_config('agent_factory', {
            'default_creation_mode': 'standard',
            'enable_tools_by_default': False,
            'enable_discussion_optimization': True
        })
