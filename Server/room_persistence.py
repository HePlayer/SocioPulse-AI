"""
聊天室持久化存储模块
解决服务器重启后房间数据丢失的问题
"""

import json
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class RoomPersistence:
    """聊天室持久化管理器"""
    
    def __init__(self, storage_dir: str = "workspace/rooms"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 房间数据文件
        self.rooms_file = self.storage_dir / "rooms.json"
        self.room_metadata_file = self.storage_dir / "room_metadata.json"
        
        # 备份设置
        self.backup_interval = 300  # 5分钟备份一次
        self.max_backups = 10
        
        logger.info(f"Room persistence initialized: {self.storage_dir}")
    
    async def save_room_data(self, chat_rooms: Dict[str, Any]) -> bool:
        """保存房间数据到文件"""
        try:
            # 准备序列化数据
            serializable_rooms = {}
            room_metadata = {}
            
            for room_id, room in chat_rooms.items():
                try:
                    # 提取可序列化的房间信息
                    room_data = await self._extract_room_data(room_id, room)
                    if room_data:
                        serializable_rooms[room_id] = room_data['room_info']
                        room_metadata[room_id] = room_data['metadata']
                        
                except Exception as e:
                    logger.error(f"Failed to extract data for room {room_id}: {e}")
                    continue
            
            # 保存房间数据
            await self._save_json_file(self.rooms_file, {
                'rooms': serializable_rooms,
                'saved_at': datetime.now().isoformat(),
                'version': '1.0'
            })
            
            # 保存元数据
            await self._save_json_file(self.room_metadata_file, {
                'metadata': room_metadata,
                'saved_at': datetime.now().isoformat()
            })
            
            logger.info(f"Saved {len(serializable_rooms)} rooms to storage")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save room data: {e}")
            return False
    
    async def load_room_data(self) -> Dict[str, Any]:
        """从文件加载房间数据"""
        try:
            # 检查文件是否存在
            if not self.rooms_file.exists():
                logger.info("No room data file found, starting with empty rooms")
                return {}
            
            # 加载房间数据
            rooms_data = await self._load_json_file(self.rooms_file)
            metadata_data = await self._load_json_file(self.room_metadata_file)
            
            if not rooms_data or 'rooms' not in rooms_data:
                logger.warning("Invalid room data format")
                return {}
            
            rooms = rooms_data['rooms']
            metadata = metadata_data.get('metadata', {}) if metadata_data else {}
            
            # 验证数据完整性
            valid_rooms = {}
            for room_id, room_info in rooms.items():
                if self._validate_room_data(room_id, room_info):
                    # 合并元数据
                    room_info['metadata'] = metadata.get(room_id, {})
                    valid_rooms[room_id] = room_info
                else:
                    logger.warning(f"Invalid room data for {room_id}, skipping")
            
            logger.info(f"Loaded {len(valid_rooms)} valid rooms from storage")
            return valid_rooms
            
        except Exception as e:
            logger.error(f"Failed to load room data: {e}")
            return {}
    
    async def backup_room_data(self, chat_rooms: Dict[str, Any]) -> bool:
        """创建房间数据备份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.storage_dir / f"rooms_backup_{timestamp}.json"
            
            # 准备备份数据
            backup_data = {
                'backup_time': datetime.now().isoformat(),
                'room_count': len(chat_rooms),
                'rooms': {}
            }
            
            for room_id, room in chat_rooms.items():
                try:
                    room_data = await self._extract_room_data(room_id, room)
                    if room_data:
                        backup_data['rooms'][room_id] = room_data
                except Exception as e:
                    logger.error(f"Failed to backup room {room_id}: {e}")
            
            # 保存备份
            await self._save_json_file(backup_file, backup_data)
            
            # 清理旧备份
            await self._cleanup_old_backups()
            
            logger.info(f"Created backup: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    async def delete_room_data(self, room_id: str) -> bool:
        """删除特定房间的持久化数据"""
        try:
            # 加载现有数据
            rooms_data = await self._load_json_file(self.rooms_file)
            metadata_data = await self._load_json_file(self.room_metadata_file)
            
            if rooms_data and 'rooms' in rooms_data:
                rooms_data['rooms'].pop(room_id, None)
                await self._save_json_file(self.rooms_file, rooms_data)
            
            if metadata_data and 'metadata' in metadata_data:
                metadata_data['metadata'].pop(room_id, None)
                await self._save_json_file(self.room_metadata_file, metadata_data)
            
            logger.info(f"Deleted persistent data for room {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete room data for {room_id}: {e}")
            return False
    
    async def get_room_statistics(self) -> Dict[str, Any]:
        """获取房间存储统计信息"""
        try:
            stats = {
                'storage_dir': str(self.storage_dir),
                'files_exist': {
                    'rooms': self.rooms_file.exists(),
                    'metadata': self.room_metadata_file.exists()
                },
                'file_sizes': {},
                'room_count': 0,
                'last_saved': None,
                'backups_count': 0
            }
            
            # 文件大小
            if self.rooms_file.exists():
                stats['file_sizes']['rooms'] = self.rooms_file.stat().st_size
            if self.room_metadata_file.exists():
                stats['file_sizes']['metadata'] = self.room_metadata_file.stat().st_size
            
            # 房间数量和最后保存时间
            rooms_data = await self._load_json_file(self.rooms_file)
            if rooms_data:
                stats['room_count'] = len(rooms_data.get('rooms', {}))
                stats['last_saved'] = rooms_data.get('saved_at')
            
            # 备份文件数量
            backup_files = list(self.storage_dir.glob("rooms_backup_*.json"))
            stats['backups_count'] = len(backup_files)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get room statistics: {e}")
            return {}
    
    async def _extract_room_data(self, room_id: str, room: Any) -> Optional[Dict[str, Any]]:
        """提取房间的可序列化数据 - 增强版"""
        try:
            room_info = {
                'room_id': room_id,
                'created_at': datetime.now().isoformat(),
                'agents': [],
                'config': {},
                'message_count': 0,
                'room_type': 'single'  # 默认类型
            }
            
            metadata = {
                'last_accessed': datetime.now().isoformat(),
                'creation_method': 'extracted_from_memory',
                'extraction_version': '2.0'
            }
            
            # 多策略提取房间配置
            room_name = None
            
            # 策略1：ChatRoom对象方式
            if hasattr(room, 'get_room_status'):
                try:
                    room_status = room.get_room_status()
                    room_name = room_status.get('room_name')
                    room_info['config']['agent_count'] = room_status.get('agent_count', 0)
                    logger.info(f"Extraction Method 1 - Room status for {room_id}: name='{room_name}'")
                except Exception as e:
                    logger.warning(f"Extraction Method 1 failed for {room_id}: {e}")
            
            # 策略2：直接访问config属性
            if hasattr(room, 'config'):
                try:
                    if hasattr(room.config, 'room_name'):
                        room_name = room.config.room_name
                    if hasattr(room.config, 'description'):
                        room_info['config']['description'] = room.config.description
                    if hasattr(room.config, 'max_agents'):
                        room_info['config']['max_agents'] = room.config.max_agents
                    if hasattr(room.config, 'communication_mode'):
                        room_info['config']['communication_mode'] = str(room.config.communication_mode)
                    logger.info(f"Extraction Method 2 - Config access for {room_id}: name='{room_name}'")
                except Exception as e:
                    logger.warning(f"Extraction Method 2 failed for {room_id}: {e}")
            
            # 策略3：字典格式访问
            if isinstance(room, dict):
                try:
                    config = room.get('config', {})
                    room_name = config.get('room_name')
                    room_info['config'].update(config)
                    logger.info(f"Extraction Method 3 - Dict access for {room_id}: name='{room_name}'")
                except Exception as e:
                    logger.warning(f"Extraction Method 3 failed for {room_id}: {e}")
            
            # 确保房间名称
            if not room_name:
                room_name = f'Room_{room_id[:8]}'
                logger.info(f"Using fallback room name for {room_id}: '{room_name}'")
            
            room_info['config']['room_name'] = room_name
            
            # 增强的Agent信息提取
            agents_extracted = 0
            
            # 从ChatRoom对象提取Agent
            if hasattr(room, 'agents') and room.agents:
                for agent_id, agent in room.agents.items():
                    try:
                        agent_info = {
                            'agent_id': agent_id,
                            'name': getattr(agent, 'name', f'Agent_{agents_extracted + 1}'),
                            'role': str(getattr(agent, 'role', 'assistant'))
                        }
                        
                        # 增强的Agent元数据提取
                        if hasattr(agent, 'get_metadata'):
                            try:
                                agent_metadata = agent.get_metadata()
                                agent_info.update({
                                    'platform': agent_metadata.get('platform', 'unknown'),
                                    'model_name': agent_metadata.get('model_name', 'unknown'),
                                    'model': agent_metadata.get('model_name', 'unknown'),  # 兼容性
                                    'custom_prompt': agent_metadata.get('custom_prompt', ''),
                                    'prompt': agent_metadata.get('custom_prompt', ''),  # 兼容性
                                    'role_description': agent_metadata.get('role_description', '')
                                })
                            except Exception as e:
                                logger.warning(f"Failed to get metadata for agent {agent_id}: {e}")
                        
                        # 尝试从Agent对象直接获取属性
                        if hasattr(agent, 'platform'):
                            agent_info['platform'] = agent.platform
                        if hasattr(agent, 'model_name'):
                            agent_info['model_name'] = agent.model_name
                            agent_info['model'] = agent.model_name
                        if hasattr(agent, 'system_prompt'):
                            agent_info['custom_prompt'] = agent.system_prompt
                            agent_info['prompt'] = agent.system_prompt
                        
                        room_info['agents'].append(agent_info)
                        agents_extracted += 1
                        logger.info(f"Extracted agent {agent_info['name']} from room {room_id}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract agent data for {agent_id}: {e}")
            
            # 从字典格式提取Agent
            elif isinstance(room, dict) and 'agents' in room:
                try:
                    agents_data = room['agents']
                    if isinstance(agents_data, list):
                        for agent_data in agents_data:
                            if isinstance(agent_data, dict):
                                agent_info = {
                                    'agent_id': agent_data.get('agent_id', f'agent_{agents_extracted}'),
                                    'name': agent_data.get('name', f'Agent_{agents_extracted + 1}'),
                                    'role': agent_data.get('role', 'assistant'),
                                    'platform': agent_data.get('platform', 'unknown'),
                                    'model_name': agent_data.get('model_name') or agent_data.get('model', 'unknown'),
                                    'model': agent_data.get('model') or agent_data.get('model_name', 'unknown'),
                                    'custom_prompt': agent_data.get('custom_prompt') or agent_data.get('prompt', ''),
                                    'prompt': agent_data.get('prompt') or agent_data.get('custom_prompt', ''),
                                    'role_description': agent_data.get('role_description', '')
                                }
                                room_info['agents'].append(agent_info)
                                agents_extracted += 1
                                logger.info(f"Extracted agent {agent_info['name']} from dict format in room {room_id}")
                    elif isinstance(agents_data, dict):
                        for agent_id, agent_data in agents_data.items():
                            if isinstance(agent_data, dict):
                                agent_info = {
                                    'agent_id': agent_id,
                                    'name': agent_data.get('name', f'Agent_{agents_extracted + 1}'),
                                    'role': agent_data.get('role', 'assistant'),
                                    'platform': agent_data.get('platform', 'unknown'),
                                    'model_name': agent_data.get('model_name') or agent_data.get('model', 'unknown'),
                                    'model': agent_data.get('model') or agent_data.get('model_name', 'unknown'),
                                    'custom_prompt': agent_data.get('custom_prompt') or agent_data.get('prompt', ''),
                                    'prompt': agent_data.get('prompt') or agent_data.get('custom_prompt', ''),
                                    'role_description': agent_data.get('role_description', '')
                                }
                                room_info['agents'].append(agent_info)
                                agents_extracted += 1
                                logger.info(f"Extracted agent {agent_info['name']} from dict agents in room {room_id}")
                except Exception as e:
                    logger.warning(f"Failed to extract agents from dict format for {room_id}: {e}")
            
            # 确定房间类型
            room_info['room_type'] = 'group' if agents_extracted > 1 else 'single'
            
            # 提取消息历史统计
            message_count = 0
            try:
                if hasattr(room, 'message_history') and room.message_history:
                    message_count = len(room.message_history)
                elif isinstance(room, dict) and 'message_history' in room:
                    message_history = room['message_history']
                    if isinstance(message_history, list):
                        message_count = len(message_history)
                
                room_info['message_count'] = message_count
                metadata['has_message_history'] = message_count > 0
                
            except Exception as e:
                logger.warning(f"Failed to extract message history for {room_id}: {e}")
                metadata['has_message_history'] = False
            
            # 添加提取统计信息
            metadata['agents_extracted'] = agents_extracted
            metadata['extraction_success'] = agents_extracted > 0
            
            logger.info(f"✅ Room data extraction completed for {room_id}: {agents_extracted} agents, {message_count} messages")
            
            return {
                'room_info': room_info,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to extract room data for {room_id}: {e}")
            return None
    
    def _validate_room_data(self, room_id: str, room_data: Dict[str, Any]) -> bool:
        """验证房间数据的完整性"""
        try:
            # 基本字段检查
            required_fields = ['room_id', 'config', 'agents']
            for field in required_fields:
                if field not in room_data:
                    logger.warning(f"Missing required field '{field}' in room {room_id}")
                    return False
            
            # 配置检查
            config = room_data['config']
            if not isinstance(config, dict):
                logger.warning(f"Invalid config format in room {room_id}")
                return False
            
            # Agent列表检查
            agents = room_data['agents']
            if not isinstance(agents, list):
                logger.warning(f"Invalid agents format in room {room_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating room data for {room_id}: {e}")
            return False
    
    async def _save_json_file(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """异步保存JSON文件"""
        try:
            # 创建临时文件
            temp_file = file_path.with_suffix('.tmp')
            
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 原子性重命名
            temp_file.replace(file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save JSON file {file_path}: {e}")
            return False
    
    async def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """异步加载JSON文件"""
        try:
            if not file_path.exists():
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load JSON file {file_path}: {e}")
            return None
    
    async def _cleanup_old_backups(self):
        """清理过期的备份文件"""
        try:
            backup_files = sorted(
                self.storage_dir.glob("rooms_backup_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # 保留最新的备份文件
            for backup_file in backup_files[self.max_backups:]:
                backup_file.unlink()
                logger.info(f"Deleted old backup: {backup_file}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    async def start_auto_backup(self, chat_rooms: Dict[str, Any]):
        """启动自动备份任务"""
        async def backup_task():
            while True:
                try:
                    await asyncio.sleep(self.backup_interval)
                    await self.backup_room_data(chat_rooms)
                except Exception as e:
                    logger.error(f"Auto backup task error: {e}")
        
        # 启动后台任务
        asyncio.create_task(backup_task())
        logger.info(f"Auto backup started (interval: {self.backup_interval}s)")
