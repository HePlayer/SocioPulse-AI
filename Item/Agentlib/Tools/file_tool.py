"""
FileTool - 文件操作工具
提供基本的文件读写功能
"""

import os
import json
from typing import Dict, Any, List
from pathlib import Path

from .base_tool import BaseTool, ToolResult


class FileTool(BaseTool):
    """文件操作工具 - 读写文件"""
    
    def __init__(self, tool_id: str = "file_tool", workspace_dir: str = "./workspace"):
        super().__init__(
            tool_id,
            "file_tool",
            "执行文件操作，包括读取、写入、列出文件等"
        )
        
        # 设置工作空间目录（安全限制）
        self.workspace_dir = Path(workspace_dir).resolve()
        self.workspace_dir.mkdir(exist_ok=True)
    
    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "action": {
                "type": "string",
                "description": "要执行的操作：read, write, list, delete, exists",
                "required": True
            },
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作空间）",
                "required": False
            },
            "content": {
                "type": "string",
                "description": "要写入的内容（write操作需要）",
                "required": False
            },
            "encoding": {
                "type": "string",
                "description": "文件编码",
                "required": False,
                "default": "utf-8"
            }
        }
    
    async def _execute_tool(self, action: str, path: str = "", content: str = "", encoding: str = "utf-8") -> ToolResult:
        """执行文件操作"""
        try:
            # 验证并规范化路径
            if path:
                file_path = self._validate_path(path)
            else:
                file_path = self.workspace_dir
            
            # 根据操作类型执行
            if action == "read":
                return await self._read_file(file_path, encoding)
            elif action == "write":
                return await self._write_file(file_path, content, encoding)
            elif action == "list":
                return await self._list_files(file_path)
            elif action == "delete":
                return await self._delete_file(file_path)
            elif action == "exists":
                return await self._check_exists(file_path)
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"不支持的操作: {action}"
                )
                
        except PermissionError:
            return ToolResult(
                success=False,
                data=None,
                error="权限错误：无法访问指定的文件或目录"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"文件操作错误：{str(e)}"
            )
    
    def _validate_path(self, path: str) -> Path:
        """验证路径安全性"""
        # 转换为Path对象并规范化
        target_path = (self.workspace_dir / path).resolve()
        
        # 确保路径在工作空间内
        if not str(target_path).startswith(str(self.workspace_dir)):
            raise ValueError(f"路径超出工作空间范围: {path}")
        
        return target_path
    
    async def _read_file(self, file_path: Path, encoding: str) -> ToolResult:
        """读取文件"""
        if not file_path.exists():
            return ToolResult(
                success=False,
                data=None,
                error=f"文件不存在: {file_path.name}"
            )
        
        if not file_path.is_file():
            return ToolResult(
                success=False,
                data=None,
                error=f"不是文件: {file_path.name}"
            )
        
        try:
            content = file_path.read_text(encoding=encoding)
            return ToolResult(
                success=True,
                data={
                    "path": str(file_path.relative_to(self.workspace_dir)),
                    "content": content,
                    "size": len(content),
                    "encoding": encoding
                }
            )
        except UnicodeDecodeError:
            # 尝试读取为二进制
            content = file_path.read_bytes()
            return ToolResult(
                success=True,
                data={
                    "path": str(file_path.relative_to(self.workspace_dir)),
                    "content": f"[二进制文件，大小: {len(content)} 字节]",
                    "size": len(content),
                    "is_binary": True
                }
            )
    
    async def _write_file(self, file_path: Path, content: str, encoding: str) -> ToolResult:
        """写入文件"""
        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        file_path.write_text(content, encoding=encoding)
        
        return ToolResult(
            success=True,
            data={
                "path": str(file_path.relative_to(self.workspace_dir)),
                "size": len(content),
                "encoding": encoding
            }
        )
    
    async def _list_files(self, dir_path: Path) -> ToolResult:
        """列出目录内容"""
        if not dir_path.exists():
            return ToolResult(
                success=False,
                data=None,
                error=f"目录不存在: {dir_path.name}"
            )
        
        if not dir_path.is_dir():
            return ToolResult(
                success=False,
                data=None,
                error=f"不是目录: {dir_path.name}"
            )
        
        files = []
        for item in dir_path.iterdir():
            relative_path = item.relative_to(self.workspace_dir)
            files.append({
                "name": item.name,
                "path": str(relative_path),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })
        
        return ToolResult(
            success=True,
            data={
                "path": str(dir_path.relative_to(self.workspace_dir)),
                "files": files,
                "count": len(files)
            }
        )
    
    async def _delete_file(self, file_path: Path) -> ToolResult:
        """删除文件"""
        if not file_path.exists():
            return ToolResult(
                success=False,
                data=None,
                error=f"文件不存在: {file_path.name}"
            )
        
        if file_path.is_file():
            file_path.unlink()
        else:
            # 如果是目录，使用rmdir（只能删除空目录）
            try:
                file_path.rmdir()
            except OSError:
                return ToolResult(
                    success=False,
                    data=None,
                    error="目录不为空，无法删除"
                )
        
        return ToolResult(
            success=True,
            data={
                "path": str(file_path.relative_to(self.workspace_dir)),
                "deleted": True
            }
        )
    
    async def _check_exists(self, file_path: Path) -> ToolResult:
        """检查文件是否存在"""
        exists = file_path.exists()
        file_type = None
        
        if exists:
            if file_path.is_file():
                file_type = "file"
            elif file_path.is_dir():
                file_type = "directory"
            else:
                file_type = "other"
        
        return ToolResult(
            success=True,
            data={
                "path": str(file_path.relative_to(self.workspace_dir)),
                "exists": exists,
                "type": file_type
            }
        )
    
    def get_usage_example(self) -> str:
        """获取使用示例"""
        examples = [
            "file_tool(action='read', path='example.txt')",
            "file_tool(action='write', path='output.txt', content='Hello, World!')",
            "file_tool(action='list', path='.')",
            "file_tool(action='exists', path='config.json')",
            "file_tool(action='delete', path='temp.txt')"
        ]
        return "\n".join(examples)
