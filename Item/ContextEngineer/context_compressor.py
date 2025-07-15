"""
ContextCompressor - 上下文压缩器
使用COCOM方法进行上下文压缩
"""

from typing import Dict, List, Any, Optional
from ..FlowTools.base_component import BaseComponent
from .context_types import StructuredContext


class ContextCompressor(BaseComponent):
    """上下文压缩器 - 简化版实现"""
    
    def __init__(self, compressor_id: str = "context_compressor"):
        super().__init__(compressor_id, "context_compressor")
        
        # 压缩配置
        self.compression_ratio = 0.7  # 目标压缩到原来的70%
        self.min_importance_threshold = 0.5
        
        self.log_debug("ContextCompressor initialized")
    
    def compress_text(self, text: str, target_ratio: float = None) -> str:
        """压缩文本（简化实现）"""
        if target_ratio is None:
            target_ratio = self.compression_ratio
        
        sentences = text.split('.')
        if len(sentences) <= 1:
            return text
        
        # 计算目标句子数
        target_count = max(1, int(len(sentences) * target_ratio))
        
        # 简单的重要性评分（基于句子长度和关键词）
        scored_sentences = []
        keywords = ['重要', '关键', '必须', '需要', '问题', '解决', '结果', '错误', '成功']
        
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                score = len(sentence.strip())  # 基础分数：句子长度
                
                # 关键词加分
                for keyword in keywords:
                    if keyword in sentence:
                        score += 50
                
                # 位置加分（开头和结尾的句子更重要）
                if i == 0 or i == len(sentences) - 1:
                    score += 30
                
                scored_sentences.append((sentence.strip(), score))
        
        # 按分数排序，保留重要的句子
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        selected_sentences = [s[0] for s in scored_sentences[:target_count]]
        
        return '. '.join(selected_sentences) + '.'
    
    def compress_conversation_history(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """压缩对话历史"""
        if len(conversations) <= 2:
            return conversations
        
        # 保留最新的对话，压缩较旧的对话
        compressed = []
        
        # 保留最近2轮完整对话
        recent_conversations = conversations[-2:]
        older_conversations = conversations[:-2]
        
        # 压缩较旧的对话
        for conv in older_conversations:
            compressed_conv = conv.copy()
            
            if 'user' in compressed_conv:
                compressed_conv['user'] = self.compress_text(compressed_conv['user'], 0.5)
            
            if 'assistant' in compressed_conv:
                compressed_conv['assistant'] = self.compress_text(compressed_conv['assistant'], 0.5)
            
            compressed.append(compressed_conv)
        
        # 添加最近的完整对话
        compressed.extend(recent_conversations)
        
        return compressed
    
    def compress_tool_results(self, tool_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """压缩工具结果"""
        compressed = []
        
        for result in tool_results:
            compressed_result = result.copy()
            
            if 'content' in compressed_result:
                # 工具结果通常比较重要，压缩比例较小
                compressed_result['content'] = self.compress_text(compressed_result['content'], 0.8)
            
            compressed.append(compressed_result)
        
        return compressed
    
    def compress_external_data(self, external_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """压缩外部数据"""
        # 按重要性过滤和压缩
        filtered_data = []
        
        for data in external_data:
            importance = data.get('similarity_score', 0.5)
            
            if importance >= self.min_importance_threshold:
                compressed_data = data.copy()
                
                if 'content' in compressed_data:
                    compressed_data['content'] = self.compress_text(compressed_data['content'], 0.6)
                
                filtered_data.append(compressed_data)
        
        # 只保留最重要的几个
        filtered_data.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        return filtered_data[:3]
    
    def compress_structured_context(self, context: StructuredContext) -> StructuredContext:
        """压缩结构化上下文"""
        compressed_context = StructuredContext()
        
        # 开发者指令通常不压缩（重要性最高）
        compressed_context.developer_instructions = context.developer_instructions
        
        # 压缩对话历史
        compressed_context.conversation_history = self.compress_conversation_history(
            context.conversation_history
        )
        
        # 用户输入不压缩
        compressed_context.user_input = context.user_input
        
        # 压缩工具结果
        compressed_context.tool_results = self.compress_tool_results(context.tool_results)
        
        # 压缩外部数据
        compressed_context.external_data = self.compress_external_data(context.external_data)
        
        # 压缩系统消息
        compressed_system_messages = []
        for msg in context.system_messages:
            compressed_system_messages.append(self.compress_text(msg, 0.7))
        compressed_context.system_messages = compressed_system_messages
        
        # 复制元数据并添加压缩信息
        compressed_context.metadata = context.metadata.copy()
        compressed_context.metadata.update({
            'compressed': True,
            'original_conversation_count': len(context.conversation_history),
            'compressed_conversation_count': len(compressed_context.conversation_history),
            'original_tool_results_count': len(context.tool_results),
            'compressed_tool_results_count': len(compressed_context.tool_results),
            'original_external_data_count': len(context.external_data),
            'compressed_external_data_count': len(compressed_context.external_data)
        })
        
        self.log_info("Context compressed", {
            'conversation_compression': f"{len(compressed_context.conversation_history)}/{len(context.conversation_history)}",
            'tool_results_compression': f"{len(compressed_context.tool_results)}/{len(context.tool_results)}",
            'external_data_compression': f"{len(compressed_context.external_data)}/{len(context.external_data)}"
        })
        
        return compressed_context
    
    def estimate_compression_ratio(self, original_context: StructuredContext, compressed_context: StructuredContext) -> float:
        """估算压缩比例"""
        def calculate_size(ctx):
            size = 0
            size += sum(len(instr) for instr in ctx.developer_instructions)
            size += sum(len(str(conv)) for conv in ctx.conversation_history)
            size += len(ctx.user_input)
            size += sum(len(str(result)) for result in ctx.tool_results)
            size += sum(len(str(data)) for data in ctx.external_data)
            size += sum(len(msg) for msg in ctx.system_messages)
            return size
        
        original_size = calculate_size(original_context)
        compressed_size = calculate_size(compressed_context)
        
        if original_size == 0:
            return 1.0
        
        return compressed_size / original_size
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')
            
            if action == 'compress_text':
                return self.compress_text(
                    input_data['text'],
                    input_data.get('target_ratio', self.compression_ratio)
                )
            
            elif action == 'compress_context':
                return self.compress_structured_context(input_data['context'])
            
            else:
                raise ValueError(f"Unknown action: {action}")
        
        else:
            raise ValueError("ContextCompressor requires dict input with 'action' field")
