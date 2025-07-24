"""
Models - 大模型调用模块
提供统一的模型调用接口和不同平台的具体实现
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

from ..FlowTools.base_component import BaseComponent
from ..ContextEngineer.context_manager import StructuredContext


@dataclass
class ModelConfig:
    """模型配置"""
    model_name: str
    api_key: str
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 60
    retry_times: int = 3
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    """模型响应"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelBase(BaseComponent, ABC):
    """模型基类 - 定义统一的模型调用接口"""
    
    def __init__(self, model_id: str, config: ModelConfig):
        super().__init__(model_id, "model")
        self.config = config
        self.call_count = 0
        self.total_tokens = 0
        
        self.log_debug(f"Model initialized: {config.model_name}")
    
    @abstractmethod
    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """
        调用具体的API
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            模型响应
        """
        pass
    
    def _format_context_to_messages(self, prompt: str, context: Optional[StructuredContext] = None) -> List[Dict[str, str]]:
        """
        将上下文格式化为消息列表
        
        Args:
            prompt: 主提示词
            context: 结构化上下文
            
        Returns:
            消息列表
        """
        messages = []
        
        # 添加系统消息
        system_content = "你是一个智能助手。"
        
        if context:
            # 添加开发者指令
            if context.developer_instructions:
                system_content += "\n\n开发者指令：\n" + "\n".join(context.developer_instructions)
            
            # 开发者指令已在上面处理
            # 如果需要额外的系统信息，可以通过metadata或其他方式传递
        
        messages.append({"role": "system", "content": system_content})
        
        # 添加历史对话
        if context and context.conversation_history:
            for turn in context.conversation_history:
                if 'user' in turn:
                    messages.append({"role": "user", "content": turn['user']})
                if 'assistant' in turn:
                    messages.append({"role": "assistant", "content": turn['assistant']})
        
        # 添加工具结果
        if context and context.tool_results:
            tool_info = "工具调用结果：\n"
            for result in context.tool_results:
                tool_info += f"- {result.get('metadata', {}).get('tool_name', 'unknown')}: {result['content']}\n"
            messages.append({"role": "system", "content": tool_info})
        
        # 添加检索到的记忆
        if context and context.external_data:
            memory_info = "相关记忆：\n"
            for data in context.external_data:
                memory_info += f"- {data['content']}\n"
            messages.append({"role": "system", "content": memory_info})
        
        # 添加当前用户输入
        if context and context.user_input:
            messages.append({"role": "user", "content": context.user_input})
        else:
            # 如果没有上下文，直接使用prompt作为用户输入
            messages.append({"role": "user", "content": prompt})
        
        return messages
    
    async def generate(self, prompt: str, context: Optional[StructuredContext] = None, **kwargs) -> str:
        """
        生成响应
        
        Args:
            prompt: 提示词
            context: 结构化上下文
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        messages = self._format_context_to_messages(prompt, context)
        
        # 合并配置参数
        call_params = {
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'top_p': self.config.top_p,
            'frequency_penalty': self.config.frequency_penalty,
            'presence_penalty': self.config.presence_penalty,
        }
        call_params.update(kwargs)
        
        # 重试机制
        last_error = None
        for attempt in range(self.config.retry_times):
            try:
                self.log_debug(f"Calling model API (attempt {attempt + 1}/{self.config.retry_times})")
                
                response = await self._call_api(messages, **call_params)
                
                self.call_count += 1
                self.total_tokens += response.usage.get('total_tokens', 0)
                
                self.log_info(f"Model response received", {
                    'model': response.model,
                    'tokens': response.usage,
                    'finish_reason': response.finish_reason
                })
                
                return response.content
                
            except Exception as e:
                last_error = e
                self.log_warning(f"Model API call failed (attempt {attempt + 1})", {
                    'error': str(e)
                })
                
                if attempt < self.config.retry_times - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
        
        # 所有重试都失败
        self.log_error("All model API calls failed", last_error)
        raise last_error
    
    async def generate_stream(self, prompt: str, context: Optional[StructuredContext] = None, **kwargs):
        """
        流式生成响应
        
        Args:
            prompt: 提示词
            context: 结构化上下文
            **kwargs: 额外参数
            
        Yields:
            生成的文本片段
        """
        # 基础实现，子类可以覆盖以支持真正的流式输出
        response = await self.generate(prompt, context, **kwargs)
        
        # 模拟流式输出
        words = response.split()
        for i in range(0, len(words), 5):
            chunk = ' '.join(words[i:i+5])
            yield chunk
            await asyncio.sleep(0.1)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取模型调用统计"""
        return {
            'model_name': self.config.model_name,
            'call_count': self.call_count,
            'total_tokens': self.total_tokens,
            'average_tokens': self.total_tokens / self.call_count if self.call_count > 0 else 0
        }
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            prompt = input_data.get('prompt', '')
            context = input_data.get('context')
            
            # 同步包装异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(self.generate(prompt, context))
                return {'response': response, 'success': True}
            finally:
                loop.close()
        else:
            return {'error': 'Invalid input', 'success': False}


class OpenAIModel(ModelBase):
    """OpenAI模型实现"""
    
    def __init__(self, model_id: str = "openai_model", config: Optional[ModelConfig] = None):
        if config is None:
            config = ModelConfig(
                model_name="gpt-3.5-turbo",
                api_key="",  # 需要在配置中设置
                api_base="https://api.openai.com/v1"
            )
        super().__init__(model_id, config)
    
    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """调用OpenAI API"""
        try:
            import openai
            
            # 配置OpenAI客户端
            client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base
            )
            
            # 准备请求参数
            request_params = {
                'model': self.config.model_name,
                'messages': messages,
                'temperature': kwargs.get('temperature', self.config.temperature),
                'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
                'top_p': kwargs.get('top_p', self.config.top_p),
                'frequency_penalty': kwargs.get('frequency_penalty', self.config.frequency_penalty),
                'presence_penalty': kwargs.get('presence_penalty', self.config.presence_penalty),
            }
            
            # 添加自定义参数
            request_params.update(self.config.custom_params)
            
            # 调用API
            response = client.chat.completions.create(**request_params)
            
            # 解析响应
            choice = response.choices[0]
            return ModelResponse(
                content=choice.message.content,
                model=response.model,
                usage={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                finish_reason=choice.finish_reason,
                metadata={'api': 'openai'}
            )
            
        except ImportError:
            self.log_warning("OpenAI SDK not installed, using simulation")
            return await self._simulate_response(messages)
        except Exception as e:
            self.log_error(f"OpenAI API call failed: {e}")
            raise
    
    async def _simulate_response(self, messages: List[Dict[str, str]]) -> ModelResponse:
        """模拟响应（当SDK不可用时）"""
        await asyncio.sleep(0.5)
        
        response_content = f"这是来自{self.config.model_name}的模拟响应。"
        
        if messages:
            last_user_message = next((msg['content'] for msg in reversed(messages) if msg['role'] == 'user'), '')
            if last_user_message:
                response_content += f"\n\n您说：{last_user_message}\n\n我的回复：这是一个模拟的响应。请安装OpenAI SDK并配置API密钥以使用真实API。"
        
        return ModelResponse(
            content=response_content,
            model=self.config.model_name,
            usage={
                'prompt_tokens': sum(len(msg['content']) for msg in messages),
                'completion_tokens': len(response_content),
                'total_tokens': sum(len(msg['content']) for msg in messages) + len(response_content)
            },
            finish_reason="stop",
            metadata={'api': 'openai', 'simulated': True}
        )


class AiHubMixModel(ModelBase):
    """AiHubMix模型实现 - 使用OpenAI兼容接口"""
    
    def __init__(self, model_id: str = "aihubmix_model", config: Optional[ModelConfig] = None):
        if config is None:
            config = ModelConfig(
                model_name="gpt-4o-mini",
                api_key="",  # 需要设置AIHUBMIX_API_KEY
                api_base="https://aihubmix.com/v1"
            )
        super().__init__(model_id, config)
    
    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """调用AiHubMix API"""
        try:
            import openai
            
            # 配置OpenAI客户端使用AiHubMix端点
            client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base
            )
            
            # 准备请求参数
            request_params = {
                'model': self.config.model_name,
                'messages': messages,
                'temperature': kwargs.get('temperature', self.config.temperature),
                'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
                'top_p': kwargs.get('top_p', self.config.top_p),
            }
            
            # AiHubMix特有参数
            if 'web_search_options' in kwargs:
                request_params['web_search_options'] = kwargs['web_search_options']
            
            # 添加自定义参数
            request_params.update(self.config.custom_params)
            
            # 调用API
            response = client.chat.completions.create(**request_params)
            
            # 解析响应
            choice = response.choices[0]
            return ModelResponse(
                content=choice.message.content,
                model=response.model,
                usage={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                finish_reason=choice.finish_reason,
                metadata={'api': 'aihubmix'}
            )
            
        except ImportError:
            self.log_warning("OpenAI SDK not installed, using simulation")
            return await self._simulate_response(messages)
        except Exception as e:
            self.log_error(f"AiHubMix API call failed: {e}")
            raise
    
    async def _simulate_response(self, messages: List[Dict[str, str]]) -> ModelResponse:
        """模拟响应（当SDK不可用时）"""
        await asyncio.sleep(0.5)
        
        response_content = f"这是来自AiHubMix {self.config.model_name}的模拟响应。"
        
        if messages:
            last_user_message = next((msg['content'] for msg in reversed(messages) if msg['role'] == 'user'), '')
            if last_user_message:
                response_content += f"\n\n您说：{last_user_message}\n\n我的回复：这是一个模拟的响应。请安装OpenAI SDK并配置AIHUBMIX_API_KEY以使用真实的AiHubMix API。"
        
        return ModelResponse(
            content=response_content,
            model=self.config.model_name,
            usage={
                'prompt_tokens': sum(len(msg['content']) for msg in messages),
                'completion_tokens': len(response_content),
                'total_tokens': sum(len(msg['content']) for msg in messages) + len(response_content)
            },
            finish_reason="stop",
            metadata={'api': 'aihubmix', 'simulated': True}
        )


class ZhipuAIModel(ModelBase):
    """智谱AI模型实现"""
    
    def __init__(self, model_id: str = "zhipuai_model", config: Optional[ModelConfig] = None):
        if config is None:
            config = ModelConfig(
                model_name="glm-4",
                api_key="",  # 需要在配置中设置
                api_base="https://open.bigmodel.cn/api/paas/v4",
                timeout=120,  # 增加超时时间到120秒
                retry_times=3  # 保持3次重试
            )
        super().__init__(model_id, config)
    
    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """调用智谱AI API"""
        try:
            # 尝试使用zhipuai SDK
            try:
                from zhipuai import ZhipuAI
                
                # 创建客户端
                client = ZhipuAI(api_key=self.config.api_key)
                
                # 准备请求参数
                request_params = {
                    'model': self.config.model_name,
                    'messages': messages,
                    'temperature': kwargs.get('temperature', self.config.temperature),
                    'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
                    'top_p': kwargs.get('top_p', self.config.top_p),
                }
                
                # 添加自定义参数
                request_params.update(self.config.custom_params)
                
                # 调用API（同步调用，需要在异步环境中运行）
                import asyncio
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: client.chat.completions.create(**request_params)
                )
                
                # 解析响应
                choice = response.choices[0]
                return ModelResponse(
                    content=choice.message.content,
                    model=response.model,
                    usage={
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    },
                    finish_reason=choice.finish_reason,
                    metadata={'api': 'zhipuai', 'sdk': 'zhipuai'}
                )
                
            except ImportError:
                self.log_warning("ZhipuAI SDK not installed, trying OpenAI-compatible API")
                # 使用OpenAI兼容的方式调用
                return await self._call_openai_compatible_api(messages, **kwargs)
                
        except Exception as e:
            self.log_error(f"ZhipuAI API call failed: {e}")
            # 如果真实API调用失败，返回模拟响应作为降级
            return await self._simulate_response(messages)
    
    async def _call_openai_compatible_api(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """使用OpenAI兼容接口调用智谱AI API"""
        try:
            import openai
            import asyncio
            
            # 配置OpenAI客户端使用智谱AI端点
            client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout
            )
            
            # 准备请求参数
            request_params = {
                'model': self.config.model_name,
                'messages': messages,
                'temperature': kwargs.get('temperature', self.config.temperature),
                'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
                'top_p': kwargs.get('top_p', self.config.top_p),
            }
            
            # 添加自定义参数
            request_params.update(self.config.custom_params)
            
            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(**request_params)
            )
            
            # 解析响应
            choice = response.choices[0]
            return ModelResponse(
                content=choice.message.content,
                model=response.model,
                usage={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                finish_reason=choice.finish_reason,
                metadata={'api': 'zhipuai', 'sdk': 'openai_compatible'}
            )
            
        except ImportError:
            self.log_warning("OpenAI SDK not installed, using simulation")
            return await self._simulate_response(messages)
        except Exception as e:
            self.log_error(f"OpenAI-compatible ZhipuAI API call failed: {e}")
            raise
    
    async def _simulate_response(self, messages: List[Dict[str, str]]) -> ModelResponse:
        """模拟响应（当SDK不可用或API调用失败时）"""
        await asyncio.sleep(0.5)
        
        response_content = f"这是来自{self.config.model_name}的模拟响应。"
        
        if messages:
            last_user_message = next((msg['content'] for msg in reversed(messages) if msg['role'] == 'user'), '')
            if last_user_message:
                response_content += f"\n\n您说：{last_user_message}\n\n我的回复：这是一个模拟的响应。请安装zhipuai SDK或OpenAI SDK并确保API密钥配置正确以使用真实的智谱AI API。"
        
        return ModelResponse(
            content=response_content,
            model=self.config.model_name,
            usage={
                'prompt_tokens': sum(len(msg['content']) for msg in messages),
                'completion_tokens': len(response_content),
                'total_tokens': sum(len(msg['content']) for msg in messages) + len(response_content)
            },
            finish_reason="stop",
            metadata={'api': 'zhipuai', 'simulated': True}
        )


class ModelFactory:
    """模型工厂 - 用于创建不同类型的模型实例"""
    
    _model_classes = {
        'openai': OpenAIModel,
        'aihubmix': AiHubMixModel,
        'zhipuai': ZhipuAIModel,
        'zhipu': ZhipuAIModel,  # 兼容性别名
    }
    
    @classmethod
    def create_model(cls, model_type: str, config: ModelConfig) -> ModelBase:
        """
        创建模型实例
        
        Args:
            model_type: 模型类型（openai, aihubmix, zhipuai, zhipu等）
            config: 模型配置
            
        Returns:
            模型实例
        """
        # 标准化模型类型名称
        normalized_type = cls._normalize_model_type(model_type)
        
        if normalized_type not in cls._model_classes:
            available_types = list(cls._model_classes.keys())
            raise ValueError(f"Unknown model type: {model_type}. Available types: {available_types}")
        
        model_class = cls._model_classes[normalized_type]
        return model_class(f"{normalized_type}_model", config)
    
    @classmethod
    def _normalize_model_type(cls, model_type: str) -> str:
        """标准化模型类型名称"""
        # 处理别名映射
        aliases = {
            'zhipu': 'zhipuai',  # zhipu是zhipuai的别名
        }
        return aliases.get(model_type.lower(), model_type.lower())
    
    @classmethod
    def register_model_class(cls, model_type: str, model_class: type):
        """注册新的模型类型"""
        if not issubclass(model_class, ModelBase):
            raise ValueError(f"Model class must inherit from ModelBase")
        
        cls._model_classes[model_type] = model_class
