"""自学习 Agent — 审查历史报告，提炼分析技能

通过对比多份历史研报，识别遗漏的分析维度和可改进之处，
将经验提炼为可复用的分析技能（skill），注入未来的报告生成。
"""

import json
import re
import uuid

from loguru import logger

from stock.data.storage import Storage
from stock.llm import chat, is_configured


def _build_review_prompt(
    code: str,
    name: str,
    reports: list[dict],
    existing_skills: list[str],
) -> str:
    reports_text = ""
    for i, r in enumerate(reports, 1):
        text = r["report_text"]
        if len(text) > 800:
            text = text[:800] + "...(截断)"
        reports_text += (
            f"### 报告{i}（{r['created_at']}）\n"
            f"用户补充: {r.get('user_input', '无')}\n"
            f"{text}\n\n"
        )

    skills_text = "\n".join(f"- {s}" for s in existing_skills) if existing_skills else "暂无"

    return (
        f"你是一位分析报告质量审查专家。以下是对 {name}（{code}）的多份历史分析报告。\n\n"
        f"请审查这些报告，识别以下模式：\n"
        f"1. 哪些分析维度被反复遗漏？\n"
        f"2. 哪些预判后来被证实或证伪？（对比不同时间点的报告）\n"
        f"3. 报告之间是否存在矛盾或不一致？\n"
        f"4. 有哪些行业/公司特有的分析角度应该固定纳入？\n\n"
        f"## 历史报告\n\n{reports_text}"
        f"## 当前已有的分析技能\n{skills_text}\n\n"
        f"## 输出要求\n"
        f"请输出 JSON 数组，每个元素是一条新的分析技能/规则：\n"
        f'```json\n'
        f'[\n'
        f'  {{\n'
        f'    "scope": "stock" 或 "industry" 或 "global",\n'
        f'    "text": "具体的分析指导规则",\n'
        f'    "reason": "为什么需要这条规则"\n'
        f'  }}\n'
        f']\n'
        f'```\n'
        f"只输出新的、不与已有技能重复的规则。如果没有新发现，输出空数组 []。"
    )


def _parse_skills(response: str) -> list[dict]:
    json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    else:
        bracket_match = re.search(r"\[.*\]", response, re.DOTALL)
        if bracket_match:
            text = bracket_match.group(0)
        else:
            return []

    try:
        items = json.loads(text)
        if not isinstance(items, list):
            return []
        return [
            {
                "scope": item.get("scope", "stock"),
                "text": item.get("text", ""),
                "reason": item.get("reason", ""),
            }
            for item in items
            if item.get("text")
        ]
    except json.JSONDecodeError:
        return []


def review_reports(
    code: str,
    name: str,
    storage: Storage,
    industry: str = "",
) -> list[dict]:
    """审查历史报告并提炼新技能

    Returns:
        新提炼的技能列表 [{"scope", "text", "reason"}, ...]
    """
    if not is_configured():
        return []

    reports_df = storage.get_reports(code, limit=10)
    if reports_df.empty or len(reports_df) < 3:
        return []

    reports = reports_df.to_dict("records")

    existing_skills_df = storage.get_active_skills(code, industry)
    existing_skills = existing_skills_df["skill_text"].tolist() if not existing_skills_df.empty else []

    prompt = _build_review_prompt(code, name, reports, existing_skills)
    response = chat(prompt)

    new_skills = _parse_skills(response)

    report_ids = ",".join(str(r["id"]) for r in reports[:5])
    saved = []
    for skill in new_skills:
        skill_id = str(uuid.uuid4())[:8]
        scope = skill["scope"]
        storage.save_skill(
            skill_id=skill_id,
            skill_text=skill["text"],
            reason=skill["reason"],
            code=code if scope == "stock" else "",
            industry=industry if scope == "industry" else "",
            source_report_ids=report_ids,
        )
        saved.append(skill)
        logger.info(f"新技能: [{scope}] {skill['text'][:50]}")

    return saved
