"""
API连接测试模块
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class ConnectionTester:
    """API连接测试器"""
    
    @staticmethod
    async def test_openai_connection(api_key: str, api_base: str) -> Tuple[bool, str]:
        """测试OpenAI API连接"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 测试模型列表API
            url = f"{api_base.rstrip('/')}/models"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        return True, "Connection successful"
                    else:
                        error_text = await response.text()
                        return False, f"HTTP {response.status}: {error_text}"
                        
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    async def test_aihubmix_connection(api_key: str, api_base: str) -> Tuple[bool, str]:
        """测试AiHubMix API连接"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 测试模型列表API
            url = f"{api_base.rstrip('/')}/models"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        return True, "Connection successful"
                    else:
                        error_text = await response.text()
                        return False, f"HTTP {response.status}: {error_text}"
                        
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    async def test_zhipu_connection(api_key: str, api_base: str) -> Tuple[bool, str]:
        """测试智谱AI API连接"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 测试简单的聊天API
            url = f"{api_base.rstrip('/')}/chat/completions"
            
            payload = {
                'model': 'glm-4',
                'messages': [{'role': 'user', 'content': 'test'}],
                'max_tokens': 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                    if response.status == 200:
                        return True, "Connection successful"
                    else:
                        error_text = await response.text()
                        return False, f"HTTP {response.status}: {error_text}"
                        
        except Exception as e:
            return False, str(e)
    
    async def test_connection(self, platform: str, api_key: str, api_base: str) -> Tuple[bool, str]:
        """
        测试指定平台的API连接
        
        Args:
            platform: 平台名称
            api_key: API密钥
            api_base: API基础URL
            
        Returns:
            (success, error_message) 元组
        """
        if platform == 'openai':
            return await self.test_openai_connection(api_key, api_base)
        elif platform == 'aihubmix':
            return await self.test_aihubmix_connection(api_key, api_base)
        elif platform == 'zhipu':
            return await self.test_zhipu_connection(api_key, api_base)
        else:
            return False, f'Unsupported platform: {platform}'
