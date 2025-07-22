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
            
            # 测试简单的聊天API - 使用免费模型
            url = f"{api_base.rstrip('/')}/chat/completions"
            
            payload = {
                'model': 'glm-4-flash-250414',  # 使用免费模型进行测试
                'messages': [{'role': 'user', 'content': 'test'}],
                'max_tokens': 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=15) as response:
                    if response.status == 200:
                        return True, "Connection successful"
                    else:
                        error_text = await response.text()
                        # 提供更详细的错误信息
                        if response.status == 400:
                            return False, f"API请求错误 (400): 可能是API密钥无效或模型不可用 - {error_text}"
                        elif response.status == 401:
                            return False, f"认证失败 (401): API密钥无效或已过期 - {error_text}"
                        elif response.status == 402:
                            return False, f"余额不足 (402): 账户余额不足或已欠费 - {error_text}"
                        elif response.status == 429:
                            return False, f"请求频率限制 (429): 请求过于频繁，请稍后重试 - {error_text}"
                        else:
                            return False, f"HTTP {response.status}: {error_text}"
                        
        except Exception as e:
            return False, f"连接测试异常: {str(e)}"
    
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
        elif platform in ['zhipu', 'zhipuai']:  # 支持两种名称以保持兼容性
            return await self.test_zhipu_connection(api_key, api_base)
        else:
            return False, f'Unsupported platform: {platform}'
