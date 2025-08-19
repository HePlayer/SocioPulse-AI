"""
HNSW Node - HNSW算法中的节点定义
包含节点的向量数据、层级信息和连接关系
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Any, Optional
from collections import defaultdict


@dataclass
class HNSWNode:
    """HNSW图中的节点"""
    
    node_id: str
    vector: List[float]
    level: int
    data: Optional[Any] = None
    connections: Dict[int, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    def __post_init__(self):
        """初始化后处理"""
        if not isinstance(self.connections, defaultdict):
            # 确保connections是defaultdict类型
            connections_dict = defaultdict(set)
            if self.connections:
                for level, conn_set in self.connections.items():
                    connections_dict[level] = set(conn_set) if not isinstance(conn_set, set) else conn_set
            self.connections = connections_dict
    
    def add_connection(self, neighbor_id: str, level: int) -> None:
        """在指定层级添加连接"""
        self.connections[level].add(neighbor_id)
    
    def remove_connection(self, neighbor_id: str, level: int) -> None:
        """在指定层级移除连接"""
        if level in self.connections:
            self.connections[level].discard(neighbor_id)
    
    def get_connections(self, level: int) -> Set[str]:
        """获取指定层级的连接"""
        return self.connections.get(level, set())
    
    def get_connection_count(self, level: int) -> int:
        """获取指定层级的连接数量"""
        return len(self.connections.get(level, set()))
    
    def get_all_levels(self) -> List[int]:
        """获取所有存在连接的层级"""
        return list(self.connections.keys())
    
    def has_connection(self, neighbor_id: str, level: int) -> bool:
        """检查是否存在指定连接"""
        return neighbor_id in self.connections.get(level, set())
    
    def get_total_connections(self) -> int:
        """获取所有层级的总连接数"""
        return sum(len(connections) for connections in self.connections.values())
    
    def clear_level(self, level: int) -> None:
        """清空指定层级的所有连接"""
        if level in self.connections:
            self.connections[level].clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于序列化）"""
        return {
            'node_id': self.node_id,
            'vector': self.vector,
            'level': self.level,
            'data': self.data,
            'connections': {
                str(level): list(connections) 
                for level, connections in self.connections.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HNSWNode':
        """从字典创建节点实例"""
        connections = defaultdict(set)
        if 'connections' in data:
            for level_str, conn_list in data['connections'].items():
                level = int(level_str)
                connections[level] = set(conn_list)
        
        return cls(
            node_id=data['node_id'],
            vector=data['vector'],
            level=data['level'],
            data=data.get('data'),
            connections=connections
        )
    
    def __str__(self) -> str:
        return f"HNSWNode(id={self.node_id}, level={self.level}, connections={self.get_total_connections()})"
    
    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class SearchCandidate:
    """搜索候选项"""
    
    node_id: str
    distance: float
    
    def __lt__(self, other: 'SearchCandidate') -> bool:
        """用于堆排序的比较函数"""
        return self.distance < other.distance
    
    def __eq__(self, other: 'SearchCandidate') -> bool:
        return self.node_id == other.node_id
    
    def __hash__(self) -> int:
        return hash(self.node_id)


@dataclass
class HNSWStats:
    """HNSW索引统计信息"""
    
    total_nodes: int = 0
    max_level: int = 0
    level_distribution: Dict[int, int] = field(default_factory=dict)
    total_connections: int = 0
    avg_connections_per_level: Dict[int, float] = field(default_factory=dict)
    entry_point_id: Optional[str] = None
    
    def update_from_index(self, nodes: Dict[str, HNSWNode], entry_point: Optional[str]) -> None:
        """从索引更新统计信息"""
        self.total_nodes = len(nodes)
        self.entry_point_id = entry_point
        self.level_distribution.clear()
        self.avg_connections_per_level.clear()
        
        if not nodes:
            self.max_level = 0
            self.total_connections = 0
            return
        
        # 统计层级分布
        level_connections = defaultdict(list)
        total_connections = 0
        
        for node in nodes.values():
            # 更新最大层级
            self.max_level = max(self.max_level, node.level)
            
            # 统计层级分布
            self.level_distribution[node.level] = self.level_distribution.get(node.level, 0) + 1
            
            # 统计每层连接数
            for level in range(node.level + 1):
                conn_count = node.get_connection_count(level)
                level_connections[level].append(conn_count)
                total_connections += conn_count
        
        self.total_connections = total_connections // 2  # 双向连接，除以2
        
        # 计算每层平均连接数
        for level, conn_counts in level_connections.items():
            if conn_counts:
                self.avg_connections_per_level[level] = sum(conn_counts) / len(conn_counts)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'total_nodes': self.total_nodes,
            'max_level': self.max_level,
            'level_distribution': self.level_distribution,
            'total_connections': self.total_connections,
            'avg_connections_per_level': self.avg_connections_per_level,
            'entry_point_id': self.entry_point_id
        }
