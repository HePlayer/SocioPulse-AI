"""
服务器工具函数
"""

from typing import Dict, Tuple
from .config import PLATFORM_DISPLAY_NAMES, MODEL_DISPLAY_NAMES, DEFAULT_MODELS, MODEL_TYPES


def parse_model_type(model_type_str: str) -> Tuple[str, str]:
    """
    解析模型类型字符串
    
    Args:
        model_type_str: 格式为 "platform:model" 或 "platform"
        
    Returns:
        (platform, model_name) 元组
    """
    if ':' in model_type_str:
        platform, model_name = model_type_str.split(':', 1)
        return platform.strip(), model_name.strip()
    else:
        # 如果没有指定模型，使用默认模型
        platform = model_type_str.strip()
        return platform, DEFAULT_MODELS.get(platform, 'gpt-3.5-turbo')


def is_room_name_unique(room_name: str, chat_rooms: Dict) -> bool:
    """检查房间名称是否唯一"""
    return not any(
        room.config.room_name == room_name 
        for room in chat_rooms.values()
    )


def suggest_unique_room_name(base_name: str, chat_rooms: Dict) -> str:
    """生成唯一的房间名称"""
    if is_room_name_unique(base_name, chat_rooms):
        return base_name
    
    counter = 1
    while True:
        suggested_name = f"{base_name} ({counter})"
        if is_room_name_unique(suggested_name, chat_rooms):
            return suggested_name
        counter += 1


def get_platform_display_name(platform: str) -> str:
    """获取平台显示名称"""
    return PLATFORM_DISPLAY_NAMES.get(platform, platform)


def get_model_display_name(model: str) -> str:
    """获取模型显示名称"""
    return MODEL_DISPLAY_NAMES.get(model, model)


def validate_agent_config(agent_config: dict, index: int) -> dict:
    """
    验证并处理Agent配置
    
    Args:
        agent_config: Agent配置字典
        index: Agent索引
        
    Returns:
        验证后的Agent配置
        
    Raises:
        Exception: 配置验证失败
    """
    agent_name = agent_config.get('name', f'Agent{index+1}')
    # 统一使用CHAT角色，具体专业化通过自定义Prompt实现
    agent_role = 'chat'
    
    # 优先使用platform和model字段（前端发送的格式）
    if 'platform' in agent_config and 'model' in agent_config:
        platform = agent_config['platform']
        model_name = agent_config['model']
        model_type_str = f"{platform}:{model_name}"
    elif 'platform' in agent_config and 'model_name' in agent_config:
        platform = agent_config['platform']
        model_name = agent_config['model_name']
        model_type_str = f"{platform}:{model_name}"
    else:
        # 兼容旧格式
        model_type_str = agent_config.get('model_type', 'openai:gpt-4')
        
        # 解析模型类型
        try:
            platform, model_name = parse_model_type(model_type_str)
        except Exception as e:
            raise Exception(f'Agent "{agent_name}" 的模型类型格式无效: {model_type_str}')
    
    return {
        'name': agent_name,
        'role': agent_role,
        'prompt': agent_config.get('prompt', ''),
        'platform': platform,
        'model_name': model_name,
        'model_type_str': model_type_str
    }


def format_room_info(room_id: str, room) -> dict:
    """
    格式化房间信息
    
    Args:
        room_id: 房间ID
        room: 房间对象
        
    Returns:
        格式化的房间信息字典
    """
    status = room.get_room_status()
    return {
        'room_id': room_id,
        'room_name': status['room_name'],
        'description': status['description'],
        'agent_count': status['agent_count'],
        'message_count': status['message_count'],
        'communication_mode': status['communication_mode']
    }


def build_model_option(platform_name: str, platform_config: dict, model_name: str) -> dict:
    """
    构建模型选项
    
    Args:
        platform_name: 平台名称
        platform_config: 平台配置
        model_name: 模型名称
        
    Returns:
        模型选项字典
    """
    model_type = MODEL_TYPES.get(model_name, 'paid')  # 默认为收费模型
    type_label = '免费' if model_type == 'free' else '收费'
    
    return {
        'value': f"{platform_name}:{model_name}",
        'label': f"{get_platform_display_name(platform_name)} - {get_model_display_name(model_name)} ({type_label})",
        'platform': platform_name,
        'model': model_name,
        'model_type': model_type,
        'is_free': model_type == 'free',
        'is_default': model_name == platform_config.get('default_model')
    }


def create_error_response(error_message: str, error_type: str = None) -> dict:
    """
    创建错误响应
    
    Args:
        error_message: 错误消息
        error_type: 错误类型
        
    Returns:
        错误响应字典
    """
    response = {
        'success': False,
        'error': error_message,
        'message': error_message
    }
    
    if error_type:
        response['error_type'] = error_type
        
    return response


def create_success_response(message: str = None, **kwargs) -> dict:
    """
    创建成功响应
    
    Args:
        message: 成功消息
        **kwargs: 其他响应字段
        
    Returns:
        成功响应字典
    """
    response = {
        'success': True
    }
    
    if message:
        response['message'] = message
        
    response.update(kwargs)
    return response
