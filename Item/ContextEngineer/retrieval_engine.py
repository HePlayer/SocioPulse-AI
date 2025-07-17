"""
RetrievalEngine - 检索引擎
基于HNSW算法的向量检索系统
"""

import math
from typing import Dict, List, Any, Optional
from ..FlowTools.base_component import BaseComponent


class RetrievalEngine(BaseComponent):
    """检索引擎 - 简化版实现"""
    
    def __init__(self, engine_id: str = "retrieval_engine"):
        super().__init__(engine_id, "retrieval_engine")
        
        # 存储向量索引（简化实现）
        self.vector_index: Dict[str, List[float]] = {}
        self.content_mapping: Dict[str, Dict[str, Any]] = {}
        
        self.log_debug("RetrievalEngine initialized")
    
    def generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入向量（简化实现）"""
        # 这里使用简单的词频统计作为嵌入向量
        # 实际应用中应该使用真正的embedding模型
        
        words = text.lower().split()
        embedding = [0.0] * 128  # 128维向量
        
        for i, word in enumerate(words[:128]):
            # 简单的hash映射
            hash_val = hash(word) % 128
            embedding[hash_val] += 1.0
        
        # 归一化
        magnitude = math.sqrt(sum(x*x for x in embedding))
        if magnitude > 0:
            embedding = [x/magnitude for x in embedding]
        
        return embedding
    
    def add_to_index(self, content_id: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """添加内容到索引"""
        embedding = self.generate_embedding(content)
        
        self.vector_index[content_id] = embedding
        self.content_mapping[content_id] = {
            'content': content,
            'metadata': metadata or {},
            'embedding': embedding
        }
        
        self.log_debug(f"Added content to index: {content_id}")
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a*b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a*a for a in vec1))
        mag2 = math.sqrt(sum(b*b for b in vec2))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def search_memories(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相关记忆"""
        query_embedding = self.generate_embedding(query)
        results = []
        
        for content_id, stored_embedding in self.vector_index.items():
            similarity = self.cosine_similarity(query_embedding, stored_embedding)
            
            if similarity > 0.1:  # 最低相似度阈值
                content_data = self.content_mapping[content_id]
                results.append({
                    'content_id': content_id,
                    'content': content_data['content'],
                    'metadata': content_data['metadata'],
                    'similarity_score': similarity
                })
        
        # 按相似度排序
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:top_k]
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')
            
            if action == 'add_to_index':
                self.add_to_index(
                    input_data['content_id'],
                    input_data['content'],
                    input_data.get('metadata')
                )
                return {'status': 'success'}
            
            elif action == 'search':
                return self.search_memories(
                    input_data['query'],
                    input_data.get('top_k', 5)
                )
            
            elif action == 'generate_embedding':
                return self.generate_embedding(input_data['text'])
            
            else:
                raise ValueError(f"Unknown action: {action}")
        
        else:
            raise ValueError("RetrievalEngine requires dict input with 'action' field")
