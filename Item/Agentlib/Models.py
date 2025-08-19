import traceback
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
from .sdk_templates import RequestTemplateRegistry


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
        
        # 添加系统消息（房间约束优先）
        system_content = ""

        if context and context.developer_instructions:
            # 🚀 关键修改：检查是否包含房间主题约束，如果有则优先使用
            developer_content = "\n".join(context.developer_instructions)
            if "聊天室主题约束" in developer_content:
                # 房间约束存在时，直接使用开发者指令作为系统消息
                system_content = developer_content
            else:
                # 没有房间约束时，使用默认系统消息+开发者指令
                system_content = "你是一个智能助手。\n\n开发者指令：\n" + developer_content
        else:
            # 没有开发者指令时，使用默认系统消息
            system_content = "你是一个智能助手。"

        messages.append({"role": "system", "content": system_content})
        
        # 添加历史对话（支持发言者信息）
        if context and context.conversation_history:
            for turn in context.conversation_history:
                if 'user' in turn:
                    # 为用户消息添加发言者信息
                    sender_name = turn.get('sender_name', '用户')
                    content = f"[{sender_name}]：{turn['user']}"
                    messages.append({"role": "user", "content": content})
                if 'assistant' in turn:
                    # 为助手消息添加发言者信息
                    sender_name = turn.get('sender_name', 'Assistant')
                    content = f"[{sender_name}]：{turn['assistant']}"
                    messages.append({"role": "assistant", "content": content})
        
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
                # 记录详细错误信息
                error_details = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                }
                self.log_error(f"详细错误信息: {error_details}")
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
            # 记录详细错误信息
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            self.log_error(f"详细错误信息: {error_details}")
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
            
            # 🌐 处理模型名称（支持:surfing后缀启用搜索）
            model_name = self.config.model_name
            enable_surfing = kwargs.get('enable_surfing', False)

            # 如果传入了web_search_options或enable_surfing，自动添加:surfing后缀
            if (kwargs.get('web_search_options') or enable_surfing) and ':surfing' not in model_name:
                model_name = f"{model_name}:surfing"
                self.log_info(f"AiHubMix: 启用搜索模式，模型名修改为 {model_name}")

            # 准备请求参数
            request_params = {
                'model': model_name,
                'messages': messages,
                'temperature': kwargs.get('temperature', self.config.temperature),
                'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
                'top_p': kwargs.get('top_p', self.config.top_p),
            }

            # AiHubMix特有参数
            if 'web_search_options' in kwargs:
                request_params['web_search_options'] = kwargs['web_search_options']
                self.log_info(f"AiHubMix: 启用web_search_options - {kwargs['web_search_options']}")
            
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
            # 记录详细错误信息
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            self.log_error(f"详细错误信息: {error_details}")
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
            # 仅使用稳定的 zhipuai SDK
            return await self._call_zhipuai_sdk_fallback(messages, **kwargs)
        except Exception as e:
            # 记录详细错误信息
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            self.log_error(f"详细错误信息: {error_details}")
            error_msg = str(e).lower()
            self.log_error(f"ZhipuAI API call failed: {e}")

            # 🚨 检测联网功能相关错误并提供用户友好的反馈
            if 'quota' in error_msg or 'balance' in error_msg or 'insufficient' in error_msg:
                return ModelResponse(
                    content="[联网功能不可用：账户余额不足] 抱歉，我无法获取实时信息。请检查账户余额或联系管理员。我可以基于已有知识为您提供帮助。",
                    model=self.config.model_name,
                    usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    finish_reason='quota_exceeded',
                    metadata={'error': 'quota_exceeded', 'api': 'zhipu'}
                )
            elif 'tool' in error_msg and ('not supported' in error_msg or 'invalid' in error_msg):
                return ModelResponse(
                    content="[联网功能不可用：模型不支持] 抱歉，当前模型不支持联网搜索功能。我将基于已有知识为您回答。",
                    model=self.config.model_name,
                    usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    finish_reason='tool_not_supported',
                    metadata={'error': 'tool_not_supported', 'api': 'zhipu'}
                )
            elif 'api_key' in error_msg or 'unauthorized' in error_msg or 'invalid' in error_msg:
                return ModelResponse(
                    content="[联网功能不可用：API密钥问题] 抱歉，API密钥配置有问题。请联系管理员检查配置。",
                    model=self.config.model_name,
                    usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    finish_reason='api_key_invalid',
                    metadata={'error': 'api_key_invalid', 'api': 'zhipu'}
                )

            # 如果真实API调用失败，返回模拟响应作为降级
            return await self._simulate_response(messages)

    async def _call_zhipuai_sdk_fallback(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """使用zhipuai SDK作为备用方案"""
        try:
            from zhipuai import ZhipuAI

            # 创建客户端
            client = ZhipuAI(api_key=self.config.api_key)

            # 🌐 为 glm-4.5 系列专门设计的模板（与 glm-4 系列区分）
            if self.config.model_name.startswith('glm-4.5'):
                # 使用模板化构建请求参数
                template = RequestTemplateRegistry.get(self.config.model_name)
                request_params = template.build(self.config.model_name, messages, **kwargs)
                # 对于禁用联网场景，移除tools
                if kwargs.get('disable_web_search', False):
                    request_params.pop('tools', None)
                    self.log_info("ZhipuAI SDK: glm-4.5系列 SVR计算模式（禁用联网）")
                else:
                    self.log_info("ZhipuAI SDK: glm-4.5系列 对话模式（SDK内置浏览器）")
                # 不合并 custom_params，避免干扰
            elif self.config.model_name.startswith('glm-4'):
                # 使用模板化构建请求参数（glm-4 系列）
                template = RequestTemplateRegistry.get(self.config.model_name)
                request_params = template.build(self.config.model_name, messages, **kwargs)
                self.log_info("ZhipuAI SDK: glm-4系列 启用联网功能")
                # 允许外部自定义参数
                request_params.update(self.config.custom_params)
            else:
                # 其他智谱模型的默认配置
                request_params = {
                    'model': self.config.model_name,
                    'messages': messages,
                    'temperature': kwargs.get('temperature', self.config.temperature),
                    'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
                    'top_p': kwargs.get('top_p', self.config.top_p),
                }
                self.log_info("ZhipuAI SDK: 其他模型 默认配置")
                request_params.update(self.config.custom_params)

            # 调用API（记录glm-4.5系列请求参数，便于对比模板）
            if self.config.model_name.startswith('glm-4.5'):
                try:
                    self.log_info(f"GLM-4.5系列 请求参数: tools={request_params.get('tools')} messages={request_params.get('messages')}")
                except Exception:
                    pass
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(**request_params)
            )

            # 解析响应（健壮处理 usage 为空或字段差异）
            try:
                choice = response.choices[0]
            except Exception:
                self.log_warning("ZhipuAI SDK: 响应无 choices，使用空内容降级")
                choice = type("obj", (), {"message": type("obj", (), {"content": ""})(), "finish_reason": "stop"})()

            # 提取 usage
            usage_obj = getattr(response, 'usage', None)
            def _safe_int(v, default=0):
                try:
                    return int(v)
                except Exception:
                    return default
            if usage_obj is None:
                usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            else:
                # 兼容属性或字典
                prompt_tokens = getattr(usage_obj, 'prompt_tokens', None) if not isinstance(usage_obj, dict) else usage_obj.get('prompt_tokens')
                completion_tokens = getattr(usage_obj, 'completion_tokens', None) if not isinstance(usage_obj, dict) else usage_obj.get('completion_tokens')
                total_tokens = getattr(usage_obj, 'total_tokens', None) if not isinstance(usage_obj, dict) else usage_obj.get('total_tokens')
                usage = {
                    'prompt_tokens': _safe_int(prompt_tokens, 0),
                    'completion_tokens': _safe_int(completion_tokens, 0),
                    'total_tokens': _safe_int(total_tokens, 0)
                }

            return ModelResponse(
                content=getattr(choice.message, 'content', "") or "",
                model=getattr(response, 'model', self.config.model_name),
                usage=usage,
                finish_reason=getattr(choice, 'finish_reason', 'stop'),
                metadata={'api': 'zhipuai', 'sdk': 'zhipuai_fallback'}
            )

        except ImportError:
            self.log_warning("zhipuai SDK也未安装，尝试OpenAI兼容API")
            return await self._call_openai_compatible_api(messages, **kwargs)
        except Exception as e:
            # 记录详细错误信息
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            self.log_error(f"详细错误信息: {error_details}")
            error_msg = str(e).lower()
            self.log_error(f"ZhipuAI备用SDK调用失败: {e}")

            # 🚨 检测联网功能相关错误并提供用户友好的反馈
            if 'quota' in error_msg or 'balance' in error_msg or 'insufficient' in error_msg:
                return ModelResponse(
                    content="[联网功能不可用：账户余额不足] 抱歉，我无法获取实时信息。请检查账户余额或联系管理员。我可以基于已有知识为您提供帮助。",
                    model=self.config.model_name,
                    usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    finish_reason='quota_exceeded',
                    metadata={'error': 'quota_exceeded', 'api': 'zhipu_fallback'}
                )
            elif 'tool' in error_msg and ('not supported' in error_msg or 'invalid' in error_msg):
                return ModelResponse(
                    content="[联网功能不可用：模型不支持] 抱歉，当前模型不支持联网搜索功能。我将基于已有知识为您回答。",
                    model=self.config.model_name,
                    usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    finish_reason='tool_not_supported',
                    metadata={'error': 'tool_not_supported', 'api': 'zhipu_fallback'}
                )

            raise

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
            
            # 使用模板化构建请求参数（OpenAI兼容路径）
            template = RequestTemplateRegistry.get(self.config.model_name)
            request_params = template.build(self.config.model_name, messages, **kwargs)
            self.log_info(f"ZhipuAI OpenAI兼容模式: 启用联网功能")

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
            # 记录详细错误信息
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            self.log_error(f"详细错误信息: {error_details}")
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
        'zhipu': ZhipuAIModel,  # 标准标识符
        'zhipuai': ZhipuAIModel,  # 兼容性别名
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
        # 处理别名映射 - 统一使用zhipu作为标准标识符
        aliases = {
            'zhipuai': 'zhipu',  # zhipuai是zhipu的别名
        }
        return aliases.get(model_type.lower(), model_type.lower())
    
    @classmethod
    def register_model_class(cls, model_type: str, model_class: type):
        """注册新的模型类型"""
        if not issubclass(model_class, ModelBase):
            raise ValueError(f"Model class must inherit from ModelBase")
        
        cls._model_classes[model_type] = model_class
