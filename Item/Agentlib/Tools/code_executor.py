"""
CodeExecutorTool - 代码执行工具
安全地执行Python代码片段
"""

import sys
import io
import traceback
import contextlib
from typing import Dict, Any, Optional, Tuple
import ast

from .base_tool import BaseTool, ToolResult


class CodeExecutorTool(BaseTool):
    """代码执行工具 - 执行Python代码"""
    
    def __init__(self, tool_id: str = "code_executor"):
        super().__init__(
            tool_id,
            "code_executor",
            "安全地执行Python代码片段"
        )
        
        # 安全的内置函数白名单
        self.safe_builtins = {
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'chr', 'dict',
            'divmod', 'enumerate', 'filter', 'float', 'format', 'hex',
            'int', 'isinstance', 'len', 'list', 'map', 'max', 'min',
            'oct', 'ord', 'pow', 'print', 'range', 'reversed', 'round',
            'set', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip'
        }
        
        # 允许的模块
        self.allowed_modules = {
            'math', 'random', 'datetime', 'json', 're', 'collections',
            'itertools', 'functools', 'string'
        }
    
    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "code": {
                "type": "string",
                "description": "要执行的Python代码",
                "required": True
            },
            "timeout": {
                "type": "number",
                "description": "执行超时时间（秒）",
                "required": False,
                "default": 5
            },
            "capture_output": {
                "type": "boolean",
                "description": "是否捕获输出",
                "required": False,
                "default": True
            }
        }
    
    async def _execute_tool(self, code: str, timeout: int = 5, capture_output: bool = True) -> ToolResult:
        """执行代码"""
        try:
            # 验证代码安全性
            is_safe, error_msg = self._validate_code_safety(code)
            if not is_safe:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"代码安全检查失败：{error_msg}"
                )
            
            # 准备执行环境
            exec_globals = self._prepare_execution_environment()
            
            # 捕获输出
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(error_buffer):
                try:
                    # 执行代码
                    exec(code, exec_globals)
                    
                    # 获取输出
                    stdout = output_buffer.getvalue()
                    stderr = error_buffer.getvalue()
                    
                    # 提取结果变量（如果有）
                    result_vars = {}
                    for var_name, var_value in exec_globals.items():
                        if not var_name.startswith('__') and var_name not in self.allowed_modules:
                            try:
                                # 只保存可序列化的值
                                str(var_value)  # 测试是否可以转换为字符串
                                result_vars[var_name] = var_value
                            except:
                                result_vars[var_name] = f"<{type(var_value).__name__} object>"
                    
                    return ToolResult(
                        success=True,
                        data={
                            "output": stdout if capture_output else None,
                            "error_output": stderr if stderr and capture_output else None,
                            "variables": result_vars,
                            "code_lines": len(code.strip().split('\n'))
                        }
                    )
                    
                except Exception as e:
                    # 获取详细的错误信息
                    error_trace = traceback.format_exc()
                    
                    return ToolResult(
                        success=False,
                        data={
                            "output": output_buffer.getvalue() if capture_output else None,
                            "error_output": error_buffer.getvalue() if capture_output else None
                        },
                        error=f"执行错误：{str(e)}\n{error_trace if capture_output else ''}"
                    )
                    
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"代码执行环境错误：{str(e)}"
            )
    
    def _validate_code_safety(self, code: str) -> Tuple[bool, Optional[str]]:
        """验证代码安全性"""
        # 禁止的关键字
        forbidden_keywords = {
            '__import__', 'eval', 'exec', 'compile', 'open',
            'file', 'input', 'raw_input', 'execfile',
            'globals', 'locals', 'vars', 'dir'
        }
        
        # 禁止的模块
        forbidden_modules = {
            'os', 'sys', 'subprocess', 'socket', 'requests',
            'urllib', 'pickle', 'shelve', 'tempfile', 'shutil'
        }
        
        try:
            # 解析代码为AST
            tree = ast.parse(code)
            
            # 检查导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if module_name not in self.allowed_modules:
                            return False, f"不允许导入模块：{module_name}"
                
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module.split('.')[0] if node.module else ''
                    if module_name not in self.allowed_modules:
                        return False, f"不允许从模块导入：{module_name}"
                
                elif isinstance(node, ast.Name):
                    if node.id in forbidden_keywords:
                        return False, f"不允许使用关键字：{node.id}"
            
            # 检查代码文本中的危险模式
            code_lower = code.lower()
            for keyword in forbidden_keywords:
                if keyword in code_lower:
                    return False, f"代码中包含禁止的关键字：{keyword}"
            
            for module in forbidden_modules:
                if module in code_lower:
                    return False, f"代码中包含禁止的模块：{module}"
            
            return True, None
            
        except SyntaxError as e:
            return False, f"语法错误：{str(e)}"
        except Exception as e:
            return False, f"代码分析错误：{str(e)}"
    
    def _prepare_execution_environment(self) -> Dict[str, Any]:
        """准备执行环境"""
        # 创建受限的内置函数字典
        safe_builtins_dict = {}
        for name in self.safe_builtins:
            if hasattr(__builtins__, name):
                safe_builtins_dict[name] = getattr(__builtins__, name)
        
        # 导入允许的模块
        exec_globals = {'__builtins__': safe_builtins_dict}
        
        for module_name in self.allowed_modules:
            try:
                exec_globals[module_name] = __import__(module_name)
            except ImportError:
                pass  # 忽略不存在的模块
        
        return exec_globals
    
    def get_usage_example(self) -> str:
        """获取使用示例"""
        examples = [
            "code_executor(code='print(\"Hello, World!\")')",
            "code_executor(code='import math\\nresult = math.sqrt(16)\\nprint(f\"结果是: {result}\")')",
            "code_executor(code='numbers = [1, 2, 3, 4, 5]\\nsquares = [x**2 for x in numbers]\\nprint(squares)')",
            "code_executor(code='import datetime\\nnow = datetime.datetime.now()\\nprint(now.strftime(\"%Y-%m-%d %H:%M:%S\"))')"
        ]
        return "\n".join(examples)
