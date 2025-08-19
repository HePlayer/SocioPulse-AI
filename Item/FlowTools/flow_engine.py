"""
FlowEngine - 流程执行引擎
基于有向图管理和执行复杂的工作流程，支持条件分支、并行执行和依赖管理
"""

import asyncio
import time
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from .base_component import BaseComponent
from .flow_node import IFlowNode, NodeResult, NodeStatus, NodeType


class FlowStatus(Enum):
    """流程状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class FlowEdge:
    """流程边定义"""
    from_node: str
    to_node: str
    condition: Optional[callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowExecution:
    """流程执行记录"""
    flow_id: str
    start_time: float
    end_time: Optional[float] = None
    status: FlowStatus = FlowStatus.RUNNING
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    execution_path: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class FlowEngine(BaseComponent):
    """流程执行引擎"""
    
    def __init__(self, engine_id: str = "default_flow_engine"):
        super().__init__(engine_id, "flow_engine")
        
        # 流程图结构
        self.nodes: Dict[str, IFlowNode] = {}
        self.edges: List[FlowEdge] = []
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        
        # 执行状态
        self.current_execution: Optional[FlowExecution] = None
        self.execution_history: List[FlowExecution] = []
        self.paused_nodes: Set[str] = set()
        
        # 执行控制
        self.max_concurrent_nodes = 10
        self.global_timeout = 300.0  # 5分钟
        self.enable_parallel_execution = True
        
        self.log_debug("FlowEngine initialized")
    
    def add_node(self, node: IFlowNode) -> None:
        """添加节点到流程图"""
        if hasattr(node, 'component_id'):
            node_id = node.component_id
        else:
            raise ValueError("Node must have component_id attribute")
        
        if node_id in self.nodes:
            self.log_warning(f"Node {node_id} already exists, replacing")
        
        self.nodes[node_id] = node
        
        # 初始化邻接表
        if node_id not in self.adjacency_list:
            self.adjacency_list[node_id] = []
        if node_id not in self.reverse_adjacency:
            self.reverse_adjacency[node_id] = []
        
        self.log_debug(f"Added node {node_id}", {
            'node_type': getattr(node, 'node_type', 'unknown'),
            'total_nodes': len(self.nodes)
        })
    
    def add_edge(self, from_node: str, to_node: str, condition: Optional[callable] = None, metadata: Dict[str, Any] = None) -> None:
        """添加边到流程图"""
        if from_node not in self.nodes:
            raise ValueError(f"Source node {from_node} not found")
        if to_node not in self.nodes:
            raise ValueError(f"Target node {to_node} not found")
        
        edge = FlowEdge(
            from_node=from_node,
            to_node=to_node,
            condition=condition,
            metadata=metadata or {}
        )
        
        self.edges.append(edge)
        self.adjacency_list[from_node].append(to_node)
        self.reverse_adjacency[to_node].append(from_node)
        
        self.log_debug(f"Added edge {from_node} -> {to_node}", {
            'has_condition': condition is not None,
            'total_edges': len(self.edges)
        })
    
    def remove_node(self, node_id: str) -> None:
        """从流程图中移除节点"""
        if node_id not in self.nodes:
            self.log_warning(f"Node {node_id} not found for removal")
            return
        
        # 移除相关的边
        self.edges = [e for e in self.edges if e.from_node != node_id and e.to_node != node_id]
        
        # 更新邻接表
        del self.adjacency_list[node_id]
        del self.reverse_adjacency[node_id]
        
        for adj_list in self.adjacency_list.values():
            if node_id in adj_list:
                adj_list.remove(node_id)
        
        for rev_adj_list in self.reverse_adjacency.values():
            if node_id in rev_adj_list:
                rev_adj_list.remove(node_id)
        
        # 移除节点
        del self.nodes[node_id]
        
        self.log_debug(f"Removed node {node_id}")
    
    def validate_flow(self) -> Tuple[bool, List[str]]:
        """验证流程图的有效性"""
        errors = []
        
        # 检查循环依赖
        if self._has_cycle():
            errors.append("Flow contains cycles")
        
        # 检查孤立节点
        isolated_nodes = self._find_isolated_nodes()
        if isolated_nodes:
            errors.append(f"Isolated nodes found: {isolated_nodes}")
        
        # 检查节点依赖是否满足
        for node_id, node in self.nodes.items():
            dependencies = node.get_dependencies()
            for dep in dependencies:
                if dep not in self.nodes:
                    errors.append(f"Node {node_id} depends on non-existent node {dep}")
        
        # 检查边的条件函数
        for edge in self.edges:
            if edge.condition and not callable(edge.condition):
                errors.append(f"Edge {edge.from_node} -> {edge.to_node} has invalid condition")
        
        is_valid = len(errors) == 0
        
        self.log_debug(f"Flow validation result: {'VALID' if is_valid else 'INVALID'}", {
            'errors': errors
        })
        
        return is_valid, errors
    
    def _has_cycle(self) -> bool:
        """检测流程图是否存在环"""
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.adjacency_list[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
    
    def _find_isolated_nodes(self) -> List[str]:
        """查找孤立节点（没有入边也没有出边）"""
        isolated = []
        for node_id in self.nodes:
            has_incoming = len(self.reverse_adjacency[node_id]) > 0
            has_outgoing = len(self.adjacency_list[node_id]) > 0
            
            if not has_incoming and not has_outgoing:
                isolated.append(node_id)
        
        return isolated
    
    def get_entry_nodes(self) -> List[str]:
        """获取入口节点（没有入边的节点）"""
        entry_nodes = []
        for node_id in self.nodes:
            if len(self.reverse_adjacency[node_id]) == 0:
                entry_nodes.append(node_id)
        return entry_nodes
    
    def get_exit_nodes(self) -> List[str]:
        """获取出口节点（没有出边的节点）"""
        exit_nodes = []
        for node_id in self.nodes:
            if len(self.adjacency_list[node_id]) == 0:
                exit_nodes.append(node_id)
        return exit_nodes
    
    def topological_sort(self) -> List[str]:
        """拓扑排序，返回执行顺序"""
        in_degree = {node_id: len(self.reverse_adjacency[node_id]) for node_id in self.nodes}
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            for neighbor in self.adjacency_list[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(self.nodes):
            raise ValueError("Flow contains cycles - cannot perform topological sort")
        
        return result
    
    async def execute_flow(self, 
                          initial_data: Dict[str, Any], 
                          flow_id: str = None,
                          entry_nodes: List[str] = None) -> FlowExecution:
        """执行流程"""
        if flow_id is None:
            flow_id = f"flow_{int(time.time() * 1000)}"
        
        # 验证流程
        is_valid, errors = self.validate_flow()
        if not is_valid:
            raise ValueError(f"Invalid flow: {'; '.join(errors)}")
        
        # 创建执行记录
        execution = FlowExecution(
            flow_id=flow_id,
            start_time=time.time(),
            status=FlowStatus.RUNNING
        )
        self.current_execution = execution
        
        self.log_info(f"Starting flow execution {flow_id}", {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'entry_nodes': entry_nodes
        })
        
        try:
            # 确定起始节点
            if entry_nodes is None:
                entry_nodes = self.get_entry_nodes()
            
            if not entry_nodes:
                raise ValueError("No entry nodes found or specified")
            
            # 执行流程
            await self._execute_nodes(entry_nodes, initial_data, execution)
            
            # 更新执行状态
            execution.end_time = time.time()
            execution.status = FlowStatus.COMPLETED
            
            self.log_info(f"Flow execution {flow_id} completed", {
                'execution_time': execution.end_time - execution.start_time,
                'nodes_executed': len(execution.node_results),
                'execution_path': execution.execution_path
            })
            
        except Exception as e:
            execution.end_time = time.time()
            execution.status = FlowStatus.FAILED
            execution.error_message = str(e)
            
            self.log_error(f"Flow execution {flow_id} failed", e, {
                'execution_time': execution.end_time - execution.start_time,
                'nodes_executed': len(execution.node_results),
                'execution_path': execution.execution_path
            })
            
            raise
        
        finally:
            self.execution_history.append(execution)
            self.current_execution = None
        
        return execution
    
    async def _execute_nodes(self, 
                           node_ids: List[str], 
                           data: Dict[str, Any], 
                           execution: FlowExecution) -> None:
        """递归执行节点"""
        if not node_ids:
            return
        
        # 过滤已执行和暂停的节点
        pending_nodes = [nid for nid in node_ids if nid not in execution.node_results and nid not in self.paused_nodes]
        
        if not pending_nodes:
            return
        
        # 并行执行节点（如果启用）
        if self.enable_parallel_execution and len(pending_nodes) > 1:
            # 检查哪些节点可以并行执行
            parallel_nodes = [nid for nid in pending_nodes if self.nodes[nid].parallel_safe]
            sequential_nodes = [nid for nid in pending_nodes if not self.nodes[nid].parallel_safe]
            
            # 并行执行
            if parallel_nodes:
                await self._execute_parallel_nodes(parallel_nodes, data, execution)
            
            # 串行执行
            for node_id in sequential_nodes:
                await self._execute_single_node(node_id, data, execution)
        
        else:
            # 串行执行所有节点
            for node_id in pending_nodes:
                await self._execute_single_node(node_id, data, execution)
        
        # 确定下一批要执行的节点
        next_nodes = []
        for node_id in pending_nodes:
            if node_id in execution.node_results and execution.node_results[node_id].success:
                next_nodes.extend(self._get_next_nodes(node_id, execution.node_results[node_id].data))
        
        # 递归执行下一批节点
        if next_nodes:
            # 合并数据
            merged_data = data.copy()
            for node_id in pending_nodes:
                if node_id in execution.node_results:
                    result = execution.node_results[node_id]
                    if result.success and isinstance(result.data, dict):
                        merged_data.update(result.data)
            
            await self._execute_nodes(next_nodes, merged_data, execution)
    
    async def _execute_parallel_nodes(self, 
                                    node_ids: List[str], 
                                    data: Dict[str, Any], 
                                    execution: FlowExecution) -> None:
        """并行执行节点"""
        tasks = []
        for node_id in node_ids:
            task = asyncio.create_task(self._execute_single_node(node_id, data, execution))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_single_node(self, 
                                 node_id: str, 
                                 data: Dict[str, Any], 
                                 execution: FlowExecution) -> None:
        """执行单个节点"""
        if node_id in execution.node_results:
            return  # 节点已执行
        
        node = self.nodes[node_id]
        execution.execution_path.append(node_id)
        
        self.log_debug(f"Executing node {node_id}")
        
        try:
            # 执行节点
            result = await node.execute(data)
            execution.node_results[node_id] = result
            
            if result.success:
                self.log_debug(f"Node {node_id} executed successfully", {
                    'execution_time': result.execution_time
                })
            else:
                self.log_error(f"Node {node_id} execution failed: {result.error}")
                
        except Exception as e:
            self.log_error(f"Node {node_id} execution exception", e)
            execution.node_results[node_id] = NodeResult(
                success=False,
                data=None,
                error=str(e),
                node_id=node_id,
                status=NodeStatus.FAILED
            )
    
    def _get_next_nodes(self, from_node: str, result_data: Any) -> List[str]:
        """根据执行结果确定下一个要执行的节点"""
        next_nodes = []
        
        for edge in self.edges:
            if edge.from_node == from_node:
                # 检查边的条件
                if edge.condition is None or edge.condition(result_data):
                    next_nodes.append(edge.to_node)
        
        return next_nodes
    
    def pause_node(self, node_id: str) -> None:
        """暂停节点执行"""
        self.paused_nodes.add(node_id)
        self.log_info(f"Node {node_id} paused")
    
    def resume_node(self, node_id: str) -> None:
        """恢复节点执行"""
        self.paused_nodes.discard(node_id)
        self.log_info(f"Node {node_id} resumed")
    
    def get_flow_status(self) -> Dict[str, Any]:
        """获取流程状态信息"""
        return {
            'engine_id': self.component_id,
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'current_execution': self.current_execution.__dict__ if self.current_execution else None,
            'paused_nodes': list(self.paused_nodes),
            'execution_history_count': len(self.execution_history),
            'configuration': {
                'max_concurrent_nodes': self.max_concurrent_nodes,
                'global_timeout': self.global_timeout,
                'enable_parallel_execution': self.enable_parallel_execution
            }
        }
    
    def visualize_flow(self) -> str:
        """生成流程图的文本可视化"""
        lines = ["Flow Visualization:"]
        lines.append("=" * 50)
        
        # 节点信息
        lines.append("Nodes:")
        for node_id, node in self.nodes.items():
            node_type = getattr(node, 'node_type', 'unknown')
            status = getattr(node, 'status', 'unknown')
            lines.append(f"  {node_id} ({node_type}) - {status}")
        
        lines.append("")
        
        # 边信息
        lines.append("Edges:")
        for edge in self.edges:
            condition_info = " [conditional]" if edge.condition else ""
            lines.append(f"  {edge.from_node} -> {edge.to_node}{condition_info}")
        
        return "\n".join(lines)
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if not isinstance(input_data, dict):
            raise ValueError("FlowEngine requires dict input data")
        
        # 同步包装异步执行
        return asyncio.run(self.execute_flow(input_data))
