"""
BaseTool - 工具基类
定义所有工具的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import time

from ...FlowTools.base_component import BaseComponent


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool(BaseComponent, ABC):
    """工具基类"""
    
    def __init__(self, tool_id: str, tool_name: str, description: str = ""):
        super().__init__(tool_id, "tool")
        self.tool_name = tool_name
        self.description = description
        self.execution_count = 0
        self.total_execution_time = 0.0
        
        # 工具参数定义
        self.parameters = self._define_parameters()
        
        self.log_debug(f"Tool {tool_name} initialized")
    
    @abstractmethod
    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        定义工具参数
        
        Returns:
            参数定义字典，格式：
            {
                "param_name": {
                    "type": "string|number|boolean|object|array",
                    "description": "参数描述",
                    "required": True/False,
                    "default": 默认值（可选）
                }
            }
        """
        pass
    
    @abstractmethod
    async def _execute_tool(self, **kwargs) -> ToolResult:
        """
        执行工具的具体逻辑
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证参数
        
        Args:
            params: 参数字典
            
        Returns:
            (是否有效, 错误信息)
        """
        # 检查必需参数
        for param_name, param_def in self.parameters.items():
            if param_def.get('required', False) and param_name not in params:
                return False, f"Missing required parameter: {param_name}"
        
        # 检查参数类型
        for param_name, param_value in params.items():
            if param_name not in self.parameters:
                continue  # 忽略未定义的参数
            
            expected_type = self.parameters[param_name].get('type', 'any')
            if not self._check_type(param_value, expected_type):
                return False, f"Invalid type for parameter {param_name}: expected {expected_type}"
        
        return True, None
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查值的类型"""
        type_map = {
            'string': str,
            'number': (int, float),
            'boolean': bool,
            'object': dict,
            'array': list,
            'any': object
        }
        
        expected_python_type = type_map.get(expected_type, object)
        return isinstance(value, expected_python_type)
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        start_time = time.time()
        
        try:
            # 验证参数
            is_valid, error_msg = self.validate_parameters(kwargs)
            if not is_valid:
                self.log_warning(f"Invalid parameters for tool {self.tool_name}", {
                    'error': error_msg,
                    'params': kwargs
                })
                return ToolResult(
                    success=False,
                    data=None,
                    error=error_msg
                )
            
            # 填充默认值
            final_params = {}
            for param_name, param_def in self.parameters.items():
                if param_name in kwargs:
                    final_params[param_name] = kwargs[param_name]
                elif 'default' in param_def:
                    final_params[param_name] = param_def['default']
            
            self.log_debug(f"Executing tool {self.tool_name}", {
                'params': final_params
            })
            
            # 执行工具
            result = await self._execute_tool(**final_params)
            
            # 更新统计
            execution_time = time.time() - start_time
            self.execution_count += 1
            self.total_execution_time += execution_time
            
            # 添加执行时间到结果
            result.execution_time = execution_time
            
            if result.success:
                self.log_info(f"Tool {self.tool_name} executed successfully", {
                    'execution_time': f"{execution_time:.3f}s"
                })
            else:
                self.log_warning(f"Tool {self.tool_name} execution failed", {
                    'error': result.error,
                    'execution_time': f"{execution_time:.3f}s"
                })
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_error(f"Tool {self.tool_name} execution error", e)
            
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                execution_time=execution_time
            )
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            'id': self.component_id,
            'name': self.tool_name,
            'description': self.description,
            'parameters': self.parameters,
            'statistics': {
                'execution_count': self.execution_count,
                'total_execution_time': self.total_execution_time,
                'average_execution_time': self.total_execution_time / self.execution_count if self.execution_count > 0 else 0
            }
        }
    
    def get_usage_example(self) -> str:
        """获取使用示例"""
        params_example = {}
        for param_name, param_def in self.parameters.items():
            if param_def.get('required', False):
                params_example[param_name] = f"<{param_def.get('description', param_name)}>"
            elif 'default' in param_def:
                params_example[param_name] = param_def['default']
        
        return f"{self.tool_name}({', '.join(f'{k}={v}' for k, v in params_example.items())})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.component_id}, name={self.tool_name})"
