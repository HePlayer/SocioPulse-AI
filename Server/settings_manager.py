"""
设置管理模块
"""

import os
import logging
from typing import Dict, Any, List
from aiohttp import web

from .config import CONFIG_FILE_PATH, DEFAULT_SETTINGS, DEFAULT_AVAILABLE_MODELS, HTTP_STATUS
from .utils import get_platform_display_name, get_model_display_name, build_model_option, create_error_response, create_success_response
from .connection_tester import ConnectionTester

logger = logging.getLogger(__name__)


class SettingsManager:
    """设置管理器"""
    
    def __init__(self):
        self.connection_tester = ConnectionTester()
        # 确保settings属性始终存在
        self._settings = None
    
    @property
    def settings(self) -> Dict[str, Any]:
        """确保settings属性始终可用"""
        if self._settings is None:
            self._settings = self.get_settings()
        return self._settings

    @settings.setter
    def settings(self, value: Dict[str, Any]):
        """允许外部设置settings"""
        self._settings = value
    
    def _read_config_file(self) -> Dict[str, Any]:
        """读取配置文件"""
        try:
            if os.path.exists(CONFIG_FILE_PATH):
                import yaml
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {}
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            return {}
    
    def _write_config_file(self, config: Dict[str, Any]) -> bool:
        """写入配置文件"""
        try:
            import yaml
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            logger.error(f"Error writing config file: {e}")
            return False
    
    def get_settings(self) -> Dict[str, Any]:
        """获取系统设置"""
        config = self._read_config_file()
        
        if config:
            return config
        else:
            # 返回默认设置
            return DEFAULT_SETTINGS
    
    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """更新系统设置"""
        try:
            # 读取现有配置
            existing_config = self._read_config_file()
            
            # 更新配置
            if 'models' in new_settings:
                existing_config['models'] = new_settings['models']
            
            if 'features' in new_settings:
                existing_config['features'] = new_settings['features']
            
            # 保存配置
            return self._write_config_file(existing_config)
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        try:
            config = self._read_config_file()
            models = []
            
            if config and 'models' in config and 'platforms' in config['models']:
                platforms = config['models']['platforms']
                
                for platform_name, platform_config in platforms.items():
                    enabled_models = platform_config.get('enabled_models', [])
                    
                    for model_name in enabled_models:
                        models.append(build_model_option(platform_name, platform_config, model_name))
            
            # 如果没有配置文件，返回默认模型
            if not models:
                models = DEFAULT_AVAILABLE_MODELS
            
            return models
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return DEFAULT_AVAILABLE_MODELS
    
    async def handle_get_settings(self, request):
        """处理获取设置请求"""
        try:
            settings = self.get_settings()
            logger.info(f"Returning settings: {settings}")
            
            # 确保返回的数据结构与前端期望的一致
            # 前端期望的结构是直接的settings对象，而不是嵌套在data.settings中
            return web.json_response(settings)
                
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return web.json_response(
                create_error_response(str(e)), 
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
    
    async def handle_update_settings(self, request):
        """处理更新设置请求"""
        try:
            data = await request.json()
            
            success = self.update_settings(data)
            
            if success:
                logger.info("Settings updated successfully")
                return web.json_response(create_success_response("Settings updated successfully"))
            else:
                return web.json_response(
                    create_error_response("Failed to update settings"), 
                    status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
                )
                
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return web.json_response(
                create_error_response(str(e)), 
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
    
    async def handle_test_api_connection(self, request):
        """处理API连接测试请求"""
        try:
            data = await request.json()
            platform = data.get('platform')
            api_key = data.get('api_key')
            api_base = data.get('api_base')
            
            if not platform or not api_key:
                return web.json_response(
                    create_error_response('Platform and API key are required'), 
                    status=HTTP_STATUS['BAD_REQUEST']
                )
            
            # 测试连接
            success, error = await self.connection_tester.test_connection(platform, api_key, api_base)
            
            if success:
                return web.json_response(
                    create_success_response(f'{platform} connection successful')
                )
            else:
                return web.json_response(
                    create_error_response(error), 
                    status=HTTP_STATUS['BAD_REQUEST']
                )
                
        except Exception as e:
            logger.error(f"Error testing API connection: {e}")
            return web.json_response(
                create_error_response(str(e)), 
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
    
    async def handle_get_available_models(self, request):
        """处理获取可用模型列表请求"""
        try:
            models = self.get_available_models()
            return web.json_response(create_success_response(models=models))
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return web.json_response(
                create_error_response(str(e)), 
                status=HTTP_STATUS['INTERNAL_SERVER_ERROR']
            )
