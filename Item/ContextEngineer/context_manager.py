"""
ContextManager - 上下文管理器
负责整合和管理所有类型的上下文信息
实现基于5个输入部分和3个存储类别的上下文工程系统
"""

import time
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field

from ..FlowTools.base_component import BaseComponent
from .context_types import StructuredContext, Memory, MemoryType, ScratchpadEntry, CurrentContext
from .scratchpad import Scratchpad
from .memory_system import MemorySystem 
from .retrieval_engine import RetrievalEngine


class ContextManager(BaseComponent):
    """
    上下文管理器 - 实现完整的上下文工程系统
    
    功能特性：
    1. 根据5个部分组织上下文：开发者指令、历史对话、用户输入、工具调用结果、外部数据源
    2. 分为3个存储类别：便笺、记忆、当前上下文
    3. 提供上下文选择和压缩功能
    4. 与流程控制工具集成
    """
    
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
        
        # 当前结构化上下文
        self.current_context: StructuredContext = StructuredContext()
        self.current_context.context_id = str(uuid.uuid4())
        
        # 上下文历史和会话管理
        self.context_history: List[StructuredContext] = []
        self.current_session_id: Optional[str] = None
        
        # 开发者指令存储
        self.global_developer_instructions: List[str] = []
        
        self.log_debug("ContextManager initialized", {
            'max_context_turns': self.max_context_turns,
            'context_window_limit': self.context_window_limit,
            'context_id': self.current_context.context_id
        })
    
    # === 会话管理方法 ===
    
    def start_new_session(self, session_id: str) -> None:
        """开始新的对话会话"""
        # 保存当前会话到历史
        if self.current_session_id and self.current_context.conversation_history:
            self._save_session_to_history()
        
        # 重新初始化当前上下文
        self.current_context = StructuredContext()
        self.current_context.context_id = str(uuid.uuid4())
        self.current_context.current_context.session_id = session_id
        
        # 清空便笺（单轮对话后清除）
        self.current_context.clear_scratchpad()
        
        self.current_session_id = session_id
        
        self.log_info(f"Started new session: {session_id}")
    
    def end_current_session(self) -> None:
        """结束当前会话"""
        if self.current_session_id:
            self._save_session_to_history()
            self.current_context.clear_scratchpad()
            self.current_session_id = None
            self.log_info("Session ended")
    
    # === 5个输入部分的添加方法 ===
    
    def add_developer_instruction(self, instruction: str, source: str = "system") -> None:
        """添加开发者指令"""
        self.current_context.developer_instructions.append(instruction)
        self.global_developer_instructions.append(instruction)
        
        self.log_debug(f"Added developer instruction from {source}", {
            'content_length': len(instruction),
            'total_instructions': len(self.current_context.developer_instructions)
        })
    
    def add_conversation_history(self, conversation_data: Dict[str, Any]) -> None:
        """添加历史对话"""
        self.current_context.conversation_history.append(conversation_data)
        
        # 更新当前上下文
        self.current_context.update_current_context(self.current_context.conversation_history)
        
        self.log_debug("Added conversation history", {
            'total_history': len(self.current_context.conversation_history)
        })
    
    def set_user_input(self, user_input: str, user_id: str = "user") -> None:
        """设置用户输入"""
        self.current_context.user_input = user_input
        
        # 添加到便笺
        self.current_context.add_scratchpad_entry(
            "current_user_input", 
            {
                'content': user_input,
                'user_id': user_id,
                'timestamp': time.time()
            }
        )
        
        self.log_debug(f"Set user input from {user_id}", {
            'content_length': len(user_input)
        })
    
    def add_tool_result(self, tool_name: str, result: Any, metadata: Dict[str, Any] = None) -> None:
        """添加工具调用结果"""
        result_data = {
            'tool_name': tool_name,
            'result': result,
            'result_type': type(result).__name__,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        
        self.current_context.tool_results.append(result_data)
        
        # 添加到便笺
        self.current_context.add_scratchpad_entry(
            f"tool_result_{tool_name}_{int(time.time())}", 
            result_data
        )
        
        self.log_debug(f"Added tool result: {tool_name}", {
            'result_type': type(result).__name__,
            'total_tool_results': len(self.current_context.tool_results)
        })
    
    def add_external_data(self, data: Any, source: str = "external", metadata: Dict[str, Any] = None) -> None:
        """添加外部数据源"""
        external_data = {
            'content': data,
            'source': source,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        
        self.current_context.external_data.append(external_data)
        
        self.log_debug(f"Added external data from {source}", {
            'data_type': type(data).__name__,
            'total_external_data': len(self.current_context.external_data)
        })
    
    def add_conversation_turn(self, user_message: str, assistant_response: str, metadata: Dict[str, Any] = None) -> None:
        """添加完整的对话轮次"""
        turn_data = {
            'user': user_message,
            'assistant': assistant_response,
            'timestamp': time.time(),
            'session_id': self.current_session_id,
            'metadata': metadata or {}
        }
        
        self.add_conversation_history(turn_data)
        
        # 清空便笺（单轮对话后）
        self.current_context.clear_scratchpad()
        
        self.log_debug("Added conversation turn", {
            'user_length': len(user_message),
            'assistant_length': len(assistant_response)
        })
    
    # === 记忆系统方法 ===
    
    def add_memory(self, content: str, memory_type: MemoryType, embedding: List[float] = None, 
                   metadata: Dict[str, Any] = None) -> Memory:
        """添加记忆"""
        # 生成嵌入向量
        if embedding is None:
            try:
                embedding = self.retrieval_engine.generate_embedding(content)
            except Exception as e:
                self.log_warning(f"Failed to generate embedding for memory", {'error': str(e)})
                embedding = []
        
        memory = self.current_context.add_memory(content, memory_type, embedding, metadata)
        
        # 同时添加到记忆系统
        try:
            if memory_type == MemoryType.EPISODIC:
                self.memory_system.add_episodic_memory(content, metadata or {})
            elif memory_type == MemoryType.PROCEDURAL:
                self.memory_system.add_procedural_memory(content, metadata or {})
            elif memory_type == MemoryType.SEMANTIC:
                self.memory_system.add_semantic_memory(content, metadata or {})
        except Exception as e:
            self.log_warning(f"Failed to add memory to memory system", {'error': str(e)})
        
        self.log_debug(f"Added {memory_type.value} memory", {
            'content_length': len(content),
            'memory_id': memory.id
        })
        
        return memory
    
    def retrieve_relevant_memories(self, query: str, top_k: int = 5, memory_types: List[MemoryType] = None) -> List[Memory]:
        """检索相关记忆"""
        all_memories = self.current_context.memories
        
        # 按类型筛选
        if memory_types:
            filtered_memories = []
            for mem in all_memories:
                if mem.memory_type in memory_types:
                    filtered_memories.append(mem)
            all_memories = filtered_memories
        
        try:
            # 使用检索引擎
            results = self.retrieval_engine.search_similar_content(
                query, 
                [mem.content for mem in all_memories],
                top_k
            )
            
            relevant_memories = []
            for result in results:
                # 找到对应的记忆对象
                for mem in all_memories:
                    if mem.content == result.get('content'):
                        mem.last_accessed = time.time()
                        mem.access_count += 1
                        relevant_memories.append(mem)
                        break
            
            return relevant_memories
            
        except Exception as e:
            self.log_error("Failed to retrieve relevant memories", e)
            return []
    
    # === 上下文构建和选择方法 ===
    
    def build_structured_context(self, 
                                query: str = "",
                                include_recent_turns: int = None,
                                include_retrieved_memory: bool = True,
                                auto_compress: bool = True) -> StructuredContext:
        """
        构建结构化上下文 - 核心方法
        
        根据5个输入部分构建完整的上下文：
        1. 开发者指令
        2. 历史对话  
        3. 用户输入
        4. 工具调用结果
        5. 外部数据源（检索到的记忆）
        """
        if include_recent_turns is None:
            include_recent_turns = self.max_context_turns
        
        # 使用当前上下文作为基础
        context = StructuredContext()
        context.context_id = str(uuid.uuid4())
        
        # 1. 开发者指令 - 从全局指令和当前上下文获取
        context.developer_instructions = self.global_developer_instructions.copy()
        context.developer_instructions.extend(self.current_context.developer_instructions)
        
        # 2. 历史对话 - 获取最近N轮对话
        recent_conversations = self.current_context.conversation_history[-include_recent_turns:]
        context.conversation_history = recent_conversations
        
        # 3. 用户输入 - 优先使用已设置的用户输入，如果没有则使用查询
        context.user_input = self.current_context.user_input if self.current_context.user_input else query
        
        # 4. 工具调用结果 - 从当前上下文获取
        context.tool_results = self.current_context.tool_results.copy()
        
        # 5. 外部数据源 - 检索相关记忆
        if include_retrieved_memory and context.user_input:
            retrieved_memories = self.retrieve_relevant_memories(context.user_input)
            context.external_data = [
                {
                    'content': mem.content,
                    'memory_type': mem.memory_type.value,
                    'importance_score': mem.importance_score,
                    'access_count': mem.access_count,
                    'source': 'memory_retrieval',
                    'metadata': mem.metadata
                }
                for mem in retrieved_memories
            ]
        else:
            context.external_data = self.current_context.external_data.copy()
        
        # 复制便笺、记忆和当前上下文信息
        context.scratchpad = self.current_context.scratchpad.copy()
        context.memories = self.current_context.memories.copy()
        context.current_context = CurrentContext(
            recent_conversations=recent_conversations,
            session_id=self.current_session_id or "",
            task_progress=self.current_context.current_context.task_progress.copy(),
            active_tools=self.current_context.current_context.active_tools.copy(),
            context_summary=self.current_context.current_context.context_summary
        )
        
        # 计算上下文大小
        context_size = context.get_context_size()
        
        # 添加元数据
        context.metadata = {
            'session_id': self.current_session_id,
            'build_timestamp': time.time(),
            'context_size': context_size,
            'compression_applied': False,
            'build_method': 'structured_context_engineering'
        }
        
        # 检查是否需要压缩
        if auto_compress and self._should_compress_context(context):
            context = self._compress_context(context)
            context.metadata['compression_applied'] = True
        
        self.log_debug("Built structured context", {
            'developer_instructions': len(context.developer_instructions),
            'conversation_turns': len(context.conversation_history),
            'tool_results': len(context.tool_results),
            'external_data': len(context.external_data),
            'context_size': context_size,
            'compression_applied': context.metadata['compression_applied']
        })
        
        return context
    
    def select_context_for_prompt(self, query: str, max_context_size: int = None) -> StructuredContext:
        """
        为特定查询选择最合适的上下文
        
        使用HNSW算法从记忆中检索最相关的上下文信息
        """
        if max_context_size is None:
            max_context_size = self.context_window_limit
        
        # 1. 构建初始上下文
        context = self.build_structured_context(query, auto_compress=False)
        
        # 2. 检查当前大小
        current_size = context.get_context_size()['total_characters']
        
        if current_size <= max_context_size:
            return context  # 大小合适，直接返回
        
        # 3. 需要选择性包含内容
        selected_context = StructuredContext()
        selected_context.context_id = str(uuid.uuid4())
        selected_context.user_input = query
        
        # 保留开发者指令（高优先级）
        selected_context.developer_instructions = context.developer_instructions
        
        # 计算剩余空间
        used_size = len(' '.join(context.developer_instructions)) + len(query)
        remaining_size = max_context_size - used_size
        
        # 4. 按优先级选择内容
        priority_items = []
        
        # 添加最近的对话（高优先级）
        for conv in reversed(context.conversation_history):
            conv_size = len(json.dumps(conv, ensure_ascii=False))
            priority_items.append({
                'content': conv,
                'size': conv_size,
                'priority': 3,  # 高优先级
                'type': 'conversation'
            })
        
        # 添加工具结果（中等优先级）
        for tool_result in context.tool_results:
            result_size = len(json.dumps(tool_result, ensure_ascii=False))
            priority_items.append({
                'content': tool_result,
                'size': result_size,
                'priority': 2,  # 中等优先级
                'type': 'tool_result'
            })
        
        # 添加外部数据（根据相似度确定优先级）
        for ext_data in context.external_data:
            data_size = len(json.dumps(ext_data, ensure_ascii=False))
            similarity_score = ext_data.get('importance_score', 0.5)
            priority_items.append({
                'content': ext_data,
                'size': data_size,
                'priority': 1 + similarity_score,  # 根据相似度调整优先级
                'type': 'external_data'
            })
        
        # 5. 按优先级排序并选择
        priority_items.sort(key=lambda x: x['priority'], reverse=True)
        
        current_size = used_size
        for item in priority_items:
            if current_size + item['size'] <= remaining_size:
                if item['type'] == 'conversation':
                    selected_context.conversation_history.append(item['content'])
                elif item['type'] == 'tool_result':
                    selected_context.tool_results.append(item['content'])
                elif item['type'] == 'external_data':
                    selected_context.external_data.append(item['content'])
                
                current_size += item['size']
            else:
                break  # 空间不足，停止添加
        
        # 6. 恢复对话顺序
        selected_context.conversation_history.reverse()
        
        # 7. 更新元数据
        selected_context.metadata = {
            'session_id': self.current_session_id,
            'build_timestamp': time.time(),
            'context_size': selected_context.get_context_size(),
            'selection_applied': True,
            'max_context_size': max_context_size,
            'original_size': current_size
        }
        
        self.log_debug("Selected context for prompt", {
            'original_size': context.get_context_size()['total_characters'],
            'selected_size': selected_context.get_context_size()['total_characters'],
            'max_size': max_context_size,
            'reduction_ratio': 1 - (selected_context.get_context_size()['total_characters'] / context.get_context_size()['total_characters'])
        })
        
        return selected_context
    
    def format_context_for_model(self, context: StructuredContext, format_type: str = "json") -> str:
        """
        将结构化上下文格式化为模型可读的格式
        
        Args:
            context: 结构化上下文对象
            format_type: 格式类型 ("json", "markdown", "text")
        
        Returns:
            格式化后的上下文字符串
        """
        if format_type == "json":
            return json.dumps(context.to_dict(), ensure_ascii=False, indent=2)
        
        elif format_type == "markdown":
            md_content = []
            
            # 开发者指令
            if context.developer_instructions:
                md_content.append("## 开发者指令")
                for i, instruction in enumerate(context.developer_instructions, 1):
                    md_content.append(f"{i}. {instruction}")
                md_content.append("")
            
            # 历史对话
            if context.conversation_history:
                md_content.append("## 对话历史")
                for i, conv in enumerate(context.conversation_history, 1):
                    md_content.append(f"### 对话 {i}")
                    md_content.append(f"**用户**: {conv.get('user', '')}")
                    md_content.append(f"**助手**: {conv.get('assistant', '')}")
                    md_content.append("")
            
            # 用户输入
            if context.user_input:
                md_content.append("## 当前用户输入")
                md_content.append(context.user_input)
                md_content.append("")
            
            # 工具结果
            if context.tool_results:
                md_content.append("## 工具调用结果")
                for i, result in enumerate(context.tool_results, 1):
                    tool_name = result.get('tool_name', '未知工具')
                    md_content.append(f"### {i}. {tool_name}")
                    md_content.append(f"```json")
                    md_content.append(json.dumps(result.get('result', ''), ensure_ascii=False, indent=2))
                    md_content.append(f"```")
                    md_content.append("")
            
            # 外部数据
            if context.external_data:
                md_content.append("## 相关记忆")
                for i, data in enumerate(context.external_data, 1):
                    md_content.append(f"### {i}. {data.get('memory_type', '未知类型')}记忆")
                    md_content.append(data.get('content', ''))
                    md_content.append("")
            
            return "\n".join(md_content)
        
        elif format_type == "text":
            text_content = []
            
            if context.developer_instructions:
                text_content.append("=== 开发者指令 ===")
                text_content.extend(context.developer_instructions)
                text_content.append("")
            
            if context.conversation_history:
                text_content.append("=== 对话历史 ===")
                for conv in context.conversation_history:
                    text_content.append(f"用户: {conv.get('user', '')}")
                    text_content.append(f"助手: {conv.get('assistant', '')}")
                    text_content.append("-" * 20)
                text_content.append("")
            
            if context.user_input:
                text_content.append("=== 当前用户输入 ===")
                text_content.append(context.user_input)
                text_content.append("")
            
            if context.tool_results:
                text_content.append("=== 工具调用结果 ===")
                for result in context.tool_results:
                    text_content.append(f"工具: {result.get('tool_name', '未知')}")
                    text_content.append(f"结果: {str(result.get('result', ''))}")
                    text_content.append("-" * 20)
                text_content.append("")
            
            if context.external_data:
                text_content.append("=== 相关记忆 ===")
                for data in context.external_data:
                    text_content.append(f"{data.get('memory_type', '未知')}记忆: {data.get('content', '')}")
                    text_content.append("-" * 20)
                text_content.append("")
            
            return "\n".join(text_content)
        
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
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
        total_size += len(str(context.scratchpad))
        total_size += sum(len(mem.content) for mem in context.memories)
        
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
            'context_history': [ctx.to_dict() for ctx in self.context_history],
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
            
            elif action == 'get_summary':
                return self.get_context_summary()
            
            else:
                raise ValueError(f"Unknown action: {action}")
        
        else:
            raise ValueError("ContextManager requires dict input with 'action' field")
