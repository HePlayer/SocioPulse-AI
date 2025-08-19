"""
SDK 请求模板模块化
- 为不同模型构造请求参数、工具配置、消息格式。
- 通过 Registry 按模型名选择模板，减少 if/elif 分支。
"""
from typing import Dict, Any, List
import re

class IRequestTemplate:
    def build(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

class ZhipuGLM45Template(IRequestTemplate):
    """glm-4.5 专用：严格 web_search，用户消息只保留最后一条，且保留【聊天室：】标签"""
    def build(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        # 取最后一条用户消息
        last_user = None
        for m in reversed(messages):
            if m.get('role') == 'user':
                last_user = m.get('content')
                break
        user_text = last_user or (messages[-1]['content'] if messages else '')
        # 保留聊天室标签
        room_tag = ''
        m_tag = re.search(r"^\s*(【聊天室：[^】]+】)", user_text)
        if m_tag:
            room_tag = m_tag.group(1)
        # 可选提要：若存在“当前讨论主题”，提取为简短问题
        m_topic = re.search(r"当前讨论主题[:：]\s*(.+)", user_text)
        if m_topic:
            topic_line = m_topic.group(1).strip().splitlines()[0]
            user_text = f"{room_tag}\n{topic_line}".strip() if room_tag else topic_line

        tools = [{
            "type": "web_search",
            "web_search": {
                "enable": "True",
                "search_engine": "search_pro",
                "search_result": "True",
                "count": "5"
            }
        }]
        return {
            'model': model_name,
            'messages': [{'role': 'user', 'content': user_text}],
            'tools': tools
        }

class ZhipuGLM4Template(IRequestTemplate):
    """glm-4 系列：tools 带 enable 布尔，tool_choice=auto，完整对话"""
    def build(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        params = {
            'model': model_name,
            'messages': messages,
            'tools': [{"type": "web_search", "web_search": {"enable": True}}],
            'tool_choice': 'auto'
        }
        # 透传常用采样参数
        for k in ['temperature', 'max_tokens', 'top_p']:
            if k in kwargs:
                params[k] = kwargs[k]
        return params

class OpenAICompatTemplate(IRequestTemplate):
    """OpenAI 兼容路径：与 glm-4 类似"""
    def build(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        params = {
            'model': model_name,
            'messages': messages,
            'tools': [{"type": "web_search", "web_search": {"enable": True}}],
            'tool_choice': 'auto'
        }
        for k in ['temperature', 'max_tokens', 'top_p']:
            if k in kwargs:
                params[k] = kwargs[k]
        return params

class RequestTemplateRegistry:
    _glm45 = ZhipuGLM45Template()
    _glm4 = ZhipuGLM4Template()
    _compat = OpenAICompatTemplate()

    @classmethod
    def get(cls, model_name: str) -> IRequestTemplate:
        if model_name.startswith('glm-4.5'):
            return cls._glm45
        if model_name.startswith('glm-4'):
            return cls._glm4
        return cls._compat

