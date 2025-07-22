"""
HNSW索引实现
基于Hierarchical Navigable Small World算法的高性能相似性搜索索引
"""

import logging
import math
import random
import threading
from typing import List, Dict, Optional, Set, Tuple, Any
from collections import defaultdict
import numpy as np

from .hnsw_node import HNSWNode, HNSWStats, SearchCandidate
from .distance_metrics import DistanceMetrics, OptimizedDistanceCalculator, DistanceType
from .hnsw_utils import HNSWUtils

logger = logging.getLogger(__name__)


class HNSWIndex:
    """
    Hierarchical Navigable Small World索引
    
    HNSW是一种用于近似最近邻搜索的图数据结构，具有以下特点：
    - 多层结构：较高层用于全局搜索，较低层用于精确搜索
    - 小世界网络：节点连接遵循小世界原理，提高搜索效率
    - 可调参数：支持调整连接度、层数等参数来平衡精度和性能
    """
    
    def __init__(
        self,
        space: DistanceType = DistanceType.COSINE,
        dim: int = 768,
        max_elements: int = 100000,
        m: int = 16,  # 每层最大连接数
        max_m: int = 16,  # 0层最大连接数
        max_m_l: int = 16,  # 其他层最大连接数
        ml: float = 1 / math.log(2.0),  # 层数生成参数
        ef_construction: int = 200,  # 构建时的动态候选列表大小
        ef_search: int = 50,  # 搜索时的动态候选列表大小
        seed: int = 42
    ):
        """
        初始化HNSW索引
        
        Args:
            space: 距离度量类型
            dim: 向量维度
            max_elements: 最大元素数量
            m: 每层的最大连接数
            max_m: 0层的最大连接数
            max_m_l: 其他层的最大连接数
            ml: 层数生成的参数
            ef_construction: 构建时的ef参数
            ef_search: 搜索时的ef参数
            seed: 随机种子
        """
        self.space = space
        self.dim = dim
        self.max_elements = max_elements
        self.m = m
        self.max_m = max_m
        self.max_m_l = max_m_l
        self.ml = ml
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        
        # 设置随机种子
        random.seed(seed)
        np.random.seed(seed)
        
        # 距离计算器
        self.distance_calculator = OptimizedDistanceCalculator(space)
        
        # 索引数据结构
        self.levels: Dict[int, Dict[int, HNSWNode]] = defaultdict(dict)  # level -> {node_id: node}
        self.entry_point: Optional[int] = None  # 入口点ID
        self.current_count = 0  # 当前节点数量
        self.max_level = 0  # 当前最大层数
        
        # 节点数据存储
        self.data: Dict[int, np.ndarray] = {}  # node_id -> vector
        self.metadata: Dict[int, Any] = {}  # node_id -> metadata
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = HNSWStats()
        
        logger.info(f"Initialized HNSW index with dim={dim}, m={m}, ef_construction={ef_construction}")
    
    def _get_random_level(self) -> int:
        """获取随机层数"""
        level = int(-math.log(random.uniform(0, 1)) * self.ml)
        return level
    
    def _search_layer(
        self,
        query: np.ndarray,
        entry_points: List[int],
        num_closest: int,
        level: int
    ) -> List[SearchCandidate]:
        """
        在指定层中搜索最近邻
        
        Args:
            query: 查询向量
            entry_points: 入口点列表
            num_closest: 返回的最近邻数量
            level: 搜索的层级
            
        Returns:
            最近邻候选列表
        """
        visited = set()
        candidates = []
        w = []  # 动态候选列表
        
        # 初始化候选列表
        for ep in entry_points:
            if ep in self.data and ep not in visited:
                dist = self.distance_calculator.calculate(query, self.data[ep])
                candidate = SearchCandidate(ep, dist)
                candidates.append(candidate)
                w.append(candidate)
                visited.add(ep)
        
        # 排序候选列表
        candidates.sort(key=lambda x: x.distance)
        w.sort(key=lambda x: x.distance)
        
        while candidates:
            # 取出距离最近的候选
            current = candidates.pop(0)
            
            # 如果当前候选的距离大于w中最远的距离，停止搜索
            if w and current.distance > w[-1].distance:
                break
            
            # 检查当前节点的邻居
            if current.node_id in self.levels[level]:
                node = self.levels[level][current.node_id]
                for neighbor_id in node.connections:
                    if neighbor_id not in visited and neighbor_id in self.data:
                        visited.add(neighbor_id)
                        dist = self.distance_calculator.calculate(query, self.data[neighbor_id])
                        neighbor_candidate = SearchCandidate(neighbor_id, dist)
                        
                        # 如果w未满或者邻居比w中最远的更近
                        if len(w) < num_closest:
                            candidates.append(neighbor_candidate)
                            w.append(neighbor_candidate)
                            # 保持排序
                            candidates.sort(key=lambda x: x.distance)
                            w.sort(key=lambda x: x.distance)
                        elif neighbor_candidate.distance < w[-1].distance:
                            candidates.append(neighbor_candidate)
                            w.append(neighbor_candidate)
                            # 保持排序并限制大小
                            candidates.sort(key=lambda x: x.distance)
                            w.sort(key=lambda x: x.distance)
                            if len(w) > num_closest:
                                w.pop()
        
        # 返回最近的num_closest个结果
        return w[:num_closest]
    
    def _select_neighbors_heuristic(
        self,
        candidates: List[SearchCandidate],
        max_connections: int,
        extend_candidates: bool = True,
        keep_pruned_connections: bool = True
    ) -> List[int]:
        """
        使用启发式方法选择邻居连接
        
        Args:
            candidates: 候选邻居列表
            max_connections: 最大连接数
            extend_candidates: 是否扩展候选列表
            keep_pruned_connections: 是否保留被剪枝的连接
            
        Returns:
            选择的邻居ID列表
        """
        if len(candidates) <= max_connections:
            return [c.node_id for c in candidates]
        
        # 简单实现：选择距离最近的邻居
        candidates_sorted = sorted(candidates, key=lambda x: x.distance)
        return [c.node_id for c in candidates_sorted[:max_connections]]
    
    def add_point(self, vector: np.ndarray, node_id: Optional[int] = None, metadata: Any = None) -> int:
        """
        向索引中添加点
        
        Args:
            vector: 向量数据
            node_id: 节点ID（如果为None则自动生成）
            metadata: 元数据
            
        Returns:
            节点ID
        """
        with self.lock:
            # 验证向量维度
            if len(vector) != self.dim:
                raise ValueError(f"Vector dimension {len(vector)} does not match index dimension {self.dim}")
            
            # 生成节点ID
            if node_id is None:
                node_id = self.current_count
            
            # 检查容量
            if self.current_count >= self.max_elements:
                raise ValueError(f"Index is full (max_elements={self.max_elements})")
            
            # 标准化向量（对于余弦距离）
            if self.space == DistanceType.COSINE:
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
            
            # 存储数据
            self.data[node_id] = vector.copy()
            if metadata is not None:
                self.metadata[node_id] = metadata
            
            # 确定节点层数
            node_level = self._get_random_level()
            self.max_level = max(self.max_level, node_level)
            
            # 创建各层的节点
            for level in range(node_level + 1):
                self.levels[level][node_id] = HNSWNode(node_id, level)
            
            # 如果是第一个节点，设为入口点
            if self.entry_point is None:
                self.entry_point = node_id
                self.current_count += 1
                logger.debug(f"Added first node {node_id} as entry point at level {node_level}")
                return node_id
            
            # 搜索最近邻并建立连接
            current_max_layer = max(self.levels.keys())
            entry_points = [self.entry_point]
            
            # 从顶层搜索到目标层的上一层
            for level in range(current_max_layer, node_level, -1):
                entry_points = [c.node_id for c in self._search_layer(
                    vector, entry_points, 1, level
                )]
            
            # 在目标层及以下建立连接
            for level in range(min(node_level, current_max_layer), -1, -1):
                candidates = self._search_layer(
                    vector, entry_points, self.ef_construction, level
                )
                
                # 选择邻居
                max_conn = self.max_m if level == 0 else self.max_m_l
                selected_neighbors = self._select_neighbors_heuristic(candidates, max_conn)
                
                # 建立双向连接
                current_node = self.levels[level][node_id]
                for neighbor_id in selected_neighbors:
                    if neighbor_id in self.levels[level]:
                        # 添加连接
                        current_node.add_connection(neighbor_id)
                        neighbor_node = self.levels[level][neighbor_id]
                        neighbor_node.add_connection(node_id)
                        
                        # 如果邻居连接数超过限制，进行剪枝
                        if len(neighbor_node.connections) > max_conn:
                            # 获取邻居的所有邻居候选
                            neighbor_candidates = []
                            for conn_id in neighbor_node.connections:
                                if conn_id in self.data:
                                    dist = self.distance_calculator.calculate(
                                        self.data[neighbor_id], self.data[conn_id]
                                    )
                                    neighbor_candidates.append(SearchCandidate(conn_id, dist))
                            
                            # 重新选择邻居
                            new_connections = self._select_neighbors_heuristic(
                                neighbor_candidates, max_conn
                            )
                            
                            # 更新邻居的连接
                            old_connections = neighbor_node.connections.copy()
                            neighbor_node.connections = set(new_connections)
                            
                            # 移除不再连接的反向连接
                            for old_conn in old_connections:
                                if old_conn not in neighbor_node.connections and old_conn in self.levels[level]:
                                    self.levels[level][old_conn].remove_connection(neighbor_id)
                
                # 更新入口点
                entry_points = selected_neighbors[:1] if selected_neighbors else entry_points
            
            # 如果新节点层数更高，更新入口点
            if node_level > current_max_layer:
                self.entry_point = node_id
            
            self.current_count += 1
            self.stats.nodes_added += 1
            
            logger.debug(f"Added node {node_id} at level {node_level}, total nodes: {self.current_count}")
            return node_id
    
    def search(
        self, 
        query: np.ndarray, 
        k: int = 10, 
        ef: Optional[int] = None
    ) -> List[Tuple[int, float, Any]]:
        """
        搜索最近邻
        
        Args:
            query: 查询向量
            k: 返回的最近邻数量
            ef: 搜索时的ef参数（如果为None则使用默认值）
            
        Returns:
            (node_id, distance, metadata)的列表
        """
        with self.lock:
            if self.current_count == 0:
                return []
            
            if ef is None:
                ef = max(self.ef_search, k)
            
            # 标准化查询向量（对于余弦距离）
            if self.space == DistanceType.COSINE:
                norm = np.linalg.norm(query)
                if norm > 0:
                    query = query / norm
            
            # 从入口点开始搜索
            entry_points = [self.entry_point]
            current_max_layer = max(self.levels.keys())
            
            # 从顶层搜索到第1层
            for level in range(current_max_layer, 0, -1):
                entry_points = [c.node_id for c in self._search_layer(
                    query, entry_points, 1, level
                )]
            
            # 在第0层进行最终搜索
            candidates = self._search_layer(query, entry_points, max(ef, k), 0)
            
            # 准备结果
            results = []
            for candidate in candidates[:k]:
                metadata = self.metadata.get(candidate.node_id)
                results.append((candidate.node_id, candidate.distance, metadata))
            
            self.stats.searches_performed += 1
            
            return results
    
    def get_stats(self) -> HNSWStats:
        """获取索引统计信息"""
        with self.lock:
            self.stats.total_nodes = self.current_count
            self.stats.max_level = self.max_level
            self.stats.entry_point = self.entry_point
            
            # 计算平均连接数
            total_connections = 0
            for level_nodes in self.levels.values():
                for node in level_nodes.values():
                    total_connections += len(node.connections)
            
            if self.current_count > 0:
                self.stats.avg_connections = total_connections / self.current_count
            
            return self.stats
    
    def save_index(self, filepath: str) -> bool:
        """保存索引到文件"""
        # TODO: 实现索引序列化
        logger.warning("Index saving not implemented yet")
        return False
    
    def load_index(self, filepath: str) -> bool:
        """从文件加载索引"""
        # TODO: 实现索引反序列化
        logger.warning("Index loading not implemented yet")
        return False
    
    def delete_point(self, node_id: int) -> bool:
        """删除指定的点"""
        with self.lock:
            if node_id not in self.data:
                return False
            
            # 移除所有层中的节点
            for level, level_nodes in self.levels.items():
                if node_id in level_nodes:
                    node = level_nodes[node_id]
                    # 移除与其他节点的连接
                    for neighbor_id in node.connections:
                        if neighbor_id in level_nodes:
                            level_nodes[neighbor_id].remove_connection(node_id)
                    # 删除节点
                    del level_nodes[node_id]
            
            # 删除数据
            del self.data[node_id]
            if node_id in self.metadata:
                del self.metadata[node_id]
            
            self.current_count -= 1
            
            # 如果删除的是入口点，需要重新选择
            if node_id == self.entry_point:
                # 简单实现：选择第一个可用节点作为新入口点
                if self.current_count > 0:
                    max_level = max(self.levels.keys()) if self.levels else 0
                    if max_level in self.levels and self.levels[max_level]:
                        self.entry_point = next(iter(self.levels[max_level].keys()))
                    else:
                        self.entry_point = None
                else:
                    self.entry_point = None
            
            return True
    
    def clear(self):
        """清空索引"""
        with self.lock:
            self.levels.clear()
            self.data.clear()
            self.metadata.clear()
            self.entry_point = None
            self.current_count = 0
            self.max_level = 0
            self.stats = HNSWStats()
            
            logger.info("Index cleared")
    
    def get_node_count(self) -> int:
        """获取节点数量"""
        return self.current_count
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.dim
    
    def get_space(self) -> DistanceType:
        """获取距离度量类型"""
        return self.space
