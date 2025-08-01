"""
Scratchpad - 便笺系统
用于存储当前会话的临时信息，会话结束后清除
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..FlowTools.base_component import BaseComponent


@dataclass
class ScratchpadEntry:
    """便笺条目"""
    content: str
    entry_type: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance_score: float = 1.0
    tags: List[str] = field(default_factory=list)


class Scratchpad(BaseComponent):
    """便笺系统 - 管理当前会话的临时信息"""
    
    def __init__(self, scratchpad_id: str = "default_scratchpad"):
        super().__init__(scratchpad_id, "scratchpad")
        
        # 存储条目
        self.entries: List[ScratchpadEntry] = []
        
        # 配置
        self.max_entries = 100  # 最大条目数
        self.auto_cleanup = True  # 自动清理旧条目
        
        self.log_debug("Scratchpad initialized", {
            'max_entries': self.max_entries,
            'auto_cleanup': self.auto_cleanup
        })
    
    def add_entry(self, 
                 content: str,
                 entry_type: str,
                 metadata: Dict[str, Any] = None,
                 importance_score: float = 1.0,
                 tags: List[str] = None) -> str:
        """添加便笺条目"""
        entry = ScratchpadEntry(
            content=content,
            entry_type=entry_type,
            timestamp=time.time(),
            metadata=metadata or {},
            importance_score=importance_score,
            tags=tags or []
        )
        
        self.entries.append(entry)
        
        # 自动清理
        if self.auto_cleanup and len(self.entries) > self.max_entries:
            self._cleanup_old_entries()
        
        entry_id = f"entry_{len(self.entries)}_{int(entry.timestamp)}"
        
        self.log_debug(f"Added scratchpad entry: {entry_type}", {
            'entry_id': entry_id,
            'content_length': len(content),
            'importance_score': importance_score,
            'tags': tags
        })
        
        return entry_id
    
    def get_entries_by_type(self, entry_type: str) -> List[Dict[str, Any]]:
        """根据类型获取条目"""
        matching_entries = []
        
        for entry in self.entries:
            if entry.entry_type == entry_type:
                matching_entries.append({
                    'content': entry.content,
                    'entry_type': entry.entry_type,
                    'timestamp': entry.timestamp,
                    'metadata': entry.metadata,
                    'importance_score': entry.importance_score,
                    'tags': entry.tags
                })
        
        return matching_entries
    
    def get_entries_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """根据标签获取条目"""
        matching_entries = []
        
        for entry in self.entries:
            if tag in entry.tags:
                matching_entries.append({
                    'content': entry.content,
                    'entry_type': entry.entry_type,
                    'timestamp': entry.timestamp,
                    'metadata': entry.metadata,
                    'importance_score': entry.importance_score,
                    'tags': entry.tags
                })
        
        return matching_entries
    
    def get_recent_entries(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的条目"""
        # 按时间戳排序，取最近的条目
        sorted_entries = sorted(self.entries, key=lambda x: x.timestamp, reverse=True)
        
        recent_entries = []
        for entry in sorted_entries[:count]:
            recent_entries.append({
                'content': entry.content,
                'entry_type': entry.entry_type,
                'timestamp': entry.timestamp,
                'metadata': entry.metadata,
                'importance_score': entry.importance_score,
                'tags': entry.tags
            })
        
        return recent_entries
    
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """获取所有条目"""
        all_entries = []
        
        for entry in self.entries:
            all_entries.append({
                'content': entry.content,
                'entry_type': entry.entry_type,
                'timestamp': entry.timestamp,
                'metadata': entry.metadata,
                'importance_score': entry.importance_score,
                'tags': entry.tags
            })
        
        return all_entries
    
    def search_entries(self, query: str, search_in_content: bool = True, search_in_metadata: bool = False) -> List[Dict[str, Any]]:
        """搜索条目"""
        matching_entries = []
        query_lower = query.lower()
        
        for entry in self.entries:
            match_found = False
            
            # 在内容中搜索
            if search_in_content and query_lower in entry.content.lower():
                match_found = True
            
            # 在元数据中搜索
            if search_in_metadata and not match_found:
                metadata_str = str(entry.metadata).lower()
                if query_lower in metadata_str:
                    match_found = True
            
            if match_found:
                matching_entries.append({
                    'content': entry.content,
                    'entry_type': entry.entry_type,
                    'timestamp': entry.timestamp,
                    'metadata': entry.metadata,
                    'importance_score': entry.importance_score,
                    'tags': entry.tags
                })
        
        return matching_entries
    
    def filter_entries(self, 
                      entry_types: List[str] = None,
                      tags: List[str] = None,
                      min_importance: float = None,
                      time_range: tuple = None) -> List[Dict[str, Any]]:
        """过滤条目"""
        filtered_entries = []
        
        for entry in self.entries:
            # 检查类型过滤
            if entry_types and entry.entry_type not in entry_types:
                continue
            
            # 检查标签过滤
            if tags and not any(tag in entry.tags for tag in tags):
                continue
            
            # 检查重要性过滤
            if min_importance is not None and entry.importance_score < min_importance:
                continue
            
            # 检查时间范围过滤
            if time_range:
                start_time, end_time = time_range
                if entry.timestamp < start_time or entry.timestamp > end_time:
                    continue
            
            filtered_entries.append({
                'content': entry.content,
                'entry_type': entry.entry_type,
                'timestamp': entry.timestamp,
                'metadata': entry.metadata,
                'importance_score': entry.importance_score,
                'tags': entry.tags
            })
        
        return filtered_entries
    
    def update_entry_metadata(self, entry_index: int, new_metadata: Dict[str, Any]) -> bool:
        """更新条目元数据"""
        if 0 <= entry_index < len(self.entries):
            self.entries[entry_index].metadata.update(new_metadata)
            self.log_debug(f"Updated metadata for entry {entry_index}")
            return True
        else:
            self.log_warning(f"Invalid entry index: {entry_index}")
            return False
    
    def add_tag_to_entry(self, entry_index: int, tag: str) -> bool:
        """为条目添加标签"""
        if 0 <= entry_index < len(self.entries):
            if tag not in self.entries[entry_index].tags:
                self.entries[entry_index].tags.append(tag)
                self.log_debug(f"Added tag '{tag}' to entry {entry_index}")
            return True
        else:
            self.log_warning(f"Invalid entry index: {entry_index}")
            return False
    
    def remove_entry(self, entry_index: int) -> bool:
        """删除条目"""
        if 0 <= entry_index < len(self.entries):
            removed_entry = self.entries.pop(entry_index)
            self.log_debug(f"Removed entry {entry_index}", {
                'entry_type': removed_entry.entry_type,
                'content_length': len(removed_entry.content)
            })
            return True
        else:
            self.log_warning(f"Invalid entry index: {entry_index}")
            return False
    
    def clear(self) -> None:
        """清空所有条目"""
        entries_count = len(self.entries)
        self.entries.clear()
        
        self.log_info(f"Cleared scratchpad", {
            'entries_removed': entries_count
        })
    
    def _cleanup_old_entries(self) -> None:
        """清理旧条目（保留重要的条目）"""
        if len(self.entries) <= self.max_entries:
            return
        
        # 按重要性和时间排序
        sorted_entries = sorted(
            self.entries,
            key=lambda x: (x.importance_score, x.timestamp),
            reverse=True
        )
        
        # 保留最重要和最新的条目
        entries_to_keep = sorted_entries[:self.max_entries]
        entries_removed = len(self.entries) - len(entries_to_keep)
        
        self.entries = entries_to_keep
        
        self.log_debug(f"Cleaned up old entries", {
            'entries_removed': entries_removed,
            'entries_remaining': len(self.entries)
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取便笺统计信息"""
        if not self.entries:
            return {
                'total_entries': 0,
                'entry_types': {},
                'total_content_length': 0,
                'average_importance': 0.0,
                'time_range': None
            }
        
        # 统计条目类型
        entry_types = {}
        total_content_length = 0
        total_importance = 0
        
        timestamps = []
        
        for entry in self.entries:
            entry_types[entry.entry_type] = entry_types.get(entry.entry_type, 0) + 1
            total_content_length += len(entry.content)
            total_importance += entry.importance_score
            timestamps.append(entry.timestamp)
        
        return {
            'total_entries': len(self.entries),
            'entry_types': entry_types,
            'total_content_length': total_content_length,
            'average_content_length': total_content_length / len(self.entries),
            'average_importance': total_importance / len(self.entries),
            'time_range': {
                'earliest': min(timestamps),
                'latest': max(timestamps),
                'span_hours': (max(timestamps) - min(timestamps)) / 3600
            } if timestamps else None
        }
    
    def export_data(self) -> Dict[str, Any]:
        """导出便笺数据"""
        return {
            'entries': [
                {
                    'content': entry.content,
                    'entry_type': entry.entry_type,
                    'timestamp': entry.timestamp,
                    'metadata': entry.metadata,
                    'importance_score': entry.importance_score,
                    'tags': entry.tags
                }
                for entry in self.entries
            ],
            'configuration': {
                'max_entries': self.max_entries,
                'auto_cleanup': self.auto_cleanup
            },
            'statistics': self.get_statistics()
        }
    
    def import_data(self, data: Dict[str, Any]) -> None:
        """导入便笺数据"""
        if 'entries' in data:
            self.entries.clear()
            
            for entry_data in data['entries']:
                entry = ScratchpadEntry(
                    content=entry_data['content'],
                    entry_type=entry_data['entry_type'],
                    timestamp=entry_data['timestamp'],
                    metadata=entry_data.get('metadata', {}),
                    importance_score=entry_data.get('importance_score', 1.0),
                    tags=entry_data.get('tags', [])
                )
                self.entries.append(entry)
        
        if 'configuration' in data:
            config = data['configuration']
            self.max_entries = config.get('max_entries', self.max_entries)
            self.auto_cleanup = config.get('auto_cleanup', self.auto_cleanup)
        
        self.log_info(f"Imported scratchpad data", {
            'entries_imported': len(self.entries)
        })
    
    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')
            
            if action == 'add_entry':
                return self.add_entry(
                    input_data['content'],
                    input_data['entry_type'],
                    input_data.get('metadata'),
                    input_data.get('importance_score', 1.0),
                    input_data.get('tags')
                )
            
            elif action == 'get_entries_by_type':
                return self.get_entries_by_type(input_data['entry_type'])
            
            elif action == 'search_entries':
                return self.search_entries(
                    input_data['query'],
                    input_data.get('search_in_content', True),
                    input_data.get('search_in_metadata', False)
                )
            
            elif action == 'get_statistics':
                return self.get_statistics()
            
            elif action == 'clear':
                self.clear()
                return {'status': 'success'}
            
            else:
                raise ValueError(f"Unknown action: {action}")
        
        else:
            raise ValueError("Scratchpad requires dict input with 'action' field")
