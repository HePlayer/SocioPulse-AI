"""
Context Types - 上下文相关的数据类型定义
实现根据5个部分组织的结构化上下文系统
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import time


class MemoryType(Enum):
    """记忆类型枚举"""
    EPISODIC = "episodic"        # 情景记忆 - 特定情景下的行为
    PROCEDURAL = "procedural"    # 程序记忆 - 任务的具体操作流程  
    SEMANTIC = "semantic"        # 语义记忆 - 事实和背景知识


@dataclass
class Memory:
    """记忆条目"""
    id: str
    content: str
    memory_type: MemoryType
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    importance_score: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'content': self.content,
            'memory_type': self.memory_type.value,
            'embedding': self.embedding,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count,
            'importance_score': self.importance_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """从字典创建"""
        return cls(
            id=data['id'],
            content=data['content'],
            memory_type=MemoryType(data['memory_type']),
            embedding=data.get('embedding'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at', time.time()),
            last_accessed=data.get('last_accessed', time.time()),
            access_count=data.get('access_count', 0),
            importance_score=data.get('importance_score', 0.5)
        )


@dataclass  
class ScratchpadEntry:
    """便笺条目"""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'value': self.value,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


@dataclass
class CurrentContext:
    """当前上下文 - 最近3-5轮对话"""
    recent_conversations: List[Dict[str, Any]] = field(default_factory=list)
    session_id: str = ""
    task_progress: Dict[str, Any] = field(default_factory=dict)
    active_tools: List[str] = field(default_factory=list)
    context_summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'recent_conversations': self.recent_conversations,
            'session_id': self.session_id,
            'task_progress': self.task_progress,
            'active_tools': self.active_tools,
            'context_summary': self.context_summary
        }


@dataclass
class StructuredContext:
    """
    结构化上下文系统
    根据5个部分组织：开发者指令、历史对话、用户输入、工具调用结果、外部数据源
    分为3个存储类别：便笺、记忆、当前上下文
    """
    # === 5个输入部分 ===
    developer_instructions: List[str] = field(default_factory=list)  # 开发者指令
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)  # 历史对话
    user_input: str = ""  # 用户输入
    tool_results: List[Dict[str, Any]] = field(default_factory=list)  # 工具调用结果
    external_data: List[Dict[str, Any]] = field(default_factory=list)  # 外部数据源
    
    # === 3个存储类别 ===
    scratchpad: Dict[str, ScratchpadEntry] = field(default_factory=dict)  # 便笺 - 当前会话信息
    memories: List[Memory] = field(default_factory=list)  # 记忆 - 跨会话长期信息
    current_context: CurrentContext = field(default_factory=CurrentContext)  # 当前上下文 - 最近对话
    
    # === 元数据 ===
    context_id: str = ""
    created_at: float = field(default_factory=time.time)
    compressed: bool = False
    compression_ratio: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_scratchpad_entry(self, key: str, value: Any, metadata: Dict[str, Any] = None):
        """添加便笺条目"""
        self.scratchpad[key] = ScratchpadEntry(
            key=key,
            value=value,
            metadata=metadata or {}
        )
    
    def get_scratchpad_value(self, key: str, default: Any = None) -> Any:
        """获取便笺值"""
        entry = self.scratchpad.get(key)
        return entry.value if entry else default
    
    def clear_scratchpad(self):
        """清空便笺（单轮对话后）"""
        self.scratchpad.clear()
    
    def add_memory(self, content: str, memory_type: MemoryType, embedding: List[float] = None, 
                   metadata: Dict[str, Any] = None) -> Memory:
        """添加记忆"""
        memory = Memory(
            id=f"mem_{len(self.memories)}_{int(time.time())}",
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            metadata=metadata or {}
        )
        self.memories.append(memory)
        return memory
    
    def get_memories_by_type(self, memory_type: MemoryType) -> List[Memory]:
        """按类型获取记忆"""
        return [mem for mem in self.memories if mem.memory_type == memory_type]
    
    def update_current_context(self, conversations: List[Dict[str, Any]], max_turns: int = 5):
        """更新当前上下文（最近N轮对话）"""
        self.current_context.recent_conversations = conversations[-max_turns:]
        # 生成上下文摘要
        if conversations:
            recent_content = []
            for conv in self.current_context.recent_conversations:
                if 'user' in conv:
                    recent_content.append(f"用户: {conv['user']}")
                if 'assistant' in conv:
                    recent_content.append(f"助手: {conv['assistant']}")
            self.current_context.context_summary = " | ".join(recent_content[-6:])  # 最近3轮
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            # 5个输入部分
            'developer_instructions': self.developer_instructions,
            'conversation_history': self.conversation_history,
            'user_input': self.user_input,
            'tool_results': self.tool_results,
            'external_data': self.external_data,
            
            # 3个存储类别
            'scratchpad': {k: v.to_dict() for k, v in self.scratchpad.items()},
            'memories': [mem.to_dict() for mem in self.memories],
            'current_context': self.current_context.to_dict(),
            
            # 元数据
            'context_id': self.context_id,
            'created_at': self.created_at,
            'compressed': self.compressed,
            'compression_ratio': self.compression_ratio,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuredContext':
        """从字典创建实例"""
        instance = cls(
            developer_instructions=data.get('developer_instructions', []),
            conversation_history=data.get('conversation_history', []),
            user_input=data.get('user_input', ''),
            tool_results=data.get('tool_results', []),
            external_data=data.get('external_data', []),
            context_id=data.get('context_id', ''),
            created_at=data.get('created_at', time.time()),
            compressed=data.get('compressed', False),
            compression_ratio=data.get('compression_ratio', 1.0),
            metadata=data.get('metadata', {})
        )
        
        # 恢复便笺
        scratchpad_data = data.get('scratchpad', {})
        for key, entry_data in scratchpad_data.items():
            instance.scratchpad[key] = ScratchpadEntry(
                key=entry_data['key'],
                value=entry_data['value'],
                timestamp=entry_data.get('timestamp', time.time()),
                metadata=entry_data.get('metadata', {})
            )
        
        # 恢复记忆
        memories_data = data.get('memories', [])
        instance.memories = [Memory.from_dict(mem_data) for mem_data in memories_data]
        
        # 恢复当前上下文
        current_context_data = data.get('current_context', {})
        instance.current_context = CurrentContext(
            recent_conversations=current_context_data.get('recent_conversations', []),
            session_id=current_context_data.get('session_id', ''),
            task_progress=current_context_data.get('task_progress', {}),
            active_tools=current_context_data.get('active_tools', []),
            context_summary=current_context_data.get('context_summary', '')
        )
        
        return instance
    
    def get_context_size(self) -> Dict[str, int]:
        """获取上下文大小统计"""
        total_chars = len(str(self.to_dict()))
        return {
            'total_characters': total_chars,
            'developer_instructions': len(' '.join(self.developer_instructions)),
            'conversation_history': len(str(self.conversation_history)),
            'user_input': len(self.user_input),
            'tool_results': len(str(self.tool_results)),
            'external_data': len(str(self.external_data)),
            'scratchpad_entries': len(self.scratchpad),
            'memory_count': len(self.memories),
            'recent_conversations': len(self.current_context.recent_conversations)
        }
