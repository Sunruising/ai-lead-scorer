"""
打分核心：构造 prompt、调用 DeepSeek、解析并校正返回结果。

分数由大模型综合判断给出，SCORING_RULES 作为打分指引注入 prompt，
既利用模型的语义理解能力，又把打分维度收敛在可控范围内。
"""

import json
import os
import re

from openai import OpenAI

# 打分规则：按业务场景增删或调整权重描述，会被拼进 system prompt 作为打分依据。
SCORING_RULES = [
    "预算充足且明确（给出了具体金额、且金额可观）：强加分项",
    "需求描述清晰具体（说清了要解决什么问题、有明确的功能/服务诉求）：加分",
    "联系人是决策人（老板/合伙人/总监等能拍板的角色）：强加分项",
    "时间紧迫、有明确上线/采购时间点：加分",
    "公司规模较大或处于扩张期（有持续采购能力）：加分",
    "留有有效联系方式（电话/微信/邮箱齐全）：小幅加分",
    "需求模糊、只是随便问问、无预算或预算极低：减分",
    "联系人是基层执行者、无决策权：减分",
    "信息严重缺失（没需求、没预算、没联系方式）：大幅减分",
]

# 分级阈值：高意向 >= 70，中意向 40-69，低意向 < 40
TIER_HIGH_THRESHOLD = 70
TIER_MID_THRESHOLD = 40

# DeepSeek 配置（OpenAI 兼容）
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def _build_system_prompt() -> str:
    """构造 system prompt：注入角色、打分规则、输出格式约束。"""
    rules_text = "\n".join(f"- {rule}" for rule in SCORING_RULES)
    return f"""你是一名资深 B2B 销售线索评估专家。你的任务是对收到的一条销售线索打分，
判断它的成交意向高低，帮助销售团队优先跟进高价值线索。

请严格依据以下打分规则综合评估，给出 0-100 的整数分数：
{rules_text}

分级标准：
- score >= {TIER_HIGH_THRESHOLD}：高（高意向，需立即跟进）
- {TIER_MID_THRESHOLD} <= score < {TIER_HIGH_THRESHOLD}：中（中等意向，正常跟进）
- score < {TIER_MID_THRESHOLD}：低（低意向，暂缓或培育）

你必须只返回一个 JSON 对象，不要包含任何额外说明、不要用 markdown 代码块包裹。
JSON 字段要求：
- "score": 整数，0-100
- "tier": 字符串，只能是 "高" / "中" / "低" 三者之一
- "reasons": 字符串数组，列出 2-4 条打分理由（每条简明扼要，说明加分/减分点）
- "next_action": 字符串，给销售的一句话下一步行动建议
"""


def _build_user_prompt(lead: dict) -> str:
    """把线索字典格式化成可读文本交给模型。"""
    lead_text = json.dumps(lead, ensure_ascii=False, indent=2)
    return f"请评估以下销售线索：\n{lead_text}"


def _extract_json(text: str) -> dict:
    """从模型返回文本中提取 JSON，兼容裸 JSON、markdown 代码块包裹、夹带说明文字三种情况。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 去掉 markdown 代码块包裹
    fenced = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(fenced)
    except json.JSONDecodeError:
        pass

    # 抓取第一个大括号片段
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"无法从模型返回中解析出 JSON：{text[:200]}")


def _normalize_result(raw: dict) -> dict:
    """对模型返回的结果做归一化与兜底，保证字段类型与取值合法。"""
    # 分数：强制为 0-100 的整数
    try:
        score = int(round(float(raw.get("score", 0))))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    # 分级：以分数为准重新校正，避免模型给的 tier 与 score 不一致
    if score >= TIER_HIGH_THRESHOLD:
        tier = "高"
    elif score >= TIER_MID_THRESHOLD:
        tier = "中"
    else:
        tier = "低"

    # 理由：保证是字符串列表
    reasons = raw.get("reasons", [])
    if isinstance(reasons, str):
        reasons = [reasons]
    reasons = [str(r) for r in reasons if str(r).strip()]
    if not reasons:
        reasons = ["模型未给出明确理由"]

    next_action = str(raw.get("next_action", "")).strip() or "建议人工复核该线索"

    return {
        "score": score,
        "tier": tier,
        "reasons": reasons,
        "next_action": next_action,
        "need_immediate_follow_up": tier == "高",
    }


def _get_client() -> OpenAI:
    # 延迟到调用时读取 key，使模块导入不依赖环境变量

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在 .env 中填入")
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


def score_lead(lead: dict) -> dict:
    """对单条线索打分，返回结构化结果。

    入参 lead 为任意销售线索字段组成的 dict（公司、需求、预算、联系方式等）。
    出参字段：score / tier / reasons / next_action / need_immediate_follow_up。
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": _build_user_prompt(lead)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content
    raw = _extract_json(content)
    return _normalize_result(raw)
