"""
BaseComponent - 所有系统组件的基类
提供统一的接口、调试功能和错误处理
"""

import time
import traceback
import psutil
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from .debug_logger import DebugLogger


@dataclass
class ComponentStats:
    """组件统计信息"""
    execution_count: int = 0
    total_execution_time: float = 0.0
    last_execution_time: Optional[float] = None
    error_count: int = 0
    last_error_time: Optional[float] = None
    memory_usage: float = 0.0
    created_at: float = field(default_factory=time.time)


class BaseComponent(ABC):
    """所有组件的基类"""
    
    def __init__(self, component_id: str, component_type: str = "base", debug_enabled: bool = True):
        self.component_id = component_id
        self.component_type = component_type
        self.debug_enabled = debug_enabled
        self.stats = ComponentStats()
        self.error_history: List[Dict[str, Any]] = []
        
        # 初始化调试日志器
        self.logger = DebugLogger(f"{component_type}_{component_id}", "DEBUG" if debug_enabled else "INFO")
        
        # 记录组件创建
        self.log_debug(f"Component {self.component_id} created", {
            'component_type': component_type,
            'debug_enabled': debug_enabled
        })
    
    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """所有组件的统一执行接口"""
        raise NotImplementedError("Subclasses must implement execute method")
    
    def safe_execute(self, input_data: Any) -> Dict[str, Any]:
        """安全执行包装器，提供统一的错误处理和性能监控"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            self.log_debug("Execution started", {
                'input_type': type(input_data).__name__,
                'input_preview': str(input_data)[:100] if input_data else None
            })
            
            # 执行核心逻辑
            result = self.execute(input_data)
            
            # 更新统计信息
            execution_time = time.time() - start_time
            self._update_success_stats(execution_time, start_memory)
            
            self.log_debug("Execution completed successfully", {
                'execution_time': execution_time,
                'result_type': type(result).__name__,
                'result_preview': str(result)[:100] if result else None
            })
            
            return {
                'success': True,
                'result': result,
                'execution_time': execution_time,
                'component_id': self.component_id
            }
            
        except Exception as e:
            # 处理错误
            execution_time = time.time() - start_time
            error_info = self._handle_error(e, input_data, execution_time)
            
            return {
                'success': False,
                'error': error_info,
                'execution_time': execution_time,
                'component_id': self.component_id
            }
    
    def _update_success_stats(self, execution_time: float, start_memory: float):
        """更新成功执行的统计信息"""
        self.stats.execution_count += 1
        self.stats.total_execution_time += execution_time
        self.stats.last_execution_time = execution_time
        self.stats.memory_usage = self._get_memory_usage() - start_memory
    
    def _handle_error(self, error: Exception, input_data: Any, execution_time: float) -> Dict[str, Any]:
        """处理错误并记录详细信息"""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': time.time(),
            'input_data': str(input_data)[:200] if input_data else None,
            'execution_time': execution_time
        }
        
        # 记录到错误历史
        self.error_history.append(error_info)
        if len(self.error_history) > 100:  # 限制错误历史长度
            self.error_history.pop(0)
        
        # 更新错误统计
        self.stats.error_count += 1
        self.stats.last_error_time = time.time()
        
        # 记录错误日志
        self.log_error(f"Execution failed: {str(error)}", error, {
            'input_data_preview': str(input_data)[:100] if input_data else None,
            'execution_time': execution_time
        })
        
        return error_info
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）"""
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def get_debug_info(self) -> Dict[str, Any]:
        """获取组件调试信息"""
        uptime = time.time() - self.stats.created_at
        avg_execution_time = (
            self.stats.total_execution_time / self.stats.execution_count 
            if self.stats.execution_count > 0 else 0
        )
        
        return {
            'component_id': self.component_id,
            'component_type': self.component_type,
            'uptime': uptime,
            'stats': {
                'execution_count': self.stats.execution_count,
                'error_count': self.stats.error_count,
                'success_rate': (
                    (self.stats.execution_count - self.stats.error_count) / self.stats.execution_count
                    if self.stats.execution_count > 0 else 1.0
                ),
                'avg_execution_time': avg_execution_time,
                'last_execution_time': self.stats.last_execution_time,
                'total_execution_time': self.stats.total_execution_time,
                'memory_usage': self.stats.memory_usage
            },
            'recent_errors': self.error_history[-5:] if self.error_history else [],
            'health_status': self._get_health_status()
        }
    
    def _get_health_status(self) -> str:
        """获取组件健康状态"""
        if self.stats.execution_count == 0:
            return "IDLE"
        
        error_rate = self.stats.error_count / self.stats.execution_count
        
        if error_rate == 0:
            return "HEALTHY"
        elif error_rate < 0.1:
            return "WARNING"
        else:
            return "ERROR"
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = ComponentStats()
        self.error_history.clear()
        self.log_debug("Statistics reset")
    
    def log_debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """记录调试信息"""
        if self.debug_enabled:
            self.logger.debug(message, extra_data)
    
    def log_error(self, message: str, error: Optional[Exception] = None, extra_data: Optional[Dict[str, Any]] = None):
        """记录错误信息"""
        self.logger.error(message, error, extra_data)
    
    def log_info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """记录一般信息"""
        self.logger.info(message, extra_data)
    
    def log_warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """记录警告信息"""
        self.logger.warning(message, extra_data)
    
    def __str__(self) -> str:
        return f"{self.component_type}({self.component_id})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.component_id}', type='{self.component_type}')"
