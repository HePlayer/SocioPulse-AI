"""
FlowNode - 流程控制节点的接口和基础实现
提供标准化的节点执行接口，支持各种类型的操作节点
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

from .base_component import BaseComponent


class NodeType(Enum):
    """节点类型枚举"""
    AGENT = "agent"
    CONTEXT = "context"
    TOOL = "tool"
    COMMUNICATION = "communication"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"
    CUSTOM = "custom"


class NodeStatus(Enum):
    """节点状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


@dataclass
class NodeResult:
    """节点执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    node_id: str = ""
    status: NodeStatus = NodeStatus.COMPLETED
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IFlowNode(ABC):
    """流程节点统一接口"""
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """执行节点逻辑（异步）"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出数据模式"""
        pass
    
    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """获取节点依赖列表"""
        pass


class FlowNode(BaseComponent, IFlowNode):
    """流程节点基础实现"""
    
    def __init__(self, 
                 node_id: str, 
                 node_type: NodeType = NodeType.CUSTOM,
                 dependencies: List[str] = None,
                 timeout: float = 30.0,
                 retry_count: int = 0,
                 parallel_safe: bool = True):
        super().__init__(node_id, node_type.value)
        
        self.node_type = node_type
        self.dependencies = dependencies or []
        self.timeout = timeout
        self.retry_count = retry_count
        self.parallel_safe = parallel_safe
        self.status = NodeStatus.IDLE
        
        # 节点特定的统计信息
        self.execution_history: List[NodeResult] = []
        self.input_schema: Dict[str, Any] = {}
        self.output_schema: Dict[str, Any] = {}
        
        self.log_debug(f"FlowNode {node_id} initialized", {
            'node_type': node_type.value,
            'dependencies': dependencies,
            'timeout': timeout,
            'retry_count': retry_count
        })
    
    async def execute(self, input_data: Dict[str, Any]) -> NodeResult:
        """执行节点（带超时和重试机制）"""
        self.status = NodeStatus.RUNNING
        start_time = time.time()
        
        for attempt in range(self.retry_count + 1):
            try:
                self.log_debug(f"Node execution attempt {attempt + 1}", {
                    'input_data_keys': list(input_data.keys()) if input_data else [],
                    'timeout': self.timeout
                })
                
                # 验证输入
                if not self.validate_input(input_data):
                    raise ValueError(f"Invalid input data for node {self.component_id}")
                
                # 执行核心逻辑（带超时）
                if asyncio.iscoroutinefunction(self._execute_core):
                    result = await asyncio.wait_for(
                        self._execute_core(input_data), 
                        timeout=self.timeout
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, self._execute_core, input_data
                        ),
                        timeout=self.timeout
                    )
                
                # 创建成功结果
                execution_time = time.time() - start_time
                node_result = NodeResult(
                    success=True,
                    data=result,
                    execution_time=execution_time,
                    node_id=self.component_id,
                    status=NodeStatus.COMPLETED
                )
                
                self.status = NodeStatus.COMPLETED
                self.execution_history.append(node_result)
                
                self.log_debug("Node execution completed successfully", {
                    'execution_time': execution_time,
                    'attempt': attempt + 1,
                    'result_type': type(result).__name__
                })
                
                return node_result
                
            except asyncio.TimeoutError as e:
                self.log_error(f"Node execution timeout on attempt {attempt + 1}", e)
                if attempt == self.retry_count:  # 最后一次尝试
                    self.status = NodeStatus.FAILED
                    execution_time = time.time() - start_time
                    error_result = NodeResult(
                        success=False,
                        data=None,
                        error=f"Execution timeout after {self.timeout}s",
                        execution_time=execution_time,
                        node_id=self.component_id,
                        status=NodeStatus.FAILED
                    )
                    self.execution_history.append(error_result)
                    return error_result
                    
            except Exception as e:
                self.log_error(f"Node execution error on attempt {attempt + 1}", e)
                if attempt == self.retry_count:  # 最后一次尝试
                    self.status = NodeStatus.FAILED
                    execution_time = time.time() - start_time
                    error_result = NodeResult(
                        success=False,
                        data=None,
                        error=str(e),
                        execution_time=execution_time,
                        node_id=self.component_id,
                        status=NodeStatus.FAILED
                    )
                    self.execution_history.append(error_result)
                    return error_result
                    
                # 重试前等待
                if attempt < self.retry_count:
                    await asyncio.sleep(min(2 ** attempt, 10))  # 指数退避，最大10秒
    
    @abstractmethod
    def _execute_core(self, input_data: Dict[str, Any]) -> Any:
        """子类实现的核心执行逻辑"""
        raise NotImplementedError("Subclasses must implement _execute_core method")
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """默认输入验证（子类可重写）"""
        if not isinstance(input_data, dict):
            return False
        
        # 检查必需的输入字段
        if hasattr(self, 'required_inputs'):
            for field in self.required_inputs:
                if field not in input_data:
                    self.log_error(f"Missing required input field: {field}")
                    return False
        
        return True
    
    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出模式"""
        return self.output_schema
    
    def get_dependencies(self) -> List[str]:
        """获取依赖节点"""
        return self.dependencies
    
    def get_node_info(self) -> Dict[str, Any]:
        """获取节点详细信息"""
        avg_execution_time = 0.0
        success_rate = 1.0
        
        if self.execution_history:
            successful_executions = [r for r in self.execution_history if r.success]
            success_rate = len(successful_executions) / len(self.execution_history)
            
            if successful_executions:
                avg_execution_time = sum(r.execution_time for r in successful_executions) / len(successful_executions)
        
        return {
            'node_id': self.component_id,
            'node_type': self.node_type.value,
            'status': self.status.value,
            'dependencies': self.dependencies,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'parallel_safe': self.parallel_safe,
            'statistics': {
                'total_executions': len(self.execution_history),
                'success_rate': success_rate,
                'avg_execution_time': avg_execution_time,
                'last_execution': self.execution_history[-1].__dict__ if self.execution_history else None
            },
            'input_schema': self.input_schema,
            'output_schema': self.output_schema
        }
    
    def reset_node(self):
        """重置节点状态"""
        self.status = NodeStatus.IDLE
        self.execution_history.clear()
        self.reset_stats()
        self.log_debug("Node reset completed")


class ConditionalNode(FlowNode):
    """条件节点 - 基于条件决定执行路径"""
    
    def __init__(self, 
                 node_id: str, 
                 condition_func: Callable[[Dict[str, Any]], bool],
                 true_path: str = None,
                 false_path: str = None):
        super().__init__(node_id, NodeType.CONDITION)
        self.condition_func = condition_func
        self.true_path = true_path
        self.false_path = false_path
        
        self.output_schema = {
            'condition_result': 'boolean',
            'next_node': 'string',
            'original_data': 'any'
        }
    
    def _execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行条件判断"""
        try:
            condition_result = self.condition_func(input_data)
            next_node = self.true_path if condition_result else self.false_path
            
            return {
                'condition_result': condition_result,
                'next_node': next_node,
                'original_data': input_data
            }
        except Exception as e:
            self.log_error("Condition evaluation failed", e)
            raise


class ParallelNode(FlowNode):
    """并行节点 - 并行执行多个子节点"""
    
    def __init__(self, 
                 node_id: str, 
                 child_nodes: List[IFlowNode],
                 wait_for_all: bool = True):
        super().__init__(node_id, NodeType.PARALLEL)
        self.child_nodes = child_nodes
        self.wait_for_all = wait_for_all
        
        self.output_schema = {
            'results': 'list',
            'completed_count': 'integer',
            'failed_count': 'integer'
        }
    
    async def _execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """并行执行子节点"""
        tasks = []
        for child in self.child_nodes:
            if child.parallel_safe:
                task = asyncio.create_task(child.execute(input_data))
                tasks.append((child.component_id, task))
            else:
                self.log_warning(f"Child node {child.component_id} is not parallel-safe, skipping")
        
        if self.wait_for_all:
            # 等待所有任务完成
            results = {}
            for node_id, task in tasks:
                try:
                    result = await task
                    results[node_id] = result
                except Exception as e:
                    self.log_error(f"Parallel child node {node_id} failed", e)
                    results[node_id] = NodeResult(
                        success=False,
                        data=None,
                        error=str(e),
                        node_id=node_id,
                        status=NodeStatus.FAILED
                    )
        else:
            # 等待第一个完成的任务
            done, pending = await asyncio.wait(
                [task for _, task in tasks], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消剩余任务
            for task in pending:
                task.cancel()
            
            results = {}
            for task in done:
                try:
                    result = await task
                    # 找到对应的节点ID
                    for node_id, t in tasks:
                        if t == task:
                            results[node_id] = result
                            break
                except Exception as e:
                    self.log_error("Parallel execution error", e)
        
        completed_count = sum(1 for r in results.values() if isinstance(r, NodeResult) and r.success)
        failed_count = len(results) - completed_count
        
        return {
            'results': results,
            'completed_count': completed_count,
            'failed_count': failed_count
        }


class SequenceNode(FlowNode):
    """序列节点 - 按顺序执行多个子节点"""
    
    def __init__(self, 
                 node_id: str, 
                 child_nodes: List[IFlowNode],
                 stop_on_error: bool = True):
        super().__init__(node_id, NodeType.SEQUENCE)
        self.child_nodes = child_nodes
        self.stop_on_error = stop_on_error
        
        self.output_schema = {
            'results': 'list',
            'last_successful_index': 'integer',
            'accumulated_data': 'any'
        }
    
    async def _execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """按序执行子节点"""
        results = []
        accumulated_data = input_data
        last_successful_index = -1
        
        for i, child in enumerate(self.child_nodes):
            try:
                result = await child.execute(accumulated_data)
                results.append(result)
                
                if result.success:
                    last_successful_index = i
                    # 将结果数据传递给下一个节点
                    if isinstance(result.data, dict):
                        accumulated_data.update(result.data)
                    else:
                        accumulated_data['previous_result'] = result.data
                else:
                    if self.stop_on_error:
                        self.log_error(f"Sequence stopped at node {i} due to error: {result.error}")
                        break
                        
            except Exception as e:
                self.log_error(f"Sequence node {i} execution failed", e)
                error_result = NodeResult(
                    success=False,
                    data=None,
                    error=str(e),
                    node_id=child.component_id if hasattr(child, 'component_id') else f"child_{i}",
                    status=NodeStatus.FAILED
                )
                results.append(error_result)
                
                if self.stop_on_error:
                    break
        
        return {
            'results': results,
            'last_successful_index': last_successful_index,
            'accumulated_data': accumulated_data
        }
