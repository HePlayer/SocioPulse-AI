"""
MemorySystem - 记忆系统
管理情景记忆、程序记忆和语义记忆
"""

import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..FlowTools.base_component import BaseComponent


class MemoryType(Enum):
    """记忆类型"""
    EPISODIC = "episodic"      # 情景记忆
    PROCEDURAL = "procedural"  # 程序记忆  
    SEMANTIC = "semantic"      # 语义记忆


@dataclass
class Memory:
    """记忆条目"""
    content: str
    memory_type: MemoryType
    timestamp: float
    importance_score: float = 1.0
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


class BaseMemory(BaseComponent):
    """基础记忆类"""
    
    def __init__(self, memory_id: str, memory_type: MemoryType):
        super().__init__(memory_id, f"{memory_type.value}_memory")
        self.memory_type = memory_type
        self.memories: List[Memory] = []
        self.max_memories = 1000
    
    def add_memory(self, content: str, metadata: Dict[str, Any] = None, importance_score: float = 1.0) -> str:
        """添加记忆"""
        memory = Memory(
            content=content,
            memory_type=self.memory_type,
            timestamp=time.time(),
            importance_score=importance_score,
            metadata=metadata or {}
        )
        
        self.memories.append(memory)
        
        # 简单的容量管理
        if len(self.memories) > self.max_memories:
            self._cleanup_old_memories()
        
        memory_id = f"mem_{len(self.memories)}_{int(memory.timestamp)}"
        self.log_debug(f"Added {self.memory_type.value} memory", {'memory_id': memory_id})
        
        return memory_id
    
    def search_memories(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索记忆（简单实现）"""
        results = []
        query_lower = query.lower()
        
        for memory in self.memories:
            if query_lower in memory.content.lower():
                memory.access_count += 1
                results.append({
                    'content': memory.content,
                    'memory_type': memory.memory_type.value,
                    'importance_score': memory.importance_score,
                    'access_count': memory.access_count,
                    'metadata': memory.metadata,
                    'similarity_score': 0.8  # 简化的相似度分数
                })
        
        # 按重要性和访问次数排序
        results.sort(key=lambda x: (x['importance_score'], x['access_count']), reverse=True)
        return results[:top_k]
    
    def _cleanup_old_memories(self):
        """清理旧记忆"""
        # 保留重要的记忆
        self.memories.sort(key=lambda x: (x.importance_score, x.access_count), reverse=True)
        self.memories = self.memories[:self.max_memories]
    
    def execute(self, input_data: Any) -> Any:
        if isinstance(input_data, dict):
            action = input_data.get('action')
            if action == 'add_memory':
                return self.add_memory(input_data['content'], input_data.get('metadata'), input_data.get('importance_score', 1.0))
            elif action == 'search_memories':
                return self.search_memories(input_data['query'], input_data.get('top_k', 5))
        return {'error': 'Invalid input'}


class EpisodicMemory(BaseMemory):
    """情景记忆 - 存储特定情境下的经验"""
    
    def __init__(self, memory_id: str = "episodic_memory"):
        super().__init__(memory_id, MemoryType.EPISODIC)


class ProceduralMemory(BaseMemory):
    """程序记忆 - 存储操作流程和技能"""
    
    def __init__(self, memory_id: str = "procedural_memory"):
        super().__init__(memory_id, MemoryType.PROCEDURAL)


class SemanticMemory(BaseMemory):
    """语义记忆 - 存储事实和知识"""
    
    def __init__(self, memory_id: str = "semantic_memory"):
        super().__init__(memory_id, MemoryType.SEMANTIC)


class MemorySystem(BaseComponent):
    """记忆系统 - 统一管理所有类型的记忆"""
    
    def __init__(self, system_id: str = "memory_system"):
        super().__init__(system_id, "memory_system")
        
        # 初始化各类记忆
        self.episodic_memory = EpisodicMemory(f"{system_id}_episodic")
        self.procedural_memory = ProceduralMemory(f"{system_id}_procedural")
        self.semantic_memory = SemanticMemory(f"{system_id}_semantic")
        
        self.log_debug("MemorySystem initialized")
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            'episodic_count': len(self.episodic_memory.memories),
            'procedural_count': len(self.procedural_memory.memories),
            'semantic_count': len(self.semantic_memory.memories),
            'total_memories': (len(self.episodic_memory.memories) + 
                             len(self.procedural_memory.memories) + 
                             len(self.semantic_memory.memories))
        }
    
    def export_memories(self) -> Dict[str, Any]:
        """导出所有记忆"""
        return {
            'episodic': [{'content': m.content, 'metadata': m.metadata} for m in self.episodic_memory.memories],
            'procedural': [{'content': m.content, 'metadata': m.metadata} for m in self.procedural_memory.memories],
            'semantic': [{'content': m.content, 'metadata': m.metadata} for m in self.semantic_memory.memories]
        }
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')
            if action == 'get_statistics':
                return self.get_memory_statistics()
            elif action == 'export_memories':
                return self.export_memories()
        return {'error': 'Invalid input'}
