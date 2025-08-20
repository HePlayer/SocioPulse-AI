"""
mention_parser - 轻量@解析器
最小侵入实现：
- 支持格式@（@Name）
- 支持语义@（Name，你觉得/怎么看/如何/评价/...）
- 支持多Agent（顿号/逗号/空格分隔）
- 语义优先于格式：同名命中以语义类型覆盖格式类型

返回：
- List[Dict]: [{'agent_id': str, 'type': 'semantic'|'format'}]

注意：
- 保持简单启发式，避免复杂NLP依赖
- 不引入新依赖
"""
from typing import Dict, List, Tuple, Optional, Any
import re

MENTION_TYPE_FORMAT = 'format'
MENTION_TYPE_SEMANTIC = 'semantic'

import json
from Item.Agentlib import PromptManager
from models.models import ModelBase

# 简单的名字归一化（去空白）
def _norm(s: str) -> str:
    return (s or '').strip()

async def _semantic_detect(text: str, agents: Dict[str, any], model: ModelBase, prompt_mgr: PromptManager) -> List[Dict[str, str]]:
    agents_json = json.dumps([
        {'id': aid, 'name': getattr(ag, 'name', '')}
        for aid, ag in agents.items()
    ], ensure_ascii=False)
    template = prompt_mgr.get_template("semantic_mention_detection")
    prompt = template.format(user_text=text, agents_json=agents_json) if template else (
        f"请用语义判断消息应由谁回应，仅输出JSON：{{\"mentions\":[{{\"agent_id\":\"...\"}}]}}。\n消息：{text}\nAgents：{agents_json}"
    )
    resp = await model.generate(prompt, None, temperature=0.1, max_tokens=128)
    content = getattr(resp, 'content', resp)
    data = json.loads((content or '').strip())
    mentions = data.get('mentions', []) if isinstance(data, dict) else []
    return [{'agent_id': m.get('agent_id'), 'type': MENTION_TYPE_SEMANTIC}
            for m in mentions if isinstance(m, dict) and m.get('agent_id')]

# 获取默认模型/提示词管理器：根据你们项目的实际全局单例/工厂实现替换
_default_prompt_mgr: Optional[PromptManager] = None
_default_detection_model: Optional[ModelBase] = None

def set_default_prompt_manager(pm: PromptManager) -> None:
    global _default_prompt_mgr
    _default_prompt_mgr = pm

def set_default_detection_model(m: ModelBase) -> None:
    global _default_detection_model
    _default_detection_model = m

async def parse_mentions(text: str, agents: Dict[str, any],
                         model: Optional[ModelBase] = None,
                         prompt_mgr: Optional[PromptManager] = None) -> List[Dict[str, str]]:
    """
    纯语义@识别：调用LLM判断应由谁优先回应，仅返回semantic类型。
    失败时返回空列表，不使用关键词或格式@回退。
    """
    if not text or not agents:
        return []
    model = model or _default_detection_model
    prompt_mgr = prompt_mgr or _default_prompt_mgr or PromptManager()
    if not model:
        # 无可用模型则不做任何触发
        return []
    try:
        return await _semantic_detect(text, agents, model, prompt_mgr)
    except Exception:
        return []

