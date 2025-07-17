"""
CalculatorTool - 计算器工具
提供基本的数学计算功能
"""

import ast
import operator
import math
from typing import Dict, Any

from .base_tool import BaseTool, ToolResult


class CalculatorTool(BaseTool):
    """计算器工具 - 执行数学计算"""
    
    # 允许的操作符
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # 允许的函数
    ALLOWED_FUNCTIONS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'pow': pow,
        'pi': math.pi,
        'e': math.e,
    }
    
    def __init__(self, tool_id: str = "calculator"):
        super().__init__(
            tool_id,
            "calculator",
            "执行数学计算，支持基本运算和常用数学函数"
        )
    
    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式",
                "required": True
            },
            "precision": {
                "type": "number",
                "description": "结果的小数位数",
                "required": False,
                "default": 4
            }
        }
    
    async def _execute_tool(self, expression: str, precision: int = 4) -> ToolResult:
        """执行计算"""
        try:
            # 安全地解析和计算表达式
            result = self._safe_eval(expression)
            
            # 格式化结果
            if isinstance(result, float):
                formatted_result = round(result, precision)
            else:
                formatted_result = result
            
            return ToolResult(
                success=True,
                data={
                    "expression": expression,
                    "result": formatted_result,
                    "type": type(result).__name__
                },
                metadata={
                    "precision": precision
                }
            )
            
        except ZeroDivisionError:
            return ToolResult(
                success=False,
                data=None,
                error="除零错误：不能除以零"
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"数学错误：{str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"计算错误：{str(e)}"
            )
    
    def _safe_eval(self, expression: str) -> float:
        """
        安全地计算数学表达式
        
        Args:
            expression: 数学表达式字符串
            
        Returns:
            计算结果
        """
        # 解析表达式为AST
        try:
            node = ast.parse(expression, mode='eval')
        except SyntaxError:
            raise ValueError(f"无效的表达式语法: {expression}")
        
        # 验证并计算
        return self._eval_node(node.body)
    
    def _eval_node(self, node):
        """递归计算AST节点"""
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python 3.7
            return node.n
        elif isinstance(node, ast.Name):
            # 允许使用数学常量
            if node.id in self.ALLOWED_FUNCTIONS:
                return self.ALLOWED_FUNCTIONS[node.id]
            else:
                raise ValueError(f"不允许的变量: {node.id}")
        elif isinstance(node, ast.BinOp):
            # 二元操作
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPERATORS:
                raise ValueError(f"不允许的操作符: {op_type.__name__}")
            
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.ALLOWED_OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            # 一元操作
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPERATORS:
                raise ValueError(f"不允许的操作符: {op_type.__name__}")
            
            operand = self._eval_node(node.operand)
            return self.ALLOWED_OPERATORS[op_type](operand)
        elif isinstance(node, ast.Call):
            # 函数调用
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in self.ALLOWED_FUNCTIONS:
                    raise ValueError(f"不允许的函数: {func_name}")
                
                func = self.ALLOWED_FUNCTIONS[func_name]
                args = [self._eval_node(arg) for arg in node.args]
                
                # 处理特殊情况
                if func_name == 'log' and len(args) == 2:
                    # log(x, base)
                    return math.log(args[0], args[1])
                
                return func(*args)
            else:
                raise ValueError("不支持的函数调用格式")
        elif isinstance(node, ast.List):
            # 列表（用于sum, min, max等）
            return [self._eval_node(elem) for elem in node.elts]
        else:
            raise ValueError(f"不支持的表达式类型: {type(node).__name__}")
    
    def get_usage_example(self) -> str:
        """获取使用示例"""
        examples = [
            "calculator(expression='2 + 2')",
            "calculator(expression='sqrt(16) + pow(2, 3)')",
            "calculator(expression='sin(pi/2) * cos(0)')",
            "calculator(expression='log(100, 10)', precision=2)"
        ]
        return "\n".join(examples)
