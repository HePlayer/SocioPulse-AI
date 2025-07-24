"""
服务器配置常量
"""

import os
import yaml

# 默认服务器配置
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 8000

def load_config():
    """从config.yaml加载配置"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print("Warning: config.yaml not found, using defaults")
        return {}
    except Exception as e:
        print(f"Warning: Error loading config.yaml: {e}, using defaults")
        return {}

# 加载配置
_config = load_config()

# 获取服务器配置，优先级：环境变量 > config.yaml > 默认值
_server_config = _config.get('server', {})
HOST = os.getenv('MULTIAI_HOST', _server_config.get('host', DEFAULT_HOST))
PORT = int(os.getenv('MULTIAI_PORT', _server_config.get('port', DEFAULT_PORT)))

# 平台配置
PLATFORM_DISPLAY_NAMES = {
    'openai': 'OpenAI',
    'aihubmix': 'AiHubMix',
    'zhipu': '智谱AI'
}

MODEL_DISPLAY_NAMES = {
    'gpt-4': 'GPT-4',
    'gpt-4-turbo': 'GPT-4 Turbo',
    'gpt-3.5-turbo': 'GPT-3.5 Turbo',
    'gpt-4o-mini': 'GPT-4o Mini',
    'gpt-4o-search-preview': 'GPT-4o Search Preview',
    'gpt-4o-mini-search-preview': 'GPT-4o Mini Search Preview',
    'glm-4': 'GLM-4',
    'glm-4-plus': 'GLM-4 Plus',
    'glm-3-turbo': 'GLM-3 Turbo',
    'glm-4-flash-250414': 'GLM-4 Flash'
}

# 模型类型配置（免费/收费）
MODEL_TYPES = {
    # OpenAI 模型（收费）
    'gpt-4': 'paid',
    'gpt-4-turbo': 'paid',
    'gpt-3.5-turbo': 'paid',
    
    # AiHubMix 模型（收费）
    'gpt-4o-mini': 'paid',
    'gpt-4o-search-preview': 'paid',
    'gpt-4o-mini-search-preview': 'paid',
    
    # 智谱AI 模型
    'glm-4': 'paid',
    'glm-4-plus': 'paid',
    'glm-3-turbo': 'free',  # 免费模型
    'glm-4-flash-250414': 'free'  # 免费模型
}

# 默认模型配置（优先使用免费模型）
DEFAULT_MODELS = {
    'openai': 'gpt-3.5-turbo',  # OpenAI最便宜的模型
    'aihubmix': 'gpt-4o-mini',
    'zhipu': 'glm-4-flash-250414'  # 智谱AI免费模型
}

# 默认系统设置（优先使用config.yaml中的配置）
DEFAULT_SETTINGS = {
    'models': {
        'default_platform': _config.get('models', {}).get('default_platform', 'zhipu'),  # 优先使用智谱AI（有免费模型）
        'platforms': {
            'openai': {
                'api_key': '',
                'api_base': 'https://api.openai.com/v1',
                'enabled_models': ['gpt-3.5-turbo', 'gpt-4'],  # 添加更多选择
                'default_model': 'gpt-3.5-turbo'
            },
            'aihubmix': {
                'api_key': '',
                'api_base': 'https://aihubmix.com/v1',
                'enabled_models': ['gpt-4o-mini'],
                'default_model': 'gpt-4o-mini'
            },
            'zhipu': {
                'api_key': '',
                'api_base': 'https://open.bigmodel.cn/api/paas/v4',
                'enabled_models': ['glm-4-flash-250414', 'glm-3-turbo', 'glm-4'],  # 免费模型优先
                'default_model': 'glm-4-flash-250414'  # 使用免费模型作为默认
            }
        }
    },
    'features': {
        'proactive_chat': {
            'enabled': True,
            'monitoring_interval': 5,
            'confidence_threshold': 0.8,
            'max_suggestions_per_hour': 3
        }
    }
}

# 默认可用模型列表
DEFAULT_AVAILABLE_MODELS = [
    {
        'value': 'openai:gpt-4',
        'label': 'OpenAI - GPT-4',
        'platform': 'openai',
        'model': 'gpt-4',
        'is_default': True
    },
    {
        'value': 'aihubmix:gpt-4o-mini',
        'label': 'AiHubMix - GPT-4o Mini',
        'platform': 'aihubmix',
        'model': 'gpt-4o-mini',
        'is_default': False
    },
    {
        'value': 'zhipu:glm-4',
        'label': '智谱AI - GLM-4',
        'platform': 'zhipu',
        'model': 'glm-4',
        'is_default': False
    }
]

# 文件路径
CONFIG_FILE_PATH = 'config.yaml'
INDEX_FILE_PATH = 'MultiAI.html'

# WebSocket消息类型
WS_MESSAGE_TYPES = {
    'CONNECTION': 'connection',
    'JOIN_ROOM': 'join_room',
    'SEND_MESSAGE': 'send_message',
    'MESSAGE_SENT': 'message_sent',
    'GET_ROOMS': 'get_rooms',
    'CREATE_ROOM': 'create_room',
    'DELETE_ROOM': 'delete_room',
    'ROOM_JOINED': 'room_joined',
    'ROOM_CREATED': 'room_created',
    'ROOM_DELETED': 'room_deleted',
    'NEW_MESSAGE': 'new_message',
    'ROOMS_LIST': 'rooms_list',
    'GET_ROOM_HISTORY': 'get_room_history',
    'ROOM_HISTORY': 'room_history',
    'ERROR': 'error'
}

# HTTP状态码
HTTP_STATUS = {
    'OK': 200,
    'BAD_REQUEST': 400,
    'NOT_FOUND': 404,
    'INTERNAL_SERVER_ERROR': 500
}

# 房间类型
ROOM_TYPES = {
    'SINGLE': 'single',
    'GROUP': 'group'
}

# 通信模式
COMMUNICATION_MODES = {
    'DIRECT': 'direct',
    'NETWORK': 'network'
}
