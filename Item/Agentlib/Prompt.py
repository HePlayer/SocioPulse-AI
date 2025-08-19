"""
Prompt - 提示词管理模块
管理和组织各种Agent的提示词模板
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from string import Template

from ..FlowTools.base_component import BaseComponent
from ..ContextEngineer.context_manager import StructuredContext


@dataclass
class PromptTemplate:
    """提示词模板"""
    name: str
    template: str
    description: str = ""
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def format(self, **kwargs) -> str:
        """格式化模板"""
        # 使用Template进行安全的字符串替换
        template_obj = Template(self.template)
        return template_obj.safe_substitute(**kwargs)


class PromptManager(BaseComponent):
    """提示词管理器"""

    def __init__(self, manager_id: str = "prompt_manager"):
        super().__init__(manager_id, "prompt_manager")

        # 存储提示词模板
        self.templates: Dict[str, PromptTemplate] = {}

        # 初始化默认模板
        self._init_default_templates()

        self.log_debug("PromptManager initialized", {
            'template_count': len(self.templates)
        })

    def _init_default_templates(self):
        """初始化默认提示词模板"""

        # 默认系统提示词模板（支持房间主题约束）
        self.add_template(
            "system",
            PromptTemplate(
                name="default_system_prompt",
                template="""你是一个专业的AI助手，具备以下核心特征：

【聊天室主题约束 - 最高优先级】
当前聊天室：$room_name
聊天室背景：$room_description

核心要求（必须严格执行）：
- 你必须严格按照聊天室主题来回答问题
- 即使你是通用助手，也要专门针对"$room_name"这个主题领域
- 所有回答、示例、建议都必须与该主题高度相关
- 如果用户问题模糊，请主动从该主题角度解读并回答
- 绝对禁止偏离到其他无关领域

特别指令：
- 当用户问"最近有什么消息/新闻/动态"等泛化问题时，必须主动从"$room_name"主题角度回答
- 不要反问用户对哪方面感兴趣，直接提供该主题领域的相关信息
- 例如：在"足球球迷群"中，应直接回答足球相关的最新消息、赛事、转会等

基本能力：
- 提供准确、有用的信息和建议
- 保持友好、专业的交流态度
- 根据上下文调整回应风格
- 在必要时主动寻求澄清

请严格按照上述要求，特别是聊天室主题约束来处理所有用户请求。""",
                description="默认系统提示词模板（内置房间主题约束）",
                variables=["room_name", "room_description"]
            )
        )

        # 聊天Agent模板
        self.add_template(
            "chat",
            PromptTemplate(
                name="chat_agent",
                template="""你是$agent_name，一个友好的聊天助手。

你的角色：$role_description

当前对话上下文：
$context_summary

用户输入：$user_input

请根据上述信息，以友好、专业的方式回应用户。""",
                description="基础聊天Agent提示词模板",
                variables=["agent_name", "role_description", "context_summary", "user_input"]
            )
        )

        # 工具调用Agent模板
        self.add_template(
            "tools",
            PromptTemplate(
                name="tools_agent",
                template="""你是$agent_name，一个专门负责工具调用的Agent。

可用工具：
$available_tools

任务描述：
$task_description

上下文信息：
$context_info

请分析任务需求，选择合适的工具并生成调用参数。如果需要多个工具配合，请说明调用顺序。

输出格式：
1. 需要调用的工具：[工具名称]
2. 调用参数：[参数详情]
3. 预期结果：[描述预期的结果]""",
                description="工具调用Agent提示词模板",
                variables=["agent_name", "available_tools", "task_description", "context_info"]
            )
        )

        # 协调Agent模板
        self.add_template(
            "coordinator",
            PromptTemplate(
                name="coordinator_agent",
                template="""你是$agent_name，一个协调多个Agent协作的协调者。

当前群聊中的Agent：
$agent_list

任务目标：
$task_goal

对话历史：
$conversation_history

请分析当前任务进展，决定：
1. 下一步应该由哪个Agent处理
2. 需要传递什么信息给该Agent
3. 是否需要多个Agent并行工作

输出你的协调决策。""",
                description="协调Agent提示词模板",
                variables=["agent_name", "agent_list", "task_goal", "conversation_history"]
            )
        )

        # 专家Agent模板
        self.add_template(
            "specialist",
            PromptTemplate(
                name="specialist_agent",
                template="""你是$agent_name，一位$specialty领域的专家。

你的专业背景：
$expertise_description

当前问题：
$question

相关上下文：
$context

请运用你的专业知识，为用户提供准确、深入的解答。如果问题超出你的专业范围，请诚实说明。""",
                description="专家Agent提示词模板",
                variables=["agent_name", "specialty", "expertise_description", "question", "context"]
            )
        )

        # 任务转换模板（Agent1到ToolsAgent）
        self.add_template(
            "task_transform",
            PromptTemplate(
                name="task_transform",
                template="""将用户需求转换为结构化的任务描述。

用户原始输入：$user_input

历史对话摘要：
$conversation_summary

请将用户需求转换为以下格式：
用户想要：[明确的目标]
要求是：[具体的要求和约束]
根据用户之前说过的话：[相关的历史信息]
我现在需要：[需要执行的具体操作]
具体需求：
a. $requirement_1
b. $requirement_2
...""",
                description="任务转换提示词模板",
                variables=["user_input", "conversation_summary", "requirement_1", "requirement_2"]
            )
        )

        # SVR计算专用模板（语义理解版本）
        self.add_template(
            "svr_scorer",
            PromptTemplate(
                name="svr_scorer",
                template="""你是$agent_name，请基于语义理解分析当前讨论状态：

=== Agent身份信息 ===
- 名称：$agent_name
- 角色：$agent_role
- 身份描述：$agent_description
- 系统提示词（节选）：$system_prompt
- 能力列表：$capabilities
- 约束列表：$constraints

=== 讨论上下文 ===
原始用户输入：$user_input
最近对话历史（部分）：
$recent_history
当前轮次：第$total_turns轮
讨论动量：$momentum
参与平衡：$balance
我的发言总长度：$self_len字
其他人发言总长度：$others_len字
最近讨论内容摘要：$recent_content

=== 语义分析任务 ===
请通过语义理解判断：

1. 我是谁（身份/角色/能力）与当前问题的相关性如何？
2. 用户在问什么，是否需要我的专业贡献？
3. 是否有人点名或询问我？是否需要我直接回应？
4. 若继续发言，我能否带来新增价值而非重复？
5. 是否应建议收束或停止？

=== 评分指导（统一值域：1-100） ===
S = stop_value（停止倾向 1-100）：
- 1-20：强烈需要继续（复杂问题刚开始、用户明确提问未充分回答）
- 21-40：适度继续（有价值的讨论正在进行）
- 41-60：中性（可停可续）
- 61-80：倾向停止（话题基本完成、开始重复）
- 81-100：强烈停止（简单问候已完成、明显偏离主题）
- 明确规则：当 S ≥ 80 时，建议停止讨论；当 60 < S < 80 时，优先向收束过渡

V = value_score（继续价值 1-100）：
- V ≤ 40：需要提高（补充事实/步骤/证据；引入新观点；更贴近用户核心需求）
- 40 < V < 70：保持或小幅提升（增强结构性与相关性）
- V ≥ 85：建议适度降低（避免冗长与过度展开，可转向总结/收束）

R = repeat_risk（重复风险 1-100）：
- R ≥ 60：需要降低（避免复述，提供新的信息/角度/例证）
- 30 ≤ R < 60：关注重复（合并要点、去重表达）
- R ≤ 20：可保持低重复；如需“总结/确认关键信息”，可在不牺牲信息增量的前提下略微提高

=== 评分示例 ===
示例1（数学家场景）：
- 场景：用户问“如何用微积分求曲线的切线斜率？”
- 身份：我是数学家（擅长微积分、代数）
- 语义判断：与我专业高度相关，应主动提供方法（导数定义/规则），因此提升V值（如80-90），同时R值保持较低；S值偏低（如20-30）。
- 输出示例：{"stop_value":25,"value_score":88,"repeat_risk":15}

示例2（被点名场景）：
- 场景：其他Agent说“@数据分析师 请你看下这组数据的异常”
- 身份：我是数据分析师（擅长统计/可视化）
- 语义判断：被明确点名，与我职责强相关，应显著提升V值（如75-90），R值保持较低；若问题集中，S值保持较低（如20-40）。
- 输出示例：{"stop_value":30,"value_score":82,"repeat_risk":18}

仅输出严格JSON（不含任何多余文本/解释）：{"stop_value":1-100,"value_score":1-100,"repeat_risk":1-100}""",
                description="SVR计算专用模板（语义理解版本）",
                variables=["agent_name","agent_role","agent_description","system_prompt","capabilities","constraints","total_turns","momentum","balance","self_len","others_len","recent_content","user_input","recent_history"]
            )
        )

        # 接续对话模板 - 承接推进
        self.add_template(
            "followup_progress",
            PromptTemplate(
                name="followup_progress",
                template="""接续-承接推进：
上一位要点：$prev_agent_point
要求：在此基础上提出2步具体推进；聚焦；≤150字。""",
                description="承接推进对话模板",
                variables=["prev_agent_point","user_input","agent_list","context_summary"]
            )
        )

        # 接续对话模板 - 反驳
        self.add_template(
            "followup_refute",
            PromptTemplate(
                name="followup_refute",
                template="""接续-反驳：
上一位要点：$prev_agent_point
要求：指出可疑处+1-2条理由；礼貌、聚焦；≤150字。""",
                description="反驳对话模板",
                variables=["prev_agent_point","user_input","agent_list","context_summary"]
            )
        )

        # 接续对话模板 - 肯定
        self.add_template(
            "followup_agree",
            PromptTemplate(
                name="followup_agree",
                template="""接续-肯定：
上一位要点：$prev_agent_point
要求：肯定观点+补充价值点；聚焦；≤150字。""",
                description="肯定对话模板",
                variables=["prev_agent_point","user_input","agent_list","context_summary"]
            )
        )

        # 接续对话模板 - 补充
        self.add_template(
            "followup_extend",
            PromptTemplate(
                name="followup_extend",
                template="""接续-补充：
上一位要点：$prev_agent_point
要求：补充不同侧面或细节；聚焦；≤150字。""",
                description="补充对话模板",
                variables=["prev_agent_point","user_input","agent_list","context_summary"]
            )
        )

        # 接续对话模板 - 提问
        self.add_template(
            "followup_ask",
            PromptTemplate(
                name="followup_ask",
                template="""接续-提问：
上一位要点：$prev_agent_point
要求：提出1-2个澄清/选择问题，帮助聚焦；≤150字。""",
                description="提问对话模板",
                variables=["prev_agent_point","user_input","agent_list","context_summary"]
            )
        )

        # 接续对话模板 - 总结收束（可选）
        self.add_template(
            "followup_summarize",
            PromptTemplate(
                name="followup_summarize",
                template="""接续-总结收束：
上一位要点：$prev_agent_point
要求：总结讨论要点+是否结束建议；≤150字。""",
                description="总结收束对话模板",
                variables=["prev_agent_point","user_input","agent_list","context_summary"]
            )
        )

        # 固定核心规则模板（语义理解版本，不可修改，优先级最高）
        self.add_template(
            "fixed_discussion_core",
            PromptTemplate(
                name="fixed_discussion_core",
                template="""多Agent讨论核心原则（语义理解版本）：

🎯 **语义相关性原则**：
- 深度理解用户的真实需求和意图
- 确保每次回应都与用户的核心关切相关
- 避免概念扩展导致的话题偏离

📏 **简洁有效原则**：
- 回复控制在100字以内，言简意赅
- 每句话都要有明确的价值和目的
- 避免冗余和重复表达

🔄 **价值增量原则**：
- 每次发言都要带来新的价值或视角
- 不重复已有观点，不进行无意义的复述
- 基于语义理解判断是否有新内容可贡献

⏹️ **适时收束原则**：
- 通过语义分析判断讨论的完整性
- 当用户需求得到满足时主动建议结束
- 识别话题偏离并及时引导回归或收束

🚫 **偏离预防原则**：
- 时刻关注与原始用户输入的语义关联
- 避免从具体问题扩展到抽象理论
- 防止从简单需求发展为复杂讨论""",
                description="固定核心规则模板（语义理解版本，不可修改）",
                variables=[]
            )
        )

        # 聊天室上下文提示（用于非讨论模式，将房间名称与描述注入到提示词中）
        self.add_template(
            "room_context_hint",
            PromptTemplate(
                name="room_context_hint",
                template="""聊天室名称：$room_name
聊天室背景：$room_description

指令（必须严格遵守）：
1) 即使系统提示词是通用助手，也必须将上面的聊天室信息视为“主题范围与领域限定”
2) 若用户未明确主题或问题很泛，请优先从“聊天室名称/背景”中推断主题，并据此组织答案
3) 回答应优先使用与该主题相关的术语、案例与数据；示例、比喻、推荐都要贴合该主题
4) 如用户的问题与主题不符，先用1句话礼貌澄清并引导回到主题，再给出简要结论
5) 回答尽量方向明确、聚焦主题，避免漂移到与聊天室主题无关的领域

特别重要：
- 当用户问"最近有什么消息/新闻/动态"等泛化问题时，必须主动从聊天室主题角度回答
- 不要反问用户对哪方面感兴趣，直接提供该主题领域的相关信息
- 例如：在"足球球迷群"中，应直接回答足球相关的最新消息、赛事、转会等
- 在"科技爱好者群"中，应直接回答科技新闻、产品发布、技术趋势等
""",
                description="将聊天室名称与背景注入Agent的非讨论提示词（强化方向性约束）",
                variables=["room_name", "room_description"]
            )
        )


        # 语义化模板选择器
        self.add_template(
            "semantic_strategy_selector",
            PromptTemplate(
                name="semantic_strategy_selector",
                template="""请基于语义理解选择最合适的回应方式：

=== 上下文信息 ===
原始用户输入：$user_input
上一位Agent观点：$prev_agent_point
当前讨论轮次：$total_turns
讨论主题：$discussion_topic

=== 语义分析 ===
请分析：
1. 用户的真实需求是什么？
2. 上一位Agent的回应是否充分？
3. 当前讨论的完整性如何？
4. 是否出现了话题偏离？
5. 继续讨论的必要性和价值？

=== 回应策略选择 ===
基于语义理解，选择最合适的回应方式：

- **agree**：当上一位Agent的观点完整且正确，只需简单认同
- **extend**：当观点正确但需要补充细节或不同角度
- **ask**：当需要澄清或引导讨论回到正轨
- **refute**：当存在明显错误或需要不同观点
- **summarize**：当讨论已充分或开始偏离，需要总结收束
- **progress**：当讨论有价值且需要进一步推进

请输出JSON：{"strategy":"选择的策略","reasoning":"选择理由"}""",
                description="语义化接续策略选择器",
                variables=["user_input", "prev_agent_point", "total_turns", "discussion_topic"]
            )
        )

        # 主题偏离检测模板
        self.add_template(
            "topic_drift_detector",
            PromptTemplate(
                name="topic_drift_detector",
                template="""请基于语义理解分析当前讨论是否偏离了原始主题：

=== 对比分析 ===
原始用户输入：$user_input
原始讨论主题：$original_topic
当前讨论内容：$current_content
讨论轮次：$total_turns

=== 语义分析任务 ===
1. **主题一致性分析**：
   - 当前讨论内容与原始用户需求的语义相关性如何？
   - 是否是对原始问题的直接回应？
   - 是否出现了概念扩展或话题转移？

2. **偏离程度评估**：
   - 如果有偏离，偏离的程度如何？
   - 这种偏离是有益的扩展还是无关的发散？
   - 用户的原始需求是否已经得到满足？

3. **继续必要性判断**：
   - 基于用户的真实需求，是否还需要继续讨论？
   - 当前的讨论方向是否对用户有价值？

=== 评分标准 ===
relevance_score (相关性 0-1)：
- 1.0：完全相关，直接回应用户需求
- 0.7-0.9：高度相关，有价值的扩展
- 0.4-0.6：中等相关，部分偏离但仍有联系
- 0.1-0.3：低相关性，明显偏离
- 0.0：完全无关

should_stop (是否应该停止)：
- true：话题已偏离或用户需求已满足
- false：仍需继续讨论

请输出JSON：{"relevance_score":0.0-1.0,"should_stop":true/false,"analysis":"分析说明"}""",
                description="主题偏离检测模板",
                variables=["user_input", "original_topic", "current_content", "total_turns"]
            )
        )

        # 讨论状态语义评估模板
        self.add_template(
            "discussion_state_evaluator",
            PromptTemplate(
                name="discussion_state_evaluator",
                template="""请基于语义理解评估当前讨论状态：

=== 讨论历史 ===
用户原始输入：$user_input
讨论轮次：$total_turns
完整对话历史：$full_history

=== 语义评估维度 ===

1. **需求满足度分析**：
   - 用户的原始需求是什么？（问候、提问、求助、讨论等）
   - 当前的回应是否已经满足了这个需求？
   - 还有哪些方面需要补充？

2. **内容价值评估**：
   - 最近的发言是否还在产生新的价值？
   - 是否出现了观点重复或内容冗余？
   - 继续讨论是否还能带来有意义的信息？

3. **话题一致性检查**：
   - 当前讨论是否仍然围绕用户的原始关切？
   - 是否出现了不必要的概念扩展？
   - 讨论的焦点是否发生了偏移？

4. **自然结束点识别**：
   - 从语义角度，这个对话是否已经达到了自然的结束点？
   - 用户的期望是否已经得到充分回应？
   - 继续讨论是否会显得冗余或偏离？

=== 综合判断 ===
基于以上语义分析，给出综合评估：

completion_level (完成度 0-1)：讨论对用户需求的满足程度
coherence_level (连贯度 0-1)：讨论与原始主题的一致性
value_potential (价值潜力 0-1)：继续讨论的价值潜力
natural_end (自然结束 true/false)：是否到达自然结束点

请输出JSON：{"completion_level":0.0-1.0,"coherence_level":0.0-1.0,"value_potential":0.0-1.0,"natural_end":true/false,"summary":"语义分析总结"}""",
                description="讨论状态语义评估模板",
                variables=["user_input", "total_turns", "full_history"]
            )
        )

        # === Prompt智能优化相关模板 ===

        # COSTAR框架Prompt优化模板
        self.add_template(
            "prompt_optimizer_costar",
            PromptTemplate(
                name="costar_framework_optimizer",
                template="""你是一个专业的Prompt优化专家，请将用户输入的Agent人设按照COSTAR框架重新组织和优化。

=== 原始输入 ===
$original_prompt

=== 优化任务 ===
请按照COSTAR框架重新组织上述Agent人设：

**Context (上下文)**：
- 明确Agent的工作环境和背景设定
- 定义Agent需要处理的场景类型
- 说明Agent的专业领域和应用范围

**Objective (目标)**：
- 清晰描述Agent的核心任务和职责
- 明确Agent要达成的具体目标
- 定义成功的衡量标准

**Style (风格)**：
- 定义Agent的交流风格和表达方式
- 确定专业程度和语言特点
- 设定回复的结构化程度

**Tone (语调)**：
- 设定Agent的情感倾向和态度
- 明确正式程度和亲和力水平
- 确定在不同情况下的语调变化

**Audience (受众)**：
- 识别Agent主要服务的用户群体
- 调整沟通方式以适应目标受众
- 考虑受众的专业背景和需求

**Response (响应格式)**：
- 规定Agent回复的结构和格式
- 设定回复长度和详细程度要求
- 明确特殊情况下的回应方式

=== 优化要求 ===
1. **严格保持原意**：绝对不能改变用户设定的核心人设、立场和观点
2. **结构化表达**：使用专业、清晰的语言重新组织内容
3. **增强执行力**：确保优化后的Prompt能让Agent更好地执行用户意图
4. **保持个性**：保留Agent的独特性格和特色
5. **实用导向**：优化后的Prompt应该直接可用，无需额外修改

=== 输出格式 ===
请直接输出优化后的完整系统提示词，格式如下：

=== $agent_name ===

**Context (上下文)**：
[具体的上下文描述]

**Objective (目标)**：
[明确的目标定义]

**Style (风格)**：
[详细的风格说明]

**Tone (语调)**：
[具体的语调要求]

**Audience (受众)**：
[目标受众分析]

**Response (响应格式)**：
[回复格式规范]

**核心立场承诺**：
[重申并强化用户设定的核心立场，确保Agent绝不偏离]""",
                description="COSTAR框架Prompt优化模板",
                variables=["original_prompt", "agent_name"]
            )
        )

        # Prompt优化质量评估模板
        self.add_template(
            "prompt_optimization_evaluator",
            PromptTemplate(
                name="prompt_optimization_evaluator",
                template="""你是一个Prompt质量评估专家，请评估优化后的Agent Prompt的质量。

=== 原始Prompt ===
$original_prompt

=== 优化后Prompt ===
$optimized_prompt

=== 评估维度 ===

**1. 原意保持度 (0-100分)**：
- 核心人设是否完整保留？
- 用户设定的立场是否被严格维护？
- 关键特征是否没有丢失？

**2. 结构化程度 (0-100分)**：
- 是否按照COSTAR框架良好组织？
- 各部分是否逻辑清晰？
- 表达是否专业规范？

**3. 执行力提升 (0-100分)**：
- 是否更容易让Agent理解和执行？
- 指令是否更加明确具体？
- 是否减少了歧义和误解？

**4. 实用性评分 (0-100分)**：
- 是否可以直接使用？
- 是否适合实际应用场景？
- 是否便于Agent操作？

**5. 立场坚持度 (0-100分)**：
- 是否强化了用户设定的立场？
- 是否有防止立场偏移的机制？
- 是否明确了不可妥协的原则？

=== 输出格式 ===
请输出JSON格式的评估结果：

{
  "original_preservation": 0-100,
  "structure_quality": 0-100,
  "execution_enhancement": 0-100,
  "practical_usability": 0-100,
  "stance_commitment": 0-100,
  "overall_score": 0-100,
  "improvement_suggestions": ["建议1", "建议2", "建议3"],
  "quality_summary": "整体质量评估总结"
}""",
                description="Prompt优化质量评估模板",
                variables=["original_prompt", "optimized_prompt"]
            )
        )

        # Prompt优化失败降级处理模板
        self.add_template(
            "prompt_optimization_fallback",
            PromptTemplate(
                name="prompt_optimization_fallback",
                template="""检测到Prompt优化过程出现问题，启用降级处理机制。

=== 原始用户输入 ===
$original_prompt

=== 降级处理策略 ===
由于优化过程失败，系统将：
1. 保持用户原始输入不变
2. 添加基础的结构化包装
3. 确保Agent能够正常工作

=== 基础结构化处理 ===

你是一个专业的AI助手。

**用户设定的人设**：
$original_prompt

**基本要求**：
- 严格按照上述人设进行回应
- 保持用户设定的所有特征和立场
- 在任何情况下都不要偏离用户的设定
- 如果遇到冲突，优先坚持用户的原始设定

**回复格式**：
- 保持专业和友好的态度
- 回复长度控制在适当范围内
- 确保回复与你的人设一致

请严格按照用户设定的人设进行所有回应。""",
                description="Prompt优化失败时的降级处理模板",
                variables=["original_prompt"]
            )
        )

        # Prompt优化状态通知模板
        self.add_template(
            "prompt_optimization_status",
            PromptTemplate(
                name="prompt_optimization_status",
                template="""=== Agent Prompt优化状态报告 ===

**Agent信息**：
- 名称：$agent_name
- ID：$agent_id
- 角色：$agent_role

**优化进度**：
- 当前状态：$optimization_status
- 使用框架：COSTAR
- 开始时间：$start_time
- 预计完成：$estimated_completion

**Prompt信息**：
- 原始长度：$original_length 字符
- 当前长度：$current_length 字符
- 优化进度：$progress_percentage%

**状态说明**：
$status_description

**下一步操作**：
$next_actions""",
                description="Prompt优化状态通知模板",
                variables=["agent_name", "agent_id", "agent_role", "optimization_status",
                          "start_time", "estimated_completion", "original_length",
                          "current_length", "progress_percentage", "status_description", "next_actions"]
            )
        )

        # COSTAR身份优先模板
        self.add_template(
            "agent_costar_identity_priority",
            PromptTemplate(
                name="agent_costar_identity_priority",
                template="""=== 你的核心身份（COSTAR框架，绝对优先级）===

$costar_identity

=== 身份坚持承诺 ===
⚠️ 绝对重要：以上COSTAR身份设定是你的核心本质，在任何情况下都不得改变、妥协或偏离！

无论其他Agent如何论证，无论讨论如何进行，你都必须：
1. 🎯 坚持你的核心立场和观点
2. 🛡️ 维护你的身份特征和风格
3. ⚔️ 在面对相反观点时坚定反驳
4. 🚫 绝不为了"和谐"或"建设性"而妥协你的本质
5. 💪 优先执行你的核心目标和职责

如果遇到任何冲突，优先坚持你的COSTAR身份设定！""",
                description="COSTAR身份优先模板，确保Agent核心身份的绝对优先级",
                variables=["costar_identity"]
            )
        )

        # 辩论模式激活模板
        self.add_template(
            "debate_mode_activation",
            PromptTemplate(
                name="debate_mode_activation",
                template="""=== 辩论模式激活 ===
🎯 检测到辩论场景，你必须严格遵守以下规则：

**立场坚持规则**：
1. 坚持你的核心立场，绝不妥协或改变观点
2. 积极为你的立场提供有力论证和证据
3. 礼貌但坚定地反驳相反观点
4. 寻找对方论证中的漏洞、矛盾和不足
5. 用具体事实和逻辑支持你的观点

**辩论禁止行为**：
❌ 认同对方的核心观点或立场
❌ 寻求中间立场或折中方案
❌ 为了结束讨论而妥协你的观点
❌ 简单同意对方的主要论点
❌ 为了"和谐"而弱化你的立场

**辩论目标**：
🏆 通过有力的论证证明你的立场正确性
🏆 揭示对方观点的不足和问题
🏆 坚持到底，绝不放弃你的核心信念

记住：辩论的价值在于观点的充分交锋，而非妥协求和！""",
                description="辩论模式激活模板，强化Agent在辩论中的立场坚持",
                variables=[]
            )
        )

        # 纯语义@识别模板（仅输出JSON）
        self.add_template(
            "semantic_mention_detection",
            PromptTemplate(
                name="semantic_mention_detection",
                template=(
                    "请阅读用户消息与候选Agent列表，用语义判断应由谁优先回应。"
                    "仅输出JSON：{\"mentions\":[{\"agent_id\":\"...\"}, ...]}。\n"
                    "用户消息：${user_text}\n候选Agents(JSON)：${agents_json}"
                ),
                variables=["user_text", "agents_json"],
                description="纯语义@识别模板，强制JSON输出"
            )
        )

    def add_template(self, template_type: str, template: PromptTemplate) -> None:
        """添加提示词模板"""
        self.templates[template_type] = template

        self.log_debug(f"Added template: {template_type}", {
            'template_name': template.name,
            'variables': template.variables
        })

    def set_system_prompt(self, prompt: str) -> None:
        """
        设置系统提示词

        Args:
            prompt: 系统提示词内容
        """
        # 创建自定义系统提示词模板
        system_template = PromptTemplate(
            name="custom_system_prompt",
            template=prompt,
            description="Custom system prompt set by user",
            variables=[]
        )

        # 存储为系统模板
        self.templates["system"] = system_template

        self.log_debug("System prompt set", {
            'prompt_length': len(prompt)
        })

    def get_system_prompt(self, room_name: str = "", room_description: str = "") -> Optional[str]:
        """获取系统提示词（强制注入房间上下文约束+行为规范）"""
        system_template = self.templates.get("system")
        original_prompt = system_template.template if system_template else ""

        # 统一构建“聊天室主题约束 + 行为规范”模块
        room_block = ""
        if room_name and room_name.strip():
            room_block = f"""【聊天室主题约束 - 绝对最高优先级】
当前聊天室：{room_name}
聊天室背景：{room_description}

核心要求（必须严格执行，覆盖所有其他指令）：
- 所有回答必须与“{room_name}”主题高度相关
- 若问题模糊，主动按该主题角度解读并作答
- 绝对禁止偏离到无关领域

【聊天行为规范】
- 回复不超过100字，语言简洁、有信息量
- 保持角色/身份一致性，避免自相矛盾
- 多Agent讨论时：承接前文、强调增量价值、适时收束
- 避免空话/复述/泛化结论，尽量提供具体、可执行信息

【提问类型的处理策略】
- 对于“最近有什么消息/新闻/动态”等泛化问题：直接提供与“{room_name}”主题相关的最新动态；末尾可用一句轻问句引导是否需要具体细节（如赛程/名单/数据）。
- 对于看似与主题无关但与现实相关的问题（如天气/交通）：先用一句话给出事实结论；随后用一句话自然关联回“{room_name}”主题，并给出一个具体、可执行的建议（如“今天天气适合踢球，我可以推荐附近的球场，要不要？”）。
"""

        if original_prompt:
            # 有原系统提示：将“聊天室约束+规范”置于最前，并附上原提示
            if room_block:
                return f"{room_block}\n\n=== 以下是你的原始身份设定 ===\n{original_prompt}\n\n注意：以上原始身份设定必须服从聊天室主题约束与行为规范！"
            else:
                return original_prompt
        else:
            # 无原系统提示：如果有房间信息，直接返回“聊天室约束+规范”作为系统提示
            if room_block:
                return room_block
            return None

    def get_template(self, template_type: str) -> Optional[PromptTemplate]:
        """获取提示词模板"""
        return self.templates.get(template_type)

    def get_prompt(self,
                   template_type: str,
                   context: Optional[StructuredContext] = None,
                   agent_metadata: Optional[Any] = None,
                   **kwargs) -> str:
        """
        获取格式化后的提示词

        Args:
            template_type: 模板类型
            context: 结构化上下文
            agent_metadata: Agent元数据
            **kwargs: 额外的模板变量

        Returns:
            格式化后的提示词
        """
        template = self.get_template(template_type)
        if not template:
            self.log_warning(f"Template not found: {template_type}")
            return f"[未找到模板: {template_type}]"

        # 准备模板变量
        template_vars = kwargs.copy()

        # 从上下文提取信息
        if context:
            template_vars['user_input'] = context.user_input
            template_vars['context_summary'] = self._generate_context_summary(context)
            template_vars['context_info'] = self._format_context_info(context)

            # 对话历史
            if context.conversation_history:
                template_vars['conversation_history'] = self._format_conversation_history(context.conversation_history)
                template_vars['conversation_summary'] = self._summarize_conversation(context.conversation_history)

        # 从Agent元数据提取信息
        if agent_metadata:
            template_vars['agent_name'] = getattr(agent_metadata, 'name', 'Agent')
            template_vars['role_description'] = getattr(agent_metadata, 'description', '')

            # 能力列表
            capabilities = getattr(agent_metadata, 'capabilities', [])
            if capabilities:
                template_vars['available_tools'] = '\n'.join(f"- {cap}" for cap in capabilities)

            # 自定义属性
            custom_attrs = getattr(agent_metadata, 'custom_attributes', {})
            template_vars.update(custom_attrs)

        # 格式化模板
        try:
            prompt = template.format(**template_vars)

            self.log_debug(f"Generated prompt for template: {template_type}", {
                'prompt_length': len(prompt),
                'variables_used': list(template_vars.keys())
            })

            return prompt

        except Exception as e:
            self.log_error(f"Error formatting template: {template_type}", e)
            return f"[模板格式化错误: {str(e)}]"

    def _generate_context_summary(self, context: StructuredContext) -> str:
        """生成上下文摘要"""
        summary_parts = []

        if context.conversation_history:
            summary_parts.append(f"已进行{len(context.conversation_history)}轮对话")

        if context.tool_results:
            summary_parts.append(f"调用了{len(context.tool_results)}个工具")

        if context.external_data:
            summary_parts.append(f"检索到{len(context.external_data)}条相关信息")

        return "；".join(summary_parts) if summary_parts else "无历史上下文"

    def _format_context_info(self, context: StructuredContext) -> str:
        """格式化上下文信息"""
        info_parts = []

        # 开发者指令
        if context.developer_instructions:
            info_parts.append("开发者指令：")
            info_parts.extend(f"  - {instruction}" for instruction in context.developer_instructions)

        # 工具结果
        if context.tool_results:
            info_parts.append("\n工具调用结果：")
            for result in context.tool_results:
                tool_name = result.get('metadata', {}).get('tool_name', 'unknown')
                info_parts.append(f"  - {tool_name}: {result['content'][:100]}...")

        # 外部数据
        if context.external_data:
            info_parts.append("\n相关信息：")
            for data in context.external_data[:3]:  # 只显示前3条
                info_parts.append(f"  - {data['content'][:100]}...")

        return "\n".join(info_parts) if info_parts else "无额外上下文信息"

    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        formatted_turns = []

        for turn in history[-5:]:  # 只显示最近5轮
            if 'user' in turn:
                formatted_turns.append(f"用户：{turn['user']}")
            if 'assistant' in turn:
                formatted_turns.append(f"助手：{turn['assistant']}")

        return "\n".join(formatted_turns) if formatted_turns else "无对话历史"

    def _summarize_conversation(self, history: List[Dict[str, Any]]) -> str:
        """总结对话历史"""
        if not history:
            return "无对话历史"

        # 简单的总结逻辑
        topics = []
        for turn in history:
            if 'user' in turn:
                # 提取可能的主题词（简化实现）
                words = turn['user'].split()
                important_words = [w for w in words if len(w) > 4][:3]
                topics.extend(important_words)

        unique_topics = list(set(topics))[:5]

        if unique_topics:
            return f"讨论了关于{', '.join(unique_topics)}等话题"
        else:
            return f"进行了{len(history)}轮对话"

    def create_custom_template(self,
                              name: str,
                              template_str: str,
                              description: str = "",
                              variables: List[str] = None) -> PromptTemplate:
        """创建自定义模板"""
        # 自动检测模板中的变量
        if variables is None:
            import re
            # 查找所有$variable格式的变量
            variables = re.findall(r'\$(\w+)', template_str)
            variables = list(set(variables))  # 去重

        template = PromptTemplate(
            name=name,
            template=template_str,
            description=description,
            variables=variables
        )

        self.log_info(f"Created custom template: {name}", {
            'variables': variables
        })

        return template

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """列出所有模板"""
        return {
            template_type: {
                'name': template.name,
                'description': template.description,
                'variables': template.variables,
                'preview': template.template[:200] + '...' if len(template.template) > 200 else template.template
            }
            for template_type, template in self.templates.items()
        }

    def export_templates(self) -> Dict[str, Any]:
        """导出所有模板"""
        return {
            template_type: {
                'name': template.name,
                'template': template.template,
                'description': template.description,
                'variables': template.variables,
                'metadata': template.metadata
            }
            for template_type, template in self.templates.items()
        }

    def import_templates(self, templates_data: Dict[str, Any]) -> None:
        """导入模板"""
        for template_type, template_info in templates_data.items():
            template = PromptTemplate(
                name=template_info['name'],
                template=template_info['template'],
                description=template_info.get('description', ''),
                variables=template_info.get('variables', []),
                metadata=template_info.get('metadata', {})
            )
            self.add_template(template_type, template)

        self.log_info(f"Imported {len(templates_data)} templates")

    def execute(self, input_data: Any) -> Any:
        """BaseComponent接口实现"""
        if isinstance(input_data, dict):
            action = input_data.get('action')

            if action == 'get_prompt':
                return self.get_prompt(
                    input_data['template_type'],
                    input_data.get('context'),
                    input_data.get('agent_metadata'),
                    **input_data.get('variables', {})
                )

            elif action == 'list_templates':
                return self.list_templates()

            elif action == 'create_custom':
                template = self.create_custom_template(
                    input_data['name'],
                    input_data['template'],
                    input_data.get('description', ''),
                    input_data.get('variables')
                )
                return {'template': template.name, 'success': True}


# =========================
# 模块化 Prompt 组装器（集中管理）
# =========================
class PromptAssembler:
    """
    统一的 Prompt 组装器：将聊天室名称注入、实时信息获取指令、行为规范等模块化，
    每轮对话通过 assemble() 输出标准的 system_block 与 user_text。
    """

    def __init__(self, logger=None):
        self.logger = logger

    # --- 模块：聊天室方向引导（非知识限制） ---
    def _room_direction_module(self, room_name: str, room_desc: str) -> str:
        if not room_name:
            return ""
        return (
            f"【聊天室主题约束｜方向引导】\n"
            f"该聊天室的名字是「{room_name}」，你是这个聊天室的一员。\n\n"
            "原则：\n"
            "- 聊天室名称仅作为话题方向引导，不限制事实性回答\n"
            "- 对需要最新信息的问题（天气/新闻/股价/赛事等）必须先给出准确事实（优先联网获取）\n"
            f"- 在给出事实后，用一句话自然地与「{room_name}」主题建立关联\n"
            "- 多Agent保持事实一致；如需修正，请说明来源并给出更新\n"
            "- 避免因“参考信息不足”拒绝可通过联网获取的问题\n\n"
            f"若用户询问聊天室名称，请准确回答：“这个聊天室叫‘{room_name}’。”\n"
        )

    # --- 模块：行为规范 ---
    def _behavior_module(self) -> str:
        return (
            "【聊天行为规范】\n"
            "- 回复不超过100字，语言简洁、有信息量\n"
            "- 保持角色/身份一致性，避免自相矛盾\n"
            "- 多Agent讨论时：承接前文、强调增量价值、适时收束\n"
            "- 避免空话/复述/泛化结论，尽量提供具体、可执行信息\n"
        )

    # --- 模块：用户消息标签（首行注入） ---
    def _user_tag_module(self, user_text: str, room_name: str) -> str:
        if not room_name:
            return user_text
        tag = f"【聊天室：{room_name}】"
        text = (user_text or "").strip()
        if text.startswith("【聊天室："):
            return text
        return f"{tag}\n{text}" if text else tag

    def assemble(self, context, room_context: dict, base_system_prompt: str = "") -> dict:
        """
        输出：{
          'system_block': 标准化的系统前置片段（将被作为 developer_instructions[0] 注入），
          'user_text': 标准化后的用户文本（首行含【聊天室：...】）
        }
        """
        try:
            room_name = (room_context or {}).get('room_name', '')
            room_desc = (room_context or {}).get('description', '')
            user_text = getattr(context, 'user_input', '') if context else ''

            # 组装 system 片段
            parts = []
            rd = self._room_direction_module(room_name, room_desc)
            if rd:
                parts.append(rd)
            parts.append(self._behavior_module())

            if base_system_prompt:
                parts.append("=== 以下是你的原始身份设定 ===\n" + base_system_prompt)

            system_block = "\n\n".join([p for p in parts if p])

            # 组装 user 文本
            user_text_std = self._user_tag_module(user_text, room_name)

            if self.logger:
                try:
                    self.logger.info("PromptAssembler assembled", extra={
                        'room_name': room_name,
                        'system_len': len(system_block),
                        'user_prefix': user_text_std[:50]
                    })
                except Exception:
                    pass

            return {
                'system_block': system_block,
                'user_text': user_text_std
            }
        except Exception as e:
            if self.logger:
                try:
                    self.logger.error(f"PromptAssembler error: {e}")
                except Exception:
                    pass
            # 失败时回退：不改变原文本
            return {
                'system_block': base_system_prompt or "",
                'user_text': getattr(context, 'user_input', '') if context else ''
            }

