"""
Agent ID统一管理器
解决Agent ID在不同层次使用不一致的问题
"""

import logging
from typing import Dict, Any, Tuple, Optional
from Item.Agentlib import Agent

class AgentIDManager:
    """Agent ID统一管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def normalize_participants(self, participants: Dict[str, Agent]) -> Dict[str, Agent]:
        """
        标准化participants字典，确保key与Agent的component_id一致
        
        Args:
            participants: 原始participants字典
            
        Returns:
            标准化后的participants字典
        """
        normalized = {}
        id_mapping = {}  # 记录ID映射关系
        
        for original_key, agent in participants.items():
            # 使用component_id作为标准key
            standard_key = agent.component_id
            normalized[standard_key] = agent
            
            if original_key != standard_key:
                id_mapping[original_key] = standard_key
                self.logger.info(f"ID标准化: '{original_key}' → '{standard_key}' (Agent: {agent.name})")
        
        if id_mapping:
            self.logger.info(f"完成Agent ID标准化: {len(id_mapping)} 个ID被修正")
        else:
            self.logger.debug("Agent ID已经标准化，无需修正")
            
        return normalized
    
    def validate_participants_consistency(self, participants: Dict[str, Agent]) -> bool:
        """
        验证participants字典的ID一致性
        
        Args:
            participants: 要验证的participants字典
            
        Returns:
            是否一致
        """
        inconsistencies = []
        
        for key, agent in participants.items():
            if key != agent.component_id:
                inconsistencies.append({
                    'key': key,
                    'component_id': agent.component_id,
                    'agent_name': agent.name
                })
        
        if inconsistencies:
            self.logger.warning(f"发现 {len(inconsistencies)} 个ID不一致:")
            for item in inconsistencies:
                self.logger.warning(f"  Key: '{item['key']}' ≠ component_id: '{item['component_id']}' (Agent: {item['agent_name']})")
            return False
        
        self.logger.debug(f"Participants ID一致性验证通过: {len(participants)} 个Agent")
        return True
    
    def get_agent_by_any_id(self, participants: Dict[str, Agent], target_id: str) -> Tuple[Optional[str], Optional[Agent]]:
        """
        通过任意ID查找Agent，返回标准化的key和Agent对象
        
        Args:
            participants: participants字典
            target_id: 要查找的ID
            
        Returns:
            (标准化的key, Agent对象) 或 (None, None)
        """
        # 方法1：直接匹配key
        if target_id in participants:
            agent = participants[target_id]
            return target_id, agent
        
        # 方法2：通过component_id匹配
        for key, agent in participants.items():
            if agent.component_id == target_id:
                return key, agent
        
        # 方法3：通过name匹配（最后的后备方案）
        for key, agent in participants.items():
            if agent.name == target_id:
                self.logger.warning(f"通过name匹配找到Agent: '{target_id}' → {agent.name}")
                return key, agent
        
        self.logger.error(f"无法找到ID为 '{target_id}' 的Agent")
        return None, None
    
    def diagnose_participants(self, participants: Dict[str, Agent]) -> Dict[str, Any]:
        """
        诊断participants字典的状态
        
        Args:
            participants: 要诊断的participants字典
            
        Returns:
            诊断结果字典
        """
        diagnosis = {
            'total_agents': len(participants),
            'consistent_ids': 0,
            'inconsistent_ids': 0,
            'inconsistencies': [],
            'agent_details': []
        }
        
        for key, agent in participants.items():
            agent_detail = {
                'key': key,
                'component_id': agent.component_id,
                'name': agent.name,
                'consistent': key == agent.component_id
            }
            
            if agent_detail['consistent']:
                diagnosis['consistent_ids'] += 1
            else:
                diagnosis['inconsistent_ids'] += 1
                diagnosis['inconsistencies'].append({
                    'key': key,
                    'component_id': agent.component_id,
                    'agent_name': agent.name
                })
            
            diagnosis['agent_details'].append(agent_detail)
        
        return diagnosis
    
    def log_diagnosis(self, participants: Dict[str, Agent]) -> None:
        """
        记录participants诊断信息
        
        Args:
            participants: 要诊断的participants字典
        """
        diagnosis = self.diagnose_participants(participants)
        
        self.logger.info(f"📊 Participants诊断报告:")
        self.logger.info(f"  总Agent数量: {diagnosis['total_agents']}")
        self.logger.info(f"  ID一致的Agent: {diagnosis['consistent_ids']}")
        self.logger.info(f"  ID不一致的Agent: {diagnosis['inconsistent_ids']}")
        
        if diagnosis['inconsistencies']:
            self.logger.warning(f"  ID不一致详情:")
            for item in diagnosis['inconsistencies']:
                self.logger.warning(f"    {item['agent_name']}: key='{item['key']}' ≠ component_id='{item['component_id']}'")
        
        if diagnosis['inconsistent_ids'] == 0:
            self.logger.info("  ✅ 所有Agent ID都是一致的")
        else:
            self.logger.warning(f"  ⚠️ 发现 {diagnosis['inconsistent_ids']} 个ID不一致的Agent")
