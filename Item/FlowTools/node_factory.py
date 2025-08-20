"""
NodeFactory - 节点工厂类
负责创建和管理各种类型的流程节点，支持动态注册和实例化
"""

import inspect
from typing import Dict, Type, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass

from .base_component import BaseComponent
from .flow_node import FlowNode, IFlowNode, NodeType


@dataclass
class NodeTemplate:
    """节点模板定义"""
    node_class: Type[FlowNode]
    default_params: Dict[str, Any]
    description: str
    category: str
    required_params: List[str]
    optional_params: List[str]


class NodeFactory(BaseComponent):
    """节点工厂 - 负责创建和管理流程节点"""
    
    def __init__(self, factory_id: str = "default_node_factory"):
        super().__init__(factory_id, "node_factory")
        
        # 注册的节点类型
        self.registered_nodes: Dict[str, NodeTemplate] = {}
        
        # 内置节点类型
        self._register_builtin_nodes()
        
        self.log_debug("NodeFactory initialized", {
            'builtin_nodes': len(self.registered_nodes)
        })
    
    def _register_builtin_nodes(self):
        """注册内置节点类型"""
        # 这里注册一些基础的节点类型
        # 具体的Agent、Context、Tool节点将在各自的模块中注册
        
        from .flow_node import ConditionalNode, ParallelNode, SequenceNode
        
        # 条件节点
        self.register_node_type(
            "conditional",
            ConditionalNode,
            {
                'condition_func': None,
                'true_path': None,
                'false_path': None
            },
            "条件判断节点，根据条件决定执行路径",
            "control",
            required_params=['node_id', 'condition_func'],
            optional_params=['true_path', 'false_path']
        )
        
        # 并行节点
        self.register_node_type(
            "parallel",
            ParallelNode,
            {
                'child_nodes': [],
                'wait_for_all': True
            },
            "并行执行节点，同时执行多个子节点",
            "control",
            required_params=['node_id', 'child_nodes'],
            optional_params=['wait_for_all']
        )
        
        # 序列节点
        self.register_node_type(
            "sequence",
            SequenceNode,
            {
                'child_nodes': [],
                'stop_on_error': True
            },
            "序列执行节点，按顺序执行多个子节点",
            "control",
            required_params=['node_id', 'child_nodes'],
            optional_params=['stop_on_error']
        )
    
    def register_node_type(self, 
                          node_type: str,
                          node_class: Type[FlowNode],
                          default_params: Dict[str, Any],
                          description: str,
                          category: str = "custom",
                          required_params: List[str] = None,
                          optional_params: List[str] = None) -> None:
        """注册新的节点类型"""
        
        # 验证节点类
        if not issubclass(node_class, FlowNode):
            raise ValueError(f"Node class {node_class} must inherit from FlowNode")
        
        # 分析构造函数参数
        if required_params is None or optional_params is None:
            sig = inspect.signature(node_class.__init__)
            all_params = list(sig.parameters.keys())[1:]  # 排除 self
            
            if required_params is None:
                # 没有默认值的参数为必需参数
                required_params = [
                    name for name, param in sig.parameters.items()
                    if name != 'self' and param.default is inspect.Parameter.empty
                ]
            
            if optional_params is None:
                # 有默认值的参数为可选参数
                optional_params = [
                    name for name, param in sig.parameters.items()
                    if name != 'self' and param.default is not inspect.Parameter.empty
                ]
        
        template = NodeTemplate(
            node_class=node_class,
            default_params=default_params,
            description=description,
            category=category,
            required_params=required_params,
            optional_params=optional_params
        )
        
        self.registered_nodes[node_type] = template
        
        self.log_debug(f"Registered node type: {node_type}", {
            'class': node_class.__name__,
            'category': category,
            'required_params': required_params,
            'optional_params': optional_params
        })
    
    def create_node(self, 
                   node_type: str, 
                   node_id: str,
                   **kwargs) -> FlowNode:
        """创建指定类型的节点实例"""
        
        if node_type not in self.registered_nodes:
            raise ValueError(f"Unknown node type: {node_type}")
        
        template = self.registered_nodes[node_type]
        
        # 合并参数
        params = template.default_params.copy()
        params.update(kwargs)
        params['node_id'] = node_id
        
        # 验证必需参数
        missing_params = []
        for required_param in template.required_params:
            if required_param not in params or params[required_param] is None:
                missing_params.append(required_param)
        
        if missing_params:
            raise ValueError(f"Missing required parameters for {node_type}: {missing_params}")
        
        try:
            # 创建节点实例
            node = template.node_class(**params)
            
            self.log_debug(f"Created node {node_id} of type {node_type}", {
                'class': template.node_class.__name__,
                'params': {k: str(v)[:100] for k, v in params.items()}
            })
            
            return node
            
        except Exception as e:
            self.log_error(f"Failed to create node {node_id} of type {node_type}", e, {
                'params': params
            })
            raise
    
    def create_agent_node(self, 
                         node_id: str,
                         agent_instance: Any,
                         **kwargs) -> FlowNode:
        """创建Agent节点的便捷方法"""
        # 这个方法将在AgentNode实现后完善
        return self.create_node("agent", node_id, agent_instance=agent_instance, **kwargs)
    
    def create_context_node(self,
                           node_id: str,
                           context_operation: str,
                           **kwargs) -> FlowNode:
        """创建上下文处理节点的便捷方法"""
        node_type_map = {
            'compress': 'context_compression',
            'extract': 'context_extraction',
            'organize': 'context_organization',
            'retrieve': 'memory_retrieval'
        }
        
        node_type = node_type_map.get(context_operation, f"context_{context_operation}")
        return self.create_node(node_type, node_id, **kwargs)
    
    def create_tool_node(self,
                        node_id: str,
                        tool_instance: Any,
                        **kwargs) -> FlowNode:
        """创建工具调用节点的便捷方法"""
        return self.create_node("tool", node_id, tool_instance=tool_instance, **kwargs)
    
    def create_conditional_node(self,
                               node_id: str,
                               condition_func: Callable[[Dict[str, Any]], bool],
                               true_path: str = None,
                               false_path: str = None,
                               **kwargs) -> FlowNode:
        """创建条件节点的便捷方法"""
        return self.create_node(
            "conditional", 
            node_id,
            condition_func=condition_func,
            true_path=true_path,
            false_path=false_path,
            **kwargs
        )
    
    def create_parallel_node(self,
                           node_id: str,
                           child_nodes: List[IFlowNode],
                           wait_for_all: bool = True,
                           **kwargs) -> FlowNode:
        """创建并行节点的便捷方法"""
        return self.create_node(
            "parallel",
            node_id,
            child_nodes=child_nodes,
            wait_for_all=wait_for_all,
            **kwargs
        )
    
    def create_sequence_node(self,
                           node_id: str,
                           child_nodes: List[IFlowNode],
                           stop_on_error: bool = True,
                           **kwargs) -> FlowNode:
        """创建序列节点的便捷方法"""
        return self.create_node(
            "sequence",
            node_id,
            child_nodes=child_nodes,
            stop_on_error=stop_on_error,
            **kwargs
        )
    
    def get_available_node_types(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用的节点类型信息"""
        result = {}
        
        for node_type, template in self.registered_nodes.items():
            result[node_type] = {
                'class': template.node_class.__name__,
                'description': template.description,
                'category': template.category,
                'required_params': template.required_params,
                'optional_params': template.optional_params,
                'default_params': template.default_params
            }
        
        return result
    
    def get_node_types_by_category(self, category: str) -> List[str]:
        """根据类别获取节点类型"""
        return [
            node_type for node_type, template in self.registered_nodes.items()
            if template.category == category
        ]
    
    def validate_node_config(self, node_type: str, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证节点配置"""
        if node_type not in self.registered_nodes:
            return False, [f"Unknown node type: {node_type}"]
        
        template = self.registered_nodes[node_type]
        errors = []
        
        # 检查必需参数
        for param in template.required_params:
            if param not in config:
                errors.append(f"Missing required parameter: {param}")
        
        # 检查参数类型（如果可以推断的话）
        try:
            sig = inspect.signature(template.node_class.__init__)
            for param_name, param_value in config.items():
                if param_name in sig.parameters:
                    param_info = sig.parameters[param_name]
                    if param_info.annotation != inspect.Parameter.empty:
                        # 这里可以添加更详细的类型检查
                        pass
        except Exception as e:
            self.log_warning(f"Could not validate parameter types for {node_type}", {'error': str(e)})
        
        return len(errors) == 0, errors
    
    def create_node_from_config(self, config: Dict[str, Any]) -> FlowNode:
        """从配置字典创建节点"""
        if 'node_type' not in config:
            raise ValueError("Node config must include 'node_type'")
        
        if 'node_id' not in config:
            raise ValueError("Node config must include 'node_id'")
        
        node_type = config.pop('node_type')
        node_id = config.pop('node_id')
        
        # 验证配置
        is_valid, errors = self.validate_node_config(node_type, config)
        if not is_valid:
            raise ValueError(f"Invalid node config: {'; '.join(errors)}")
        
        return self.create_node(node_type, node_id, **config)
    
    def export_node_templates(self) -> Dict[str, Any]:
        """导出所有节点模板（用于序列化）"""
        result = {}
        
        for node_type, template in self.registered_nodes.items():
            result[node_type] = {
                'class_name': template.node_class.__name__,
                'module': template.node_class.__module__,
                'description': template.description,
                'category': template.category,
                'required_params': template.required_params,
                'optional_params': template.optional_params,
                'default_params': template.default_params
            }
        
        return result
    
    def get_node_documentation(self, node_type: str) -> str:
        """获取节点类型的文档"""
        if node_type not in self.registered_nodes:
            return f"Unknown node type: {node_type}"
        
        template = self.registered_nodes[node_type]
        
        doc_lines = [
            f"Node Type: {node_type}",
            f"Class: {template.node_class.__name__}",
            f"Category: {template.category}",
            f"Description: {template.description}",
            "",
            "Required Parameters:",
        ]
        
        for param in template.required_params:
            doc_lines.append(f"  - {param}")
        
        doc_lines.append("")
        doc_lines.append("Optional Parameters:")
        
        for param in template.optional_params:
            default_value = template.default_params.get(param, "None")
            doc_lines.append(f"  - {param} (default: {default_value})")
        
        # 添加类的docstring
        if template.node_class.__doc__:
            doc_lines.append("")
            doc_lines.append("Class Documentation:")
            doc_lines.append(template.node_class.__doc__)
        
        return "\n".join(doc_lines)
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        # NodeFactory通常不直接执行，而是用于创建节点
        if isinstance(input_data, dict) and 'action' in input_data:
            action = input_data['action']
            
            if action == 'create_node':
                return self.create_node_from_config(input_data.get('config', {}))
            elif action == 'list_types':
                return self.get_available_node_types()
            elif action == 'get_documentation':
                return self.get_node_documentation(input_data.get('node_type', ''))
            else:
                raise ValueError(f"Unknown action: {action}")
        else:
            raise ValueError("NodeFactory requires dict input with 'action' field")


# 全局节点工厂实例
_default_factory: Optional[NodeFactory] = None

def get_node_factory() -> NodeFactory:
    """获取默认的节点工厂实例"""
    global _default_factory
    if _default_factory is None:
        _default_factory = NodeFactory()
    return _default_factory

def register_node_type(node_type: str, 
                      node_class: Type[FlowNode],
                      default_params: Dict[str, Any],
                      description: str,
                      category: str = "custom",
                      required_params: List[str] = None,
                      optional_params: List[str] = None) -> None:
    """在默认工厂中注册节点类型的便捷函数"""
    factory = get_node_factory()
    factory.register_node_type(
        node_type, node_class, default_params, description, 
        category, required_params, optional_params
    )
