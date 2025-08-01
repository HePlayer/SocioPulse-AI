"""
Distance Metrics - 距离计算函数
提供多种向量距离计算方法，优化性能
"""

import math
from typing import List, Callable
from enum import Enum


class DistanceType(Enum):
    """距离类型枚举"""
    EUCLIDEAN = "euclidean"
    COSINE = "cosine"
    MANHATTAN = "manhattan"
    DOT_PRODUCT = "dot_product"
    HAMMING = "hamming"


class DistanceMetrics:
    """距离计算工具类"""
    
    @staticmethod
    def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
        """欧几里得距离"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))
    
    @staticmethod
    def euclidean_distance_squared(vec1: List[float], vec2: List[float]) -> float:
        """欧几里得距离的平方（避免开方运算，提高性能）"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        return sum((a - b) ** 2 for a, b in zip(vec1, vec2))
    
    @staticmethod
    def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
        """余弦距离 (1 - cosine_similarity)"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        # 计算点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # 计算向量模长
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        # 避免除零错误
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        # 余弦相似度
        cosine_sim = dot_product / (norm1 * norm2)
        
        # 限制在[-1, 1]范围内，避免浮点误差
        cosine_sim = max(-1.0, min(1.0, cosine_sim))
        
        # 返回余弦距离
        return 1.0 - cosine_sim
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """余弦相似度"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        # 计算点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # 计算向量模长
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        # 避免除零错误
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # 余弦相似度
        cosine_sim = dot_product / (norm1 * norm2)
        
        # 限制在[-1, 1]范围内
        return max(-1.0, min(1.0, cosine_sim))
    
    @staticmethod
    def manhattan_distance(vec1: List[float], vec2: List[float]) -> float:
        """曼哈顿距离（L1距离）"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        return sum(abs(a - b) for a, b in zip(vec1, vec2))
    
    @staticmethod
    def dot_product_distance(vec1: List[float], vec2: List[float]) -> float:
        """点积距离（负点积，用于最大化点积）"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        return -sum(a * b for a, b in zip(vec1, vec2))
    
    @staticmethod
    def hamming_distance(vec1: List[float], vec2: List[float]) -> float:
        """汉明距离（用于二进制向量）"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        return sum(1 for a, b in zip(vec1, vec2) if a != b)
    
    @staticmethod
    def get_distance_function(distance_type: DistanceType) -> Callable[[List[float], List[float]], float]:
        """获取距离计算函数"""
        distance_functions = {
            DistanceType.EUCLIDEAN: DistanceMetrics.euclidean_distance_squared,  # 使用平方距离提高性能
            DistanceType.COSINE: DistanceMetrics.cosine_distance,
            DistanceType.MANHATTAN: DistanceMetrics.manhattan_distance,
            DistanceType.DOT_PRODUCT: DistanceMetrics.dot_product_distance,
            DistanceType.HAMMING: DistanceMetrics.hamming_distance
        }
        
        return distance_functions.get(distance_type, DistanceMetrics.euclidean_distance_squared)


class OptimizedDistanceCalculator:
    """优化的距离计算器"""
    
    def __init__(self, distance_type: DistanceType = DistanceType.EUCLIDEAN):
        self.distance_type = distance_type
        self.distance_func = DistanceMetrics.get_distance_function(distance_type)
        
        # 预计算的向量统计信息（用于优化）
        self._vector_norms = {}  # 存储向量的模长
        self._enable_norm_cache = distance_type in [DistanceType.COSINE, DistanceType.DOT_PRODUCT]
    
    def calculate_distance(self, vec1: List[float], vec2: List[float], 
                          vec1_id: str = None, vec2_id: str = None) -> float:
        """计算两个向量之间的距离"""
        # 对于余弦距离，可以使用缓存的向量模长
        if self._enable_norm_cache and self.distance_type == DistanceType.COSINE:
            return self._calculate_cosine_distance_optimized(vec1, vec2, vec1_id, vec2_id)
        
        return self.distance_func(vec1, vec2)
    
    def _calculate_cosine_distance_optimized(self, vec1: List[float], vec2: List[float],
                                           vec1_id: str = None, vec2_id: str = None) -> float:
        """优化的余弦距离计算"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        # 计算点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # 获取或计算向量模长
        norm1 = self._get_or_calculate_norm(vec1, vec1_id)
        norm2 = self._get_or_calculate_norm(vec2, vec2_id)
        
        # 避免除零错误
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        # 余弦相似度
        cosine_sim = dot_product / (norm1 * norm2)
        cosine_sim = max(-1.0, min(1.0, cosine_sim))
        
        return 1.0 - cosine_sim
    
    def _get_or_calculate_norm(self, vector: List[float], vector_id: str = None) -> float:
        """获取或计算向量模长"""
        if vector_id and vector_id in self._vector_norms:
            return self._vector_norms[vector_id]
        
        norm = math.sqrt(sum(x * x for x in vector))
        
        if vector_id:
            self._vector_norms[vector_id] = norm
        
        return norm
    
    def precompute_norm(self, vector: List[float], vector_id: str) -> None:
        """预计算向量模长"""
        if self._enable_norm_cache:
            norm = math.sqrt(sum(x * x for x in vector))
            self._vector_norms[vector_id] = norm
    
    def remove_norm_cache(self, vector_id: str) -> None:
        """移除向量模长缓存"""
        if vector_id in self._vector_norms:
            del self._vector_norms[vector_id]
    
    def clear_norm_cache(self) -> None:
        """清空向量模长缓存"""
        self._vector_norms.clear()
    
    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._vector_norms)


def normalize_vector(vector: List[float]) -> List[float]:
    """向量归一化"""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector.copy()
    return [x / norm for x in vector]


def vector_magnitude(vector: List[float]) -> float:
    """计算向量模长"""
    return math.sqrt(sum(x * x for x in vector))


def vector_dot_product(vec1: List[float], vec2: List[float]) -> float:
    """计算向量点积"""
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
    
    return sum(a * b for a, b in zip(vec1, vec2))


def batch_distance_calculation(query_vector: List[float], 
                             vectors: List[List[float]], 
                             distance_type: DistanceType = DistanceType.EUCLIDEAN) -> List[float]:
    """批量计算距离"""
    distance_func = DistanceMetrics.get_distance_function(distance_type)
    return [distance_func(query_vector, vec) for vec in vectors]


def find_closest_vectors(query_vector: List[float], 
                        vectors: List[List[float]], 
                        k: int = 5,
                        distance_type: DistanceType = DistanceType.EUCLIDEAN) -> List[int]:
    """找到最近的k个向量的索引"""
    distances = batch_distance_calculation(query_vector, vectors, distance_type)
    
    # 获取距离最小的k个索引
    indexed_distances = [(i, dist) for i, dist in enumerate(distances)]
    indexed_distances.sort(key=lambda x: x[1])
    
    return [i for i, _ in indexed_distances[:k]]
