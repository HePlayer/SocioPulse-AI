"""
RetrievalEngine - 检索引擎
基于HNSW算法的高效向量检索系统
"""

import math
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from ..FlowTools.base_component import BaseComponent
from .hnsw_index import HNSWIndex
from .distance_metrics import DistanceType


class RetrievalEngine(BaseComponent):
    """检索引擎 - 基于HNSW的高效实现"""
    
    def __init__(self, 
                 engine_id: str = "retrieval_engine",
                 dimension: int = 128,
                 distance_type: DistanceType = DistanceType.COSINE,
                 M: int = 16,
                 ef_construction: int = 200):
        super().__init__(engine_id, "retrieval_engine")
        
        # HNSW索引配置
        self.dimension = dimension
        self.distance_type = distance_type
        
        # 创建HNSW索引
        self.hnsw_index = HNSWIndex(
            space=distance_type,
            dim=dimension,
            m=M,
            ef_construction=ef_construction
        )
        
        # 内容映射（存储原始内容和元数据）
        self.content_mapping: Dict[str, Dict[str, Any]] = {}
        
        # 嵌入生成配置
        self.embedding_cache: Dict[str, List[float]] = {}
        self.enable_cache = True
        
        self.log_debug("RetrievalEngine initialized", {
            'dimension': dimension,
            'distance_type': distance_type.value,
            'M': M,
            'ef_construction': ef_construction
        })
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        生成文本嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        # 检查缓存
        if self.enable_cache:
            text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            if text_hash in self.embedding_cache:
                return self.embedding_cache[text_hash].copy()
        
        # 生成嵌入向量（改进的实现）
        embedding = self._generate_text_embedding(text)
        
        # 缓存结果
        if self.enable_cache:
            self.embedding_cache[text_hash] = embedding.copy()
        
        return embedding
    
    def _generate_text_embedding(self, text: str) -> List[float]:
        """
        生成文本嵌入向量的核心实现
        使用改进的词频和位置信息
        """
        # 文本预处理
        words = text.lower().split()
        if not words:
            return [0.0] * self.dimension
        
        # 初始化嵌入向量
        embedding = [0.0] * self.dimension
        
        # 词频统计
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 生成嵌入特征
        for i, word in enumerate(words):
            # 基于词的hash值分布到不同维度
            word_hash = hash(word)
            
            # 词频特征
            freq_weight = math.log(1 + word_freq[word])
            
            # 位置特征（早期词汇权重更高）
            position_weight = 1.0 / (1.0 + i * 0.1)
            
            # 长度特征
            length_weight = min(1.0, len(word) / 10.0)
            
            # 组合权重
            total_weight = freq_weight * position_weight * length_weight
            
            # 分布到多个维度
            for j in range(3):  # 每个词影响3个维度
                dim_idx = (word_hash + j) % self.dimension
                embedding[dim_idx] += total_weight
        
        # 添加文本级别特征
        text_length = len(text)
        word_count = len(words)
        avg_word_length = sum(len(word) for word in words) / max(1, word_count)
        
        # 文本统计特征
        stats_features = [
            math.log(1 + text_length) / 10.0,
            math.log(1 + word_count) / 5.0,
            avg_word_length / 10.0,
            len(set(words)) / max(1, word_count)  # 词汇多样性
        ]
        
        # 将统计特征添加到嵌入向量的末尾
        for i, feature in enumerate(stats_features):
            if i < self.dimension:
                embedding[-(i+1)] += feature
        
        # 归一化
        magnitude = math.sqrt(sum(x*x for x in embedding))
        if magnitude > 0:
            embedding = [x/magnitude for x in embedding]
        
        return embedding
    
    def add_to_index(self, content_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        添加内容到索引
        
        Args:
            content_id: 内容ID
            content: 文本内容
            metadata: 元数据
            
        Returns:
            是否添加成功
        """
        try:
            # 生成嵌入向量
            embedding = self.generate_embedding(content)
            
            # 添加到HNSW索引
            import numpy as np
            vector = np.array(embedding)
            node_id = self.hnsw_index.add_point(vector, content_id, {
                'content': content,
                'metadata': metadata or {}
            })
            
            success = node_id is not None
            
            if success:
                # 存储内容映射
                self.content_mapping[content_id] = {
                    'content': content,
                    'metadata': metadata or {},
                    'embedding': embedding
                }
                
                self.log_debug(f"Added content to index: {content_id}", {
                    'content_length': len(content),
                    'embedding_dimension': len(embedding)
                })
            
            return success
            
        except Exception as e:
            self.log_error(f"Failed to add content {content_id} to index", e)
            return False
    
    def update_content(self, content_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        更新索引中的内容
        
        Args:
            content_id: 内容ID
            content: 新的文本内容
            metadata: 新的元数据
            
        Returns:
            是否更新成功
        """
        try:
            # 生成新的嵌入向量
            embedding = self.generate_embedding(content)
            
            # 更新HNSW索引（HNSW索引通常不支持直接更新，需要先删除再添加）
            if content_id in self.content_mapping:
                # 先删除旧记录
                self.hnsw_index.delete_point(content_id)
                
                # 添加新记录
                import numpy as np
                vector = np.array(embedding)
                node_id = self.hnsw_index.add_point(vector, content_id, {
                    'content': content,
                    'metadata': metadata or {}
                })
                
                success = node_id is not None
            else:
                success = False
            
            if success:
                # 更新内容映射
                self.content_mapping[content_id] = {
                    'content': content,
                    'metadata': metadata or {},
                    'embedding': embedding
                }
                
                self.log_debug(f"Updated content in index: {content_id}")
            
            return success
            
        except Exception as e:
            self.log_error(f"Failed to update content {content_id}", e)
            return False
    
    def remove_from_index(self, content_id: str) -> bool:
        """
        从索引中移除内容
        
        Args:
            content_id: 内容ID
            
        Returns:
            是否移除成功
        """
        try:
            # 从HNSW索引中删除
            success = self.hnsw_index.delete_point(content_id)
            
            if success:
                # 从内容映射中移除
                if content_id in self.content_mapping:
                    del self.content_mapping[content_id]
                
                self.log_debug(f"Removed content from index: {content_id}")
            
            return success
            
        except Exception as e:
            self.log_error(f"Failed to remove content {content_id}", e)
            return False
    
    def search_memories(self, query: str, top_k: int = 5, ef: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        搜索相关记忆
        
        Args:
            query: 查询文本
            top_k: 返回的结果数量
            ef: 搜索宽度参数
            
        Returns:
            搜索结果列表
        """
        try:
            # 生成查询嵌入向量
            query_embedding = self.generate_embedding(query)
            
            # 使用HNSW索引搜索
            import numpy as np
            query_vector = np.array(query_embedding)
            search_results = self.hnsw_index.search(query_vector, top_k, ef)
            
            # 格式化结果
            results = []
            for node_id, distance, metadata in search_results:
                if node_id in self.content_mapping:
                    content_data = self.content_mapping[node_id]
                    
                    # 转换距离为相似度分数
                    similarity_score = self._distance_to_similarity(distance)
                    
                    results.append({
                        'content_id': node_id,
                        'content': content_data['content'],
                        'metadata': content_data['metadata'],
                        'similarity_score': similarity_score,
                        'distance': distance
                    })
            
            self.log_debug(f"Search completed", {
                'query_length': len(query),
                'top_k': top_k,
                'results_count': len(results)
            })
            
            return results
            
        except Exception as e:
            self.log_error("Memory search failed", e)
            return []
    
    def search_similar_content(self, query: str, contents: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        在给定的内容列表中搜索相似内容
        
        Args:
            query: 查询文本
            contents: 内容列表
            top_k: 返回的结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            if not contents:
                return []
            
            # 生成查询嵌入向量
            query_embedding = self.generate_embedding(query)
            
            # 为每个内容生成嵌入向量并计算相似度
            content_similarities = []
            for i, content in enumerate(contents):
                content_embedding = self.generate_embedding(content)
                
                # 计算距离
                if self.distance_type == DistanceType.COSINE:
                    distance = self._cosine_distance(query_embedding, content_embedding)
                elif self.distance_type == DistanceType.EUCLIDEAN:
                    distance = self._euclidean_distance(query_embedding, content_embedding)
                else:
                    distance = self._euclidean_distance(query_embedding, content_embedding)
                
                # 转换为相似度分数
                similarity_score = self._distance_to_similarity(distance)
                
                content_similarities.append({
                    'index': i,
                    'content': content,
                    'similarity_score': similarity_score,
                    'distance': distance
                })
            
            # 按相似度排序
            content_similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # 返回前top_k个结果
            return content_similarities[:top_k]
            
        except Exception as e:
            self.log_error("Content similarity search failed", e)
            return []
    
    def _cosine_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦距离"""
        try:
            # 计算点积
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # 计算向量长度
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 1.0  # 最大距离
            
            # 余弦相似度
            cosine_similarity = dot_product / (magnitude1 * magnitude2)
            
            # 转换为距离（0表示最相似，1表示最不相似）
            return 1.0 - cosine_similarity
            
        except Exception:
            return 1.0  # 错误时返回最大距离
    
    def _euclidean_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """计算欧几里得距离"""
        try:
            return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))
        except Exception:
            return float('inf')  # 错误时返回无穷大
    
    def _distance_to_similarity(self, distance: float) -> float:
        """
        将距离转换为相似度分数
        
        Args:
            distance: 距离值
            
        Returns:
            相似度分数 (0-1)
        """
        if self.distance_type == DistanceType.COSINE:
            # 余弦距离转相似度
            return max(0.0, 1.0 - distance)
        elif self.distance_type == DistanceType.EUCLIDEAN:
            # 欧几里得距离转相似度
            return 1.0 / (1.0 + distance)
        else:
            # 通用转换
            return max(0.0, 1.0 / (1.0 + distance))
    
    def batch_search(self, queries: List[str], top_k: int = 5, ef: Optional[int] = None) -> List[List[Dict[str, Any]]]:
        """
        批量搜索
        
        Args:
            queries: 查询列表
            top_k: 每个查询返回的结果数量
            ef: 搜索宽度参数
            
        Returns:
            每个查询的搜索结果
        """
        results = []
        for query in queries:
            result = self.search_memories(query, top_k, ef)
            results.append(result)
        return results
    
    def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定内容
        
        Args:
            content_id: 内容ID
            
        Returns:
            内容数据
        """
        return self.content_mapping.get(content_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取检索引擎统计信息
        
        Returns:
            统计信息字典
        """
        hnsw_stats = self.hnsw_index.get_stats()
        
        return {
            'engine_stats': {
                'total_contents': len(self.content_mapping),
                'dimension': self.dimension,
                'distance_type': self.distance_type.value,
                'cache_size': len(self.embedding_cache),
                'enable_cache': self.enable_cache
            },
            'hnsw_stats': hnsw_stats
        }
    
    def optimize_index(self) -> None:
        """优化索引"""
        try:
            self.hnsw_index.optimize()
            self.log_info("Index optimization completed")
        except Exception as e:
            self.log_error("Index optimization failed", e)
    
    def save_index(self, filepath: str) -> bool:
        """
        保存索引到文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            是否保存成功
        """
        try:
            # 保存HNSW索引
            hnsw_success = self.hnsw_index.save(filepath)
            
            if hnsw_success:
                # 保存内容映射（可选，因为HNSW索引中已包含）
                self.log_info(f"Index saved to {filepath}")
            
            return hnsw_success
            
        except Exception as e:
            self.log_error(f"Failed to save index to {filepath}", e)
            return False
    
    def load_index(self, filepath: str) -> bool:
        """
        从文件加载索引
        
        Args:
            filepath: 文件路径
            
        Returns:
            是否加载成功
        """
        try:
            # 由于HNSWIndex.load方法尚未实现，暂时返回False
            self.log_warning(f"Index loading not implemented yet for {filepath}")
            return False
            
        except Exception as e:
            self.log_error(f"Failed to load index from {filepath}", e)
            return False
    
    def clear_cache(self) -> None:
        """清空嵌入缓存"""
        self.embedding_cache.clear()
        self.log_debug("Embedding cache cleared")
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')
            
            if action == 'add_to_index':
                return self.add_to_index(
                    input_data['content_id'],
                    input_data['content'],
                    input_data.get('metadata')
                )
            
            elif action == 'search':
                return self.search_memories(
                    input_data['query'],
                    input_data.get('top_k', 5),
                    input_data.get('ef')
                )
            
            elif action == 'batch_search':
                return self.batch_search(
                    input_data['queries'],
                    input_data.get('top_k', 5),
                    input_data.get('ef')
                )
            
            elif action == 'update_content':
                return self.update_content(
                    input_data['content_id'],
                    input_data['content'],
                    input_data.get('metadata')
                )
            
            elif action == 'remove_from_index':
                return self.remove_from_index(input_data['content_id'])
            
            elif action == 'generate_embedding':
                return self.generate_embedding(input_data['text'])
            
            elif action == 'get_statistics':
                return self.get_statistics()
            
            elif action == 'optimize':
                self.optimize_index()
                return {'status': 'success'}
            
            elif action == 'save':
                return self.save_index(input_data['filepath'])
            
            elif action == 'load':
                return self.load_index(input_data['filepath'])
            
            else:
                raise ValueError(f"Unknown action: {action}")
        
        else:
            raise ValueError("RetrievalEngine requires dict input with 'action' field")
