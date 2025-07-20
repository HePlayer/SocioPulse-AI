"""
Context Types - 上下文相关的数据类型定义
避免循环导入的独立类型定义文件
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class StructuredContext:
    """结构化上下文"""
    user_input: str = ""
    developer_instructions: List[str] = field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    external_data: List[Dict[str, Any]] = field(default_factory=list)
    system_messages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'user_input': self.user_input,
            'developer_instructions': self.developer_instructions,
            'conversation_history': self.conversation_history,
            'tool_results': self.tool_results,
            'external_data': self.external_data,
            'system_messages': self.system_messages,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuredContext':
        """从字典创建实例"""
        return cls(
            user_input=data.get('user_input', ''),
            developer_instructions=data.get('developer_instructions', []),
            conversation_history=data.get('conversation_history', []),
            tool_results=data.get('tool_results', []),
            external_data=data.get('external_data', []),
            system_messages=data.get('system_messages', []),
            metadata=data.get('metadata', {})
        )
