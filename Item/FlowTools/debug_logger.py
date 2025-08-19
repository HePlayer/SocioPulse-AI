"""
DebugLogger - 统一的调试日志系统
提供结构化日志记录、性能监控和调试信息输出
"""

import logging
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class DebugLogger:
    """统一的调试日志器"""
    
    def __init__(self, component_name: str, log_level: str = "DEBUG", log_to_file: bool = True):
        self.component_name = component_name
        self.log_level = log_level
        self.log_to_file = log_to_file
        
        # 创建日志器
        self.logger = logging.getLogger(component_name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        if self.log_to_file:
            # 确保日志目录存在
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # 创建组件专用的日志文件
            log_file = log_dir / f"{self.component_name}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            
            # JSON格式化器用于文件
            file_handler.setFormatter(logging.Formatter('%(message)s'))
            file_handler.setLevel(getattr(logging, self.log_level.upper()))
            self.logger.addHandler(file_handler)
    
    def _create_log_entry(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建结构化日志条目"""
        return {
            'timestamp': datetime.now().isoformat(),
            'component': self.component_name,
            'level': level,
            'message': message,
            'data': extra_data or {},
            'thread_id': threading.current_thread().ident if 'threading' in globals() else None
        }
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """记录调试信息"""
        log_entry = self._create_log_entry('DEBUG', message, extra_data)
        
        # 控制台输出简化版本
        if extra_data:
            console_msg = f"{message} | Data: {json.dumps(extra_data, ensure_ascii=False, default=str)[:100]}"
        else:
            console_msg = message
        
        # 文件输出完整JSON
        if self.log_to_file:
            self.logger.debug(json.dumps(log_entry, ensure_ascii=False, default=str))
        else:
            self.logger.debug(console_msg)
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """记录一般信息"""
        log_entry = self._create_log_entry('INFO', message, extra_data)
        
        # 控制台和文件都输出INFO级别
        console_msg = f"[{self.component_name}] {message}"
        if extra_data:
            console_msg += f" | {json.dumps(extra_data, ensure_ascii=False, default=str)[:100]}"
        
        self.logger.info(console_msg)
        
        if self.log_to_file:
            # 文件中也记录完整JSON
            file_logger = logging.getLogger(f"{self.component_name}_file")
            if not file_logger.handlers:
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                log_file = log_dir / f"{self.component_name}_detailed.log"
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setFormatter(logging.Formatter('%(message)s'))
                file_logger.addHandler(file_handler)
                file_logger.setLevel(logging.DEBUG)
            
            file_logger.info(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """记录警告信息"""
        log_entry = self._create_log_entry('WARNING', message, extra_data)
        
        console_msg = f"⚠️  [{self.component_name}] {message}"
        if extra_data:
            console_msg += f" | {json.dumps(extra_data, ensure_ascii=False, default=str)[:100]}"
        
        self.logger.warning(console_msg)
        
        if self.log_to_file:
            self.logger.warning(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def error(self, message: str, error: Optional[Exception] = None, extra_data: Optional[Dict[str, Any]] = None):
        """记录错误信息"""
        error_data = extra_data or {}
        
        if error:
            error_data.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_details': getattr(error, '__dict__', {})
            })
        
        log_entry = self._create_log_entry('ERROR', message, error_data)
        
        # 控制台显示明显的错误信息
        console_msg = f"❌ [{self.component_name}] ERROR: {message}"
        if error:
            console_msg += f" | {type(error).__name__}: {str(error)}"
        
        self.logger.error(console_msg)
        
        if self.log_to_file:
            self.logger.error(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def critical(self, message: str, error: Optional[Exception] = None, extra_data: Optional[Dict[str, Any]] = None):
        """记录严重错误信息"""
        error_data = extra_data or {}
        
        if error:
            error_data.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_details': getattr(error, '__dict__', {})
            })
        
        log_entry = self._create_log_entry('CRITICAL', message, error_data)
        
        # 控制台显示严重错误
        console_msg = f"🚨 [{self.component_name}] CRITICAL: {message}"
        if error:
            console_msg += f" | {type(error).__name__}: {str(error)}"
        
        self.logger.critical(console_msg)
        
        if self.log_to_file:
            self.logger.critical(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def performance(self, operation: str, execution_time: float, extra_data: Optional[Dict[str, Any]] = None):
        """记录性能信息"""
        perf_data = {
            'operation': operation,
            'execution_time': execution_time,
            'performance_level': self._get_performance_level(execution_time)
        }
        
        if extra_data:
            perf_data.update(extra_data)
        
        # 根据执行时间决定日志级别
        if execution_time > 5.0:  # 超过5秒认为是性能问题
            self.warning(f"Slow operation: {operation} took {execution_time:.3f}s", perf_data)
        elif execution_time > 1.0:  # 超过1秒显示警告
            self.info(f"Operation: {operation} took {execution_time:.3f}s", perf_data)
        else:
            self.debug(f"Operation: {operation} took {execution_time:.3f}s", perf_data)
    
    def _get_performance_level(self, execution_time: float) -> str:
        """根据执行时间判断性能级别"""
        if execution_time < 0.1:
            return "EXCELLENT"
        elif execution_time < 0.5:
            return "GOOD"
        elif execution_time < 1.0:
            return "ACCEPTABLE"
        elif execution_time < 5.0:
            return "SLOW"
        else:
            return "VERY_SLOW"
    
    def log_system_info(self):
        """记录系统信息"""
        try:
            import psutil
            import platform
            
            system_info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
                'memory_available': f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
                'disk_usage': f"{psutil.disk_usage('/').percent}%"
            }
            
            self.info("System information logged", system_info)
            
        except ImportError:
            self.warning("psutil not available, system info logging disabled")
        except Exception as e:
            self.error("Failed to log system info", e)




# 全局日志器实例管理
_loggers: Dict[str, DebugLogger] = {}

def get_logger(component_name: str, log_level: str = "DEBUG") -> DebugLogger:
    """获取或创建日志器实例"""
    if component_name not in _loggers:
        _loggers[component_name] = DebugLogger(component_name, log_level)
    return _loggers[component_name]

def set_global_log_level(log_level: str):
    """设置全局日志级别"""
    for logger in _loggers.values():
        logger.logger.setLevel(getattr(logging, log_level.upper()))
