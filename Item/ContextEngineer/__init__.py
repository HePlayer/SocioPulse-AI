"""
ContextEngineer - 上下文工程模块
提供完整的上下文管理、记忆系统和检索功能

核心功能：
1. 上下文处理 - 根据5个部分组织结构化语言
2. 上下文分类 - 便笺、记忆、当前上下文三个存储类别
3. 上下文选择 - 基于HNSW算法的检索模块
4. 上下文压缩 - COCOM方法压缩，字数达到95%时自动压缩
5. 流程控制集成 - 可接入流程控制工具
"""

# 核心数据类型
from .context_types import (
    StructuredContext, 
    Memory, 
    MemoryType, 
    ScratchpadEntry, 
    CurrentContext
)

# 主要组件
from .context_manager import ContextManager
from .memory_system import MemorySystem
from .retrieval_engine import RetrievalEngine
from .scratchpad import Scratchpad
from .context_compressor import ContextCompressor

# HNSW检索核心
from .hnsw_index import HNSWIndex
from .hnsw_node import HNSWNode, HNSWStats, SearchCandidate
from .distance_metrics import DistanceType, DistanceMetrics, OptimizedDistanceCalculator
from .hnsw_utils import HNSWUtils

__version__ = "1.0.0"

__all__ = [
    # 核心数据类型
    'StructuredContext',
    'Memory',
    'MemoryType', 
    'ScratchpadEntry',
    'CurrentContext',
    
    # 主要组件
    'ContextManager',
    'MemorySystem', 
    'RetrievalEngine',
    'Scratchpad',
    'ContextCompressor',
    
    # HNSW检索系统
    'HNSWIndex',
    'HNSWNode',
    'HNSWStats',
    'SearchCandidate',
    'DistanceType',
    'DistanceMetrics',
    'OptimizedDistanceCalculator',
    'HNSWUtils'
]
