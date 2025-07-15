"""
ContextManager - 上下文管理器
负责整合和管理所有类型的上下文信息
"""

import time
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from ..FlowTools.base_component import BaseComponent
from .scratchpad import Scratchpad
from .memory_system import MemorySystem
from .retrieval_engine import RetrievalEngine
from .context_types import StructuredContext


class ContextType(Enum):
    """上下文类型枚举"""
    DEVELOPER_INSTRUCTION = "developer_instruction"
    HISTORICAL_CONVERSATION = "historical_conversation"
    USER_INPUT = "user_input"
    TOOL_RESULT = "tool_result"
    EXTERNAL_DATA = "external_data"
    SYSTEM_MESSAGE = "system_message"


@dataclass
class ContextEntry:
    """上下文条目"""
    content: str
    context_type: ContextType
    timestamp: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance_score: float = 1.0
    embedding: Optional[List[float]] = None


class ContextManager(BaseComponent):
    """上下文管理器 - 统一管理所有上下文信息"""
    
    def __init__(self, manager_id: str = "default_context_manager"):
        super().__init__(manager_id, "context_manager")
        
        # 初始化子系统
        self.scratchpad = Scratchpad(f"{manager_id}_scratchpad")
        self.memory_system = MemorySystem(f"{manager_id}_memory")
        self.retrieval_engine = RetrievalEngine(f"{manager_id}_retrieval")
        
        # 延迟导入以避免循环依赖
        from .context_compressor import ContextCompressor
        self.context_compressor = ContextCompressor(f"{manager_id}_compressor")
        
        # 当前上下文设置
        self.max_context_turns = 5
        self.context_window_limit = 8000  # 字符数限制
        self.compression_threshold = 0.95  # 达到95%时压缩
        
        # 上下文历史
        self.context_history: List[StructuredContext] = []
        self.current_session_id: Optional[str] = None
        
        self.log_debug("ContextManager initialized", {
            'max_context_turns': self.max_context_turns,
            'context_window_limit': self.context_window_limit
        })
    
    def start_new_session(self, session_id: str) -> None:
        """开始新的对话会话"""
        # 清空便笺
        self.scratchpad.clear()
        
        # 保存当前会话的上下文到历史
        if self.current_session_id:
            self._save_session_to_history()
        
        self.current_session_id = session_id
        
        self.log_info(f"Started new session: {session_id}")
    
    def add_context_entry(self, 
                         content: str,
                         context_type: ContextType,
                         source: str = "unknown",
                         metadata: Dict[str, Any] = None,
                         importance_score: float = 1.0) -> None:
        """添加上下文条目"""
        entry = ContextEntry(
            content=content,
            context_type=context_type,
            timestamp=time.time(),
            source=source,
            metadata=metadata or {},
            importance_score=importance_score
        )
        
        # 根据类型处理上下文
        if context_type in [ContextType.USER_INPUT, ContextType.TOOL_RESULT]:
            # 添加到便笺
            self.scratchpad.add_entry(entry.content, entry.context_type.value, entry.metadata)
        
        # 生成嵌入向量（用于检索）
        try:
            entry.embedding = self.retrieval_engine.generate_embedding(content)
        except Exception as e:
            self.log_warning(f"Failed to generate embedding for context entry", {'error': str(e)})
        
        self.log_debug(f"Added context entry: {context_type.value}", {
            'source': source,
            'content_length': len(content),
            'importance_score': importance_score
        })
    
    def add_developer_instruction(self, instruction: str, source: str = "system") -> None:
        """添加开发者指令"""
        self.add_context_entry(
            instruction, 
            ContextType.DEVELOPER_INSTRUCTION, 
            source,
            importance_score=2.0  # 开发者指令重要性较高
        )
    
    def add_user_input(self, user_input: str, user_id: str = "user") -> None:
        """添加用户输入"""
        self.add_context_entry(
            user_input,
            ContextType.USER_INPUT,
            f"user_{user_id}",
            metadata={'user_id': user_id},
            importance_score=1.5
        )
    
    def add_tool_result(self, tool_name: str, result: Any, metadata: Dict[str, Any] = None) -> None:
        """添加工具调用结果"""
        result_str = json.dumps(result, ensure_ascii=False, default=str) if not isinstance(result, str) else result
        
        tool_metadata = metadata or {}
        tool_metadata.update({
            'tool_name': tool_name,
            'result_type': type(result).__name__
        })
        
        self.add_context_entry(
            result_str,
            ContextType.TOOL_RESULT,
            f"tool_{tool_name}",
            tool_metadata,
            importance_score=1.2
        )
    
    def add_conversation_turn(self, 
                            user_message: str, 
                            assistant_response: str,
                            metadata: Dict[str, Any] = None) -> None:
        """添加对话轮次"""
        turn_metadata = metadata or {}
        turn_metadata.update({
            'turn_timestamp': time.time(),
            'session_id': self.current_session_id
        })
        
        # 将对话轮次组合为一个条目
        conversation_content = json.dumps({
            'user': user_message,
            'assistant': assistant_response,
            'metadata': turn_metadata
        }, ensure_ascii=False)
        
        self.add_context_entry(
            conversation_content,
            ContextType.HISTORICAL_CONVERSATION,
            "conversation",
            turn_metadata,
            importance_score=1.0
        )
    
    def build_structured_context(self, 
                                query: str = "",
                                include_recent_turns: int = None,
                                include_retrieved_memory: bool = True) -> StructuredContext:
        """构建结构化上下文"""
        if include_recent_turns is None:
            include_recent_turns = self.max_context_turns
        
        context = StructuredContext()
        
        # 1. 获取开发者指令
        context.developer_instructions = self._get_developer_instructions()
        
        # 2. 获取最近的对话历史
        context.conversation_history = self._get_recent_conversation_history(include_recent_turns)
        
        # 3. 设置当前用户输入
        context.user_input = query
        
        # 4. 获取便笺中的工具结果
        context.tool_results = self._get_scratchpad_tool_results()
        
        # 5. 检索相关记忆
        if include_retrieved_memory and query:
            retrieved_memories = self._retrieve_relevant_memories(query)
            context.external_data = retrieved_memories
        
        # 6. 添加元数据
        context.metadata = {
            'session_id': self.current_session_id,
            'build_timestamp': time.time(),
            'context_size': self._estimate_context_size(context),
            'compression_applied': False
        }
        
        # 7. 检查是否需要压缩
        if self._should_compress_context(context):
            context = self._compress_context(context)
            context.metadata['compression_applied'] = True
        
        self.log_debug("Built structured context", {
            'developer_instructions': len(context.developer_instructions),
            'conversation_turns': len(context.conversation_history),
            'tool_results': len(context.tool_results),
            'external_data': len(context.external_data),
            'estimated_size': context.metadata['context_size'],
            'compression_applied': context.metadata['compression_applied']
        })
        
        return context
    
    def _get_developer_instructions(self) -> List[str]:
        """获取开发者指令"""
        # 这里可以从配置文件、数据库或其他来源获取
        # 暂时返回空列表，具体实现可以后续完善
        return []
    
    def _get_recent_conversation_history(self, max_turns: int) -> List[Dict[str, Any]]:
        """获取最近的对话历史"""
        history = []
        
        # 从便笺获取当前会话的对话
        scratchpad_entries = self.scratchpad.get_entries_by_type("historical_conversation")
        
        # 按时间戳排序，取最近的几轮
        sorted_entries = sorted(scratchpad_entries, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        for entry in sorted_entries[:max_turns]:
            try:
                conversation_data = json.loads(entry['content'])
                history.append(conversation_data)
            except json.JSONDecodeError:
                self.log_warning("Invalid conversation entry in scratchpad", {'entry': entry})
        
        return list(reversed(history))  # 恢复时间顺序
    
    def _get_scratchpad_tool_results(self) -> List[Dict[str, Any]]:
        """获取便笺中的工具结果"""
        tool_results = []
        
        tool_entries = self.scratchpad.get_entries_by_type("tool_result")
        
        for entry in tool_entries:
            tool_results.append({
                'content': entry['content'],
                'metadata': entry.get('metadata', {}),
                'timestamp': entry.get('timestamp', 0)
            })
        
        return tool_results
    
    def _retrieve_relevant_memories(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        try:
            # 使用检索引擎查找相关记忆
            retrieved_memories = self.retrieval_engine.search_memories(query, top_k)
            
            external_data = []
            for memory in retrieved_memories:
                external_data.append({
                    'content': memory.get('content', ''),
                    'memory_type': memory.get('memory_type', 'unknown'),
                    'similarity_score': memory.get('similarity_score', 0.0),
                    'source': 'memory_retrieval',
                    'metadata': memory.get('metadata', {})
                })
            
            return external_data
            
        except Exception as e:
            self.log_error("Failed to retrieve relevant memories", e)
            return []
    
    def _estimate_context_size(self, context: StructuredContext) -> int:
        """估算上下文大小（字符数）"""
        total_size = 0
        
        # 计算各部分的大小
        total_size += sum(len(instr) for instr in context.developer_instructions)
        total_size += sum(len(json.dumps(turn, ensure_ascii=False)) for turn in context.conversation_history)
        total_size += len(context.user_input)
        total_size += sum(len(json.dumps(result, ensure_ascii=False)) for result in context.tool_results)
        total_size += sum(len(json.dumps(data, ensure_ascii=False)) for data in context.external_data)
        total_size += sum(len(msg) for msg in context.system_messages)
        
        return total_size
    
    def _should_compress_context(self, context: StructuredContext) -> bool:
        """判断是否需要压缩上下文"""
        current_size = self._estimate_context_size(context)
        return current_size >= (self.context_window_limit * self.compression_threshold)
    
    def _compress_context(self, context: StructuredContext) -> StructuredContext:
        """压缩上下文"""
        try:
            compressed_context = self.context_compressor.compress_structured_context(context)
            
            self.log_info("Context compressed", {
                'original_size': self._estimate_context_size(context),
                'compressed_size': self._estimate_context_size(compressed_context),
                'compression_ratio': self._estimate_context_size(compressed_context) / self._estimate_context_size(context)
            })
            
            return compressed_context
            
        except Exception as e:
            self.log_error("Context compression failed", e)
            return context  # 返回原始上下文
    
    def _save_session_to_history(self) -> None:
        """将当前会话保存到历史"""
        if not self.current_session_id:
            return
        
        # 构建会话的完整上下文
        session_context = self.build_structured_context(include_retrieved_memory=False)
        self.context_history.append(session_context)
        
        # 将重要信息保存到记忆系统
        self._save_to_memory_system()
        
        self.log_debug(f"Saved session {self.current_session_id} to history")
    
    def _save_to_memory_system(self) -> None:
        """将上下文信息保存到记忆系统"""
        try:
            # 保存对话记忆（情景记忆）
            scratchpad_entries = self.scratchpad.get_all_entries()
            for entry in scratchpad_entries:
                if entry.get('context_type') == 'historical_conversation':
                    self.memory_system.episodic_memory.add_memory(
                        entry['content'],
                        entry.get('metadata', {}),
                        importance_score=entry.get('importance_score', 1.0)
                    )
            
            # 这里可以添加更多的记忆保存逻辑
            
        except Exception as e:
            self.log_error("Failed to save to memory system", e)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """获取上下文管理器的摘要信息"""
        return {
            'manager_id': self.component_id,
            'current_session_id': self.current_session_id,
            'scratchpad_entries': len(self.scratchpad.get_all_entries()),
            'context_history_count': len(self.context_history),
            'memory_statistics': self.memory_system.get_memory_statistics(),
            'configuration': {
                'max_context_turns': self.max_context_turns,
                'context_window_limit': self.context_window_limit,
                'compression_threshold': self.compression_threshold
            }
        }
    
    def clear_session_data(self) -> None:
        """清空当前会话数据"""
        self.scratchpad.clear()
        self.current_session_id = None
        self.log_info("Session data cleared")
    
    def export_context_data(self) -> Dict[str, Any]:
        """导出上下文数据（用于备份或迁移）"""
        return {
            'context_history': [
                {
                    'developer_instructions': ctx.developer_instructions,
                    'conversation_history': ctx.conversation_history,
                    'user_input': ctx.user_input,
                    'tool_results': ctx.tool_results,
                    'external_data': ctx.external_data,
                    'system_messages': ctx.system_messages,
                    'metadata': ctx.metadata
                }
                for ctx in self.context_history
            ],
            'scratchpad_data': self.scratchpad.export_data(),
            'memory_data': self.memory_system.export_memories(),
            'configuration': {
                'max_context_turns': self.max_context_turns,
                'context_window_limit': self.context_window_limit,
                'compression_threshold': self.compression_threshold
            }
        }
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')
            
            if action == 'build_context':
                query = input_data.get('query', '')
                return self.build_structured_context(query)
            
            elif action == 'add_context':
                self.add_context_entry(
                    input_data['content'],
                    ContextType(input_data['context_type']),
                    input_data.get('source', 'unknown'),
                    input_data.get('metadata'),
                    input_data.get('importance_score', 1.0)
                )
                return {'status': 'success'}
            
            elif action == 'get_summary':
                return self.get_context_summary()
            
            else:
                raise ValueError(f"Unknown action: {action}")
        
        else:
            raise ValueError("ContextManager requires dict input with 'action' field")
