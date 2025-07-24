"""
Enhanced Models - 增强的大模型调用模块
提供企业级的模型调用接口，包含错误处理、健康监控、重试机制等
与前端完全兼容，不破坏现有功能
"""

import asyncio
import json
import time
import logging
import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime

# 导入现有的基础类
from .Models import ModelBase, ModelConfig, ModelResponse


class ErrorType(Enum):
    """错误类型枚举"""
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_UNHEALTHY = "MODEL_UNHEALTHY"
    MODEL_CALL_FAILED = "MODEL_CALL_FAILED"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    API_KEY_INVALID = "API_KEY_INVALID"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SYSTEM_ERROR = "SYSTEM_ERROR"


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True


@dataclass
class CircuitConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


@dataclass
class RateLimit:
    """限流配置"""
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000


@dataclass
class EnhancedModelConfig(ModelConfig):
    """增强的模型配置"""
    # 网络配置
    max_connections: int = 10
    connection_timeout: float = 30.0
    read_timeout: float = 60.0
    
    # 重试配置
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    
    # 熔断配置
    circuit_config: CircuitConfig = field(default_factory=CircuitConfig)
    
    # 限流配置
    rate_limit: RateLimit = field(default_factory=RateLimit)
    
    # 健康检查配置
    health_check_interval: float = 30.0
    health_check_timeout: float = 10.0


@dataclass
class HealthStatus:
    """健康状态"""
    is_healthy: bool
    error: Optional[str] = None
    response_time: Optional[float] = None
    last_check: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_healthy": self.is_healthy,
            "error": self.error,
            "response_time": self.response_time,
            "last_check": self.last_check,
            "consecutive_failures": self.consecutive_failures
        }


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class ModelError(Exception):
    """模型错误基类"""
    def __init__(self, message: str, error_type: ErrorType, model_type: str = "unknown", details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_type = error_type
        self.model_type = model_type
        self.details = details or {}
        self.timestamp = time.time()


class ModelNotFoundError(ModelError):
    """模型未找到错误"""
    def __init__(self, message: str, model_type: str = "unknown"):
        super().__init__(message, ErrorType.MODEL_NOT_FOUND, model_type)


class ModelUnavailableError(ModelError):
    """模型不可用错误"""
    def __init__(self, message: str, model_type: str = "unknown", details: Dict[str, Any] = None):
        super().__init__(message, ErrorType.MODEL_UNHEALTHY, model_type, details)


class CircuitBreakerOpenError(ModelError):
    """熔断器开启错误"""
    def __init__(self, message: str, model_type: str = "unknown"):
        super().__init__(message, ErrorType.MODEL_UNHEALTHY, model_type)


class RetryManager:
    """智能重试管理器"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs):
        """执行带重试的函数"""
        last_error = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not self._should_retry(e, attempt):
                    break
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
        
        raise last_error
    
    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        # 网络错误、超时错误、服务器错误可以重试
        retryable_errors = (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ConnectionError,
        )
        
        if isinstance(error, retryable_errors):
            return True
        
        # HTTP状态码判断
        if hasattr(error, 'status_code'):
            # 5xx服务器错误可以重试
            if 500 <= error.status_code < 600:
                return True
            # 429限流错误可以重试
            if error.status_code == 429:
                return True
        
        # 检查错误消息中的关键词
        error_msg = str(error).lower()
        retryable_keywords = ['timeout', 'connection', 'network', 'temporary', 'rate limit']
        if any(keyword in error_msg for keyword in retryable_keywords):
            return True
        
        return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算重试延迟（指数退避 + 随机抖动）"""
        delay = self.config.base_delay * (self.config.backoff_factor ** attempt)
        delay = min(delay, self.config.max_delay)
        
        # 添加随机抖动，避免雷群效应
        if self.config.jitter:
            import random
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        return delay


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, config: CircuitConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0
        self.logger = logging.getLogger(__name__)
    
    async def call(self, func: Callable, *args, **kwargs):
        """通过熔断器调用函数"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise CircuitBreakerOpenError("Circuit breaker HALF_OPEN call limit exceeded")
            self.half_open_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置熔断器"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.config.recovery_timeout
        )
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.logger.info("Circuit breaker reset to CLOSED")
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class HealthMonitor:
    """健康监控器"""
    
    def __init__(self):
        self.health_cache: Dict[str, HealthStatus] = {}
        self.cache_ttl = 30  # 健康状态缓存30秒
        self.logger = logging.getLogger(__name__)
    
    async def check_health(self, adapter: 'EnhancedModelAdapter') -> HealthStatus:
        """检查适配器健康状态"""
        model_key = f"{adapter.__class__.__name__}_{adapter.config.model_name}"
        
        # 检查缓存
        if model_key in self.health_cache:
            cached_status = self.health_cache[model_key]
            if time.time() - cached_status.last_check < self.cache_ttl:
                return cached_status
        
        # 执行健康检查
        try:
            start_time = time.time()
            
            # 发送简单的测试请求
            test_messages = [{"role": "user", "content": "test"}]
            
            # 使用较短的超时时间进行健康检查
            await asyncio.wait_for(
                adapter._call_api_direct(test_messages, max_tokens=1, temperature=0.1),
                timeout=adapter.config.health_check_timeout
            )
            
            response_time = time.time() - start_time
            
            status = HealthStatus(
                is_healthy=True,
                response_time=response_time,
                consecutive_failures=0
            )
            
        except Exception as e:
            # 获取之前的失败次数
            prev_failures = self.health_cache.get(model_key, HealthStatus(False)).consecutive_failures
            
            status = HealthStatus(
                is_healthy=False,
                error=str(e),
                consecutive_failures=prev_failures + 1
            )
        
        # 更新缓存
        self.health_cache[model_key] = status
        return status


class ErrorReporter:
    """统一错误报告器"""
    
    def __init__(self):
        self.websocket_handler = None
        self.logger = logging.getLogger(__name__)
    
    def set_websocket_handler(self, handler):
        """设置WebSocket处理器用于前端通知"""
        self.websocket_handler = handler
    
    async def report_error(self, error_type: str, error_message: str, 
                          model_type: str, details: Dict[str, Any] = None):
        """报告错误到服务器日志和前端"""
        
        error_info = {
            "error_type": error_type,
            "error_message": error_message,
            "model_type": model_type,
            "timestamp": time.time(),
            "details": details or {}
        }
        
        # 1. 记录到服务器日志
        self.logger.error(f"Model Error [{error_type}]: {error_message}", extra={
            "model_type": model_type,
            "details": details
        })
        
        # 2. 发送到前端（使用现有的error消息格式）
        if self.websocket_handler:
            await self.websocket_handler.broadcast_to_all({
                'type': 'error',  # 使用前端已识别的error类型
                'message': self._format_user_friendly_error(error_info),
                'error_details': error_info  # 可选的详细信息
            })
    
    def _format_user_friendly_error(self, error_info: Dict[str, Any]) -> str:
        """格式化用户友好的错误消息"""
        error_type = error_info['error_type']
        model_type = error_info['model_type']
        
        # 用户友好的错误消息映射
        friendly_messages = {
            'MODEL_NOT_FOUND': f'模型 "{model_type}" 未配置或不存在',
            'MODEL_UNHEALTHY': f'模型 "{model_type}" 当前不可用，请稍后重试',
            'MODEL_CALL_FAILED': f'模型 "{model_type}" 调用失败，请检查网络连接',
            'MODEL_TIMEOUT': f'模型 "{model_type}" 响应超时，请稍后重试',
            'API_KEY_INVALID': f'模型 "{model_type}" 的API密钥无效，请检查设置',
            'RATE_LIMIT_EXCEEDED': f'模型 "{model_type}" 请求频率过高，请稍后重试',
            'QUOTA_EXCEEDED': f'模型 "{model_type}" 配额已用完，请检查账户余额',
            'CONNECTION_ERROR': f'无法连接到模型 "{model_type}"，请检查网络',
            'SYSTEM_ERROR': f'系统错误，请联系管理员'
        }
        
        return friendly_messages.get(error_type, error_info['error_message'])


class EnhancedModelAdapter(ModelBase):
    """增强的模型适配器基类"""
    
    def __init__(self, model_id: str, config: EnhancedModelConfig):
        super().__init__(model_id, config)
        self.config = config  # 覆盖为增强配置
        
        # 初始化组件
        self.retry_manager = RetryManager(config.retry_config)
        self.circuit_breaker = CircuitBreaker(config.circuit_config)
        self.health_monitor = HealthMonitor()
        
        # HTTP客户端配置
        self.connector = None
        self.session = None
        
        self.logger = logging.getLogger(__name__)
    
    async def _initialize_http_client(self):
        """初始化HTTP客户端"""
        if self.session is None:
            # 配置连接器
            self.connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_connections,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            
            # 配置超时
            timeout = aiohttp.ClientTimeout(
                total=self.config.read_timeout,
                connect=self.config.connection_timeout
            )
            
            # 创建会话
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=timeout
            )
    
    async def _cleanup_http_client(self):
        """清理HTTP客户端"""
        if self.session:
            await self.session.close()
            self.session = None
        if self.connector:
            await self.connector.close()
            self.connector = None
    
    async def generate(self, prompt: str, context=None, **kwargs) -> str:
        """增强的生成方法"""
        try:
            # 初始化HTTP客户端
            await self._initialize_http_client()
            
            # 格式化消息
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
            
            # 通过熔断器和重试机制调用API
            response = await self.circuit_breaker.call(
                self.retry_manager.execute_with_retry,
                self._call_api_direct,
                messages,
                **call_params
            )
            
            self.call_count += 1
            self.total_tokens += response.usage.get('total_tokens', 0)
            
            self.logger.info(f"Model response received", {
                'model': response.model,
                'tokens': response.usage,
                'finish_reason': response.finish_reason
            })
            
            return response.content
            
        except Exception as e:
            # 分类和报告错误
            error_type = self._classify_error(e)
            
            # 创建ModelError
            if not isinstance(e, ModelError):
                e = ModelError(str(e), error_type, self.config.model_name)
            
            self.logger.error(f"Model generation failed: {e}")
            raise e
        finally:
            # 注意：不在这里清理HTTP客户端，因为可能会被重复使用
            pass
    
    async def _call_api_direct(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """直接调用API（由子类实现）"""
        return await self._call_api(messages, **kwargs)
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        if isinstance(error, ModelError):
            return error.error_type
        
        error_msg = str(error).lower()
        
        if isinstance(error, asyncio.TimeoutError) or 'timeout' in error_msg:
            return ErrorType.MODEL_TIMEOUT
        elif isinstance(error, ConnectionError) or 'connection' in error_msg:
            return ErrorType.CONNECTION_ERROR
        elif 'api key' in error_msg or 'unauthorized' in error_msg:
            return ErrorType.API_KEY_INVALID
        elif 'quota' in error_msg or 'limit' in error_msg:
            return ErrorType.QUOTA_EXCEEDED
        elif 'rate limit' in error_msg:
            return ErrorType.RATE_LIMIT_EXCEEDED
        else:
            return ErrorType.MODEL_CALL_FAILED
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._initialize_http_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._cleanup_http_client()


class EnhancedZhipuAIAdapter(EnhancedModelAdapter):
    """增强的智谱AI适配器"""
    
    def __init__(self, model_id: str = "enhanced_zhipuai", config: Optional[EnhancedModelConfig] = None):
        if config is None:
            config = EnhancedModelConfig(
                model_name="glm-4",
                api_key="",
                api_base="https://open.bigmodel.cn/api/paas/v4",
                timeout=120,
                retry_config=RetryConfig(max_attempts=3, base_delay=2.0),
                circuit_config=CircuitConfig(failure_threshold=3, recovery_timeout=60.0)
            )
        super().__init__(model_id, config)
        
        # 智谱AI特有的客户端
        self.zhipu_client = None
        self.openai_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化多种客户端"""
        # 1. 优先使用zhipuai官方SDK
        try:
            from zhipuai import ZhipuAI
            self.zhipu_client = ZhipuAI(api_key=self.config.api_key)
            self.logger.info("ZhipuAI official SDK initialized")
        except ImportError:
            self.logger.warning("zhipuai SDK not available")
        
        # 2. 备用OpenAI兼容客户端
        try:
            import openai
            self.openai_client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout
            )
            self.logger.info("OpenAI compatible client initialized")
        except ImportError:
            self.logger.warning("openai SDK not available")
    
    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """多策略API调用"""
        strategies = [
            ("zhipu_sdk", self._call_with_zhipu_sdk),
            ("openai_compatible", self._call_with_openai_compatible),
            ("http_direct", self._call_with_http_direct)
        ]
        
        last_error = None
        for strategy_name, strategy_func in strategies:
            try:
                self.logger.debug(f"Trying strategy: {strategy_name}")
                return await strategy_func(messages, **kwargs)
            except Exception as e:
                self.logger.warning(f"Strategy {strategy_name} failed: {e}")
                last_error = e
                continue
        
        raise ModelError(f"All strategies failed. Last error: {last_error}", 
                        ErrorType.MODEL_CALL_FAILED, self.config.model_name)
    
    async def _call_with_zhipu_sdk(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """使用zhipuai官方SDK"""
        if not self.zhipu_client:
            raise RuntimeError("ZhipuAI SDK not available")
        
        # 构建请求参数
        params = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "top_p": kwargs.get('top_p', self.config.top_p),
            "stream": kwargs.get('stream', False)
        }
        
        # 添加工具调用支持
        if kwargs.get('tools'):
            params["tools"] = kwargs['tools']
            params["tool_choice"] = kwargs.get('tool_choice', "auto")
        
        # 在线程池中执行同步调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.zhipu_client.chat.completions.create(**params)
        )
        
        return self._parse_zhipu_response(response)
    
    async def _call_with_openai_compatible(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """使用OpenAI兼容接口"""
        if not self.openai_client:
            raise RuntimeError("OpenAI compatible client not available")
        
        # 构建请求参数
        params = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "top_p": kwargs.get('top_p', self.config.top_p),
            "stream": kwargs.get('stream', False)
        }
        
        # 在线程池中执行同步调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.openai_client.chat.completions.create(**params)
        )
        
        return self._parse_openai_response(response)
    
    async def _call_with_http_direct(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """直接HTTP调用"""
        if not self.session:
            await self._initialize_http_client()
        
        url = f"{self.config.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "top_p": kwargs.get('top_p', self.config.top_p),
            "stream": False
        }
        
        async with self.session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise ModelError(f"HTTP {resp.status}: {error_text}", 
                               ErrorType.MODEL_CALL_FAILED, self.config.model_name)
            
            data = await resp.json()
            return self._parse_http_response(data)
    
    def _parse_zhipu_response(self, response) -> ModelResponse:
        """解析zhipuai SDK响应"""
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
    
    def _parse_openai_response(self, response) -> ModelResponse:
        """解析OpenAI兼容响应"""
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
    
    def _parse_http_response(self, data: Dict[str, Any]) -> ModelResponse:
        """解析HTTP响应"""
        choice = data['choices'][0]
        return ModelResponse(
            content=choice['message']['content'],
            model=data['model'],
            usage=data.get('usage', {}),
            finish_reason=choice.get('finish_reason', 'stop'),
            metadata={'api': 'zhipuai', 'sdk': 'http_direct'}
        )


class EnhancedOpenAIAdapter(EnhancedModelAdapter):
    """增强的OpenAI适配器"""
    
    def __init__(self, model_id: str = "enhanced_openai", config: Optional[EnhancedModelConfig] = None):
        if config is None:
            config = EnhancedModelConfig(
                model_name="gpt-3.5-turbo",
                api_key="",
                api_base="https://api.openai.com/v1",
                retry_config=RetryConfig(max_attempts=3, base_delay=1.0),
                circuit_config=CircuitConfig(failure_threshold=5, recovery_timeout=60.0)
            )
        super().__init__(model_id, config)
        
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化OpenAI客户端"""
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout
            )
            self.logger.info("OpenAI client initialized")
        except ImportError:
            self.logger.warning("OpenAI SDK not available")
    
    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """调用OpenAI API"""
        if self.client:
            return await self._call_with_sdk(messages, **kwargs)
        else:
            return await self._call_with_http(messages, **kwargs)
    
    async def _call_with_sdk(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """使用OpenAI SDK调用"""
        params = {
            'model': self.config.model_name,
            'messages': messages,
            'temperature': kwargs.get('temperature', self.config.temperature),
            'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
            'top_p': kwargs.get('top_p', self.config.top_p),
            'frequency_penalty': kwargs.get('frequency_penalty', self.config.frequency_penalty),
            'presence_penalty': kwargs.get('presence_penalty', self.config.presence_penalty),
        }
        
        # 添加自定义参数
        params.update(self.config.custom_params)
        
        # 在线程池中执行同步调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(**params)
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
            metadata={'api': 'openai', 'sdk': 'openai'}
        )
    
    async def _call_with_http(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """使用HTTP直接调用"""
        if not self.session:
            await self._initialize_http_client()
        
        url = f"{self.config.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "top_p": kwargs.get('top_p', self.config.top_p),
            "frequency_penalty": kwargs.get('frequency_penalty', self.config.frequency_penalty),
            "presence_penalty": kwargs.get('presence_penalty', self.config.presence_penalty),
        }
        
        async with self.session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise ModelError(f"HTTP {resp.status}: {error_text}", 
                               ErrorType.MODEL_CALL_FAILED, self.config.model_name)
            
            data = await resp.json()
            choice = data['choices'][0]
            return ModelResponse(
                content=choice['message']['content'],
                model=data['model'],
                usage=data.get('usage', {}),
                finish_reason=choice.get('finish_reason', 'stop'),
                metadata={'api': 'openai', 'sdk': 'http_direct'}
            )


class EnhancedAiHubMixAdapter(EnhancedModelAdapter):
    """增强的AiHubMix适配器"""
    
    def __init__(self, model_id: str = "enhanced_aihubmix", config: Optional[EnhancedModelConfig] = None):
        if config is None:
            config = EnhancedModelConfig(
                model_name="gpt-4o-mini",
                api_key="",
                api_base="https://aihubmix.com/v1",
                retry_config=RetryConfig(max_attempts=3, base_delay=1.0),
                circuit_config=CircuitConfig(failure_threshold=5, recovery_timeout=60.0)
            )
        super().__init__(model_id, config)
        
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化AiHubMix客户端"""
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout
            )
            self.logger.info("AiHubMix client initialized")
        except ImportError:
            self.logger.warning("OpenAI SDK not available for AiHubMix")
    
    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """调用AiHubMix API"""
        if self.client:
            return await self._call_with_sdk(messages, **kwargs)
        else:
            return await self._call_with_http(messages, **kwargs)
    
    async def _call_with_sdk(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """使用OpenAI SDK调用AiHubMix"""
        params = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "top_p": kwargs.get('top_p', self.config.top_p),
            "stream": kwargs.get('stream', False)
        }
        
        # AiHubMix特有功能
        if kwargs.get('web_search_options'):
            params['web_search_options'] = kwargs['web_search_options']
        
        # 在线程池中执行同步调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(**params)
        )
        
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
            metadata={'api': 'aihubmix', 'sdk': 'openai_compatible'}
        )
    
    async def _call_with_http(self, messages: List[Dict[str, str]], **kwargs) -> ModelResponse:
        """使用HTTP直接调用"""
        if not self.session:
            await self._initialize_http_client()
        
        url = f"{self.config.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "top_p": kwargs.get('top_p', self.config.top_p),
            "stream": False
        }
        
        # AiHubMix特有功能
        if kwargs.get('web_search_options'):
            payload['web_search_options'] = kwargs['web_search_options']
        
        async with self.session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise ModelError(f"HTTP {resp.status}: {error_text}", 
                               ErrorType.MODEL_CALL_FAILED, self.config.model_name)
            
            data = await resp.json()
            choice = data['choices'][0]
            return ModelResponse(
                content=choice['message']['content'],
                model=data['model'],
                usage=data.get('usage', {}),
                finish_reason=choice.get('finish_reason', 'stop'),
                metadata={'api': 'aihubmix', 'sdk': 'http_direct'}
            )
