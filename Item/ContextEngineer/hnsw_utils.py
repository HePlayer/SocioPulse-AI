"""
HNSW工具函数
提供HNSW索引的辅助功能和工具方法
"""

import logging
import math
import time
from typing import List, Dict, Set, Optional, Tuple, Any
import numpy as np

from .context_types import Memory, MemoryType

logger = logging.getLogger(__name__)


class HNSWUtils:
    """HNSW索引工具类"""
    
    @staticmethod
    def validate_vector(vector: np.ndarray, expected_dim: int) -> bool:
        """
        验证向量是否有效
        
        Args:
            vector: 要验证的向量
            expected_dim: 期望的维度
            
        Returns:
            是否有效
        """
        if not isinstance(vector, np.ndarray):
            return False
        
        if len(vector.shape) != 1:
            return False
        
        if vector.shape[0] != expected_dim:
            return False
        
        if np.isnan(vector).any() or np.isinf(vector).any():
            return False
        
        return True
    
    @staticmethod
    def normalize_vector(vector: np.ndarray) -> np.ndarray:
        """
        标准化向量（L2归一化）
        
        Args:
            vector: 输入向量
            
        Returns:
            标准化后的向量
        """
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm
    
    @staticmethod
    def calculate_recall(
        ground_truth: List[int], 
        search_results: List[int], 
        k: int
    ) -> float:
        """
        计算搜索结果的召回率
        
        Args:
            ground_truth: 真实的最近邻ID列表
            search_results: 搜索返回的ID列表
            k: 考虑的最近邻数量
            
        Returns:
            召回率（0.0到1.0之间）
        """
        if not ground_truth or not search_results:
            return 0.0
        
        # 取前k个结果
        gt_set = set(ground_truth[:k])
        result_set = set(search_results[:k])
        
        # 计算交集
        intersection = gt_set.intersection(result_set)
        
        # 计算召回率
        recall = len(intersection) / len(gt_set) if gt_set else 0.0
        
        return recall
    
    @staticmethod
    def memory_to_vector(memory: Memory, embedding_dim: int = 768) -> np.ndarray:
        """
        将记忆对象转换为向量表示
        
        Args:
            memory: 记忆对象
            embedding_dim: 向量维度
            
        Returns:
            记忆的向量表示
        """
        # 这里需要实际的嵌入模型来生成向量
        # 暂时使用简单的哈希方法作为占位符
        content = memory.content
        content_hash = hash(content) % (2**32)
        
        # 生成伪向量（实际应用中应该使用真实的embedding模型）
        np.random.seed(content_hash)
        vector = np.random.normal(0, 1, embedding_dim)
        
        # 添加记忆类型的特征
        type_feature = {
            MemoryType.EPISODIC: 0.1,
            MemoryType.PROCEDURAL: 0.5,
            MemoryType.SEMANTIC: 0.9
        }.get(memory.memory_type, 0.0)
        
        # 在向量的最后一个维度添加类型特征
        if embedding_dim > 0:
            vector[-1] = type_feature
        
        return HNSWUtils.normalize_vector(vector)
    
    @staticmethod
    def text_to_vector(text: str, embedding_dim: int = 768) -> np.ndarray:
        """
        将文本转换为向量表示
        
        Args:
            text: 输入文本
            embedding_dim: 向量维度
            
        Returns:
            文本的向量表示
        """
        # 这里需要实际的嵌入模型
        # 暂时使用简单的哈希方法作为占位符
        text_hash = hash(text) % (2**32)
        np.random.seed(text_hash)
        vector = np.random.normal(0, 1, embedding_dim)
        
        return HNSWUtils.normalize_vector(vector)
    
    @staticmethod
    def calculate_diversity_score(vectors: List[np.ndarray]) -> float:
        """
        计算向量集合的多样性分数
        
        Args:
            vectors: 向量列表
            
        Returns:
            多样性分数（越高表示越多样）
        """
        if len(vectors) < 2:
            return 0.0
        
        total_distance = 0.0
        count = 0
        
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                # 计算余弦距离
                cosine_sim = np.dot(vectors[i], vectors[j])
                cosine_distance = 1.0 - cosine_sim
                total_distance += cosine_distance
                count += 1
        
        return total_distance / count if count > 0 else 0.0
    
    @staticmethod
    def select_diverse_subset(
        candidates: List[Tuple[int, float, Any]], 
        max_count: int,
        diversity_weight: float = 0.3
    ) -> List[Tuple[int, float, Any]]:
        """
        从候选列表中选择多样性好的子集
        
        Args:
            candidates: 候选列表，格式为(id, score, vector)
            max_count: 最大选择数量
            diversity_weight: 多样性权重（0.0到1.0）
            
        Returns:
            选择的子集
        """
        if len(candidates) <= max_count:
            return candidates
        
        # 按相关性排序
        candidates_sorted = sorted(candidates, key=lambda x: x[1])
        
        # 贪心选择多样性好的子集
        selected = [candidates_sorted[0]]  # 选择最相关的作为第一个
        remaining = candidates_sorted[1:]
        
        while len(selected) < max_count and remaining:
            best_candidate = None
            best_score = -1
            
            for candidate in remaining:
                # 计算与已选择项的最小距离
                min_distance = float('inf')
                candidate_vector = candidate[2] if len(candidate) > 2 else None
                
                if candidate_vector is not None:
                    for selected_candidate in selected:
                        selected_vector = selected_candidate[2] if len(selected_candidate) > 2 else None
                        if selected_vector is not None:
                            distance = 1.0 - np.dot(candidate_vector, selected_vector)
                            min_distance = min(min_distance, distance)
                
                # 计算综合分数：相关性 + 多样性
                relevance_score = 1.0 / (1.0 + candidate[1])  # 距离越小，相关性越高
                diversity_score = min_distance if min_distance != float('inf') else 0.0
                
                combined_score = (1.0 - diversity_weight) * relevance_score + diversity_weight * diversity_score
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break
        
        return selected
    
    @staticmethod
    def estimate_memory_usage(node_count: int, dim: int, avg_connections: float) -> Dict[str, float]:
        """
        估算索引的内存使用量
        
        Args:
            node_count: 节点数量
            dim: 向量维度
            avg_connections: 平均连接数
            
        Returns:
            内存使用估算（以MB为单位）
        """
        # 向量数据：每个float32占4字节
        vector_memory = node_count * dim * 4 / (1024 * 1024)  # MB
        
        # 连接信息：每个连接ID占4字节
        connections_memory = node_count * avg_connections * 4 / (1024 * 1024)  # MB
        
        # 节点元数据：估算每个节点占100字节
        metadata_memory = node_count * 100 / (1024 * 1024)  # MB
        
        # 索引结构：估算为数据的20%
        index_memory = (vector_memory + connections_memory) * 0.2
        
        total_memory = vector_memory + connections_memory + metadata_memory + index_memory
        
        return {
            'vectors': round(vector_memory, 2),
            'connections': round(connections_memory, 2),
            'metadata': round(metadata_memory, 2),
            'index_structure': round(index_memory, 2),
            'total': round(total_memory, 2)
        }
    
    @staticmethod
    def benchmark_search_performance(
        index, 
        query_vectors: List[np.ndarray], 
        k: int = 10
    ) -> Dict[str, float]:
        """
        基准测试搜索性能
        
        Args:
            index: HNSW索引实例
            query_vectors: 查询向量列表
            k: 搜索的最近邻数量
            
        Returns:
            性能统计
        """
        if not query_vectors:
            return {'avg_time': 0.0, 'total_time': 0.0, 'queries_per_second': 0.0}
        
        total_time = 0.0
        successful_queries = 0
        
        for query in query_vectors:
            try:
                start_time = time.time()
                results = index.search(query, k)
                end_time = time.time()
                
                total_time += (end_time - start_time)
                successful_queries += 1
                
            except Exception as e:
                logger.warning(f"Query failed: {e}")
                continue
        
        if successful_queries == 0:
            return {'avg_time': 0.0, 'total_time': 0.0, 'queries_per_second': 0.0}
        
        avg_time = total_time / successful_queries
        qps = successful_queries / total_time if total_time > 0 else 0.0
        
        return {
            'avg_time': round(avg_time * 1000, 3),  # 毫秒
            'total_time': round(total_time, 3),  # 秒
            'queries_per_second': round(qps, 2),
            'successful_queries': successful_queries,
            'failed_queries': len(query_vectors) - successful_queries
        }
    
    @staticmethod
    def validate_index_consistency(index) -> Dict[str, Any]:
        """
        验证索引的一致性
        
        Args:
            index: HNSW索引实例
            
        Returns:
            一致性检查结果
        """
        issues = []
        stats = {
            'total_nodes': 0,
            'total_connections': 0,
            'orphaned_nodes': 0,
            'invalid_connections': 0,
            'bidirectional_violations': 0
        }
        
        try:
            with index.lock:
                # 检查节点一致性
                all_node_ids = set()
                for level, level_nodes in index.levels.items():
                    for node_id, node in level_nodes.items():
                        all_node_ids.add(node_id)
                        stats['total_nodes'] += 1
                        stats['total_connections'] += len(node.connections)
                        
                        # 检查是否有对应的数据
                        if node_id not in index.data:
                            issues.append(f"Node {node_id} at level {level} has no data")
                        
                        # 检查连接的有效性
                        for conn_id in node.connections:
                            if conn_id not in index.levels.get(level, {}):
                                stats['invalid_connections'] += 1
                                issues.append(f"Node {node_id} at level {level} connects to non-existent node {conn_id}")
                            else:
                                # 检查双向连接
                                connected_node = index.levels[level][conn_id]
                                if node_id not in connected_node.connections:
                                    stats['bidirectional_violations'] += 1
                                    issues.append(f"Bidirectional connection violation between {node_id} and {conn_id} at level {level}")
                
                # 检查数据一致性
                for node_id in index.data:
                    if node_id not in all_node_ids:
                        stats['orphaned_nodes'] += 1
                        issues.append(f"Data exists for node {node_id} but no node structure found")
                
                # 检查入口点
                if index.entry_point is not None:
                    if index.entry_point not in all_node_ids:
                        issues.append(f"Entry point {index.entry_point} does not exist in index")
                
        except Exception as e:
            issues.append(f"Error during consistency check: {e}")
        
        return {
            'is_consistent': len(issues) == 0,
            'issues': issues,
            'stats': stats
        }
