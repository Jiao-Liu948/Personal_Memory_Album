# -*- coding: utf-8 -*-
"""
主动交互评测执行器：
1. 信息补全：规则检测缺失字段（与生产 detect_missing_info 一致，评测限定时间/地点/情感）
2. 纪念日识别：解析日期 + 周年计算（锚定 anchor_date，可复现）
3. 年度回忆：LLM 生成年度故事（复用生产 generate_yearly_recap 的故事生成逻辑）
"""
from datetime import datetime
from langchain_openai import ChatOpenAI
from config import settings
from services.proactive_service import _parse_date_from_text
from services.memory_service import extract_model
from utils.langfuse_client import trace_llm_call


# ============ 1. 信息补全 ============
def detect_missing_fields(fact: dict) -> list:
    """检测记忆缺失字段，返回中文字段名列表"""
    missing = []
    if not fact.get("time_info"):
        missing.append("时间")
    if not fact.get("location"):
        missing.append("地点")
    if not fact.get("emotion"):
        missing.append("情感")
    return missing


# ============ 2. 纪念日识别 ============
def check_anniversary(fact: dict, anchor_str: str) -> dict:
    """
    计算记忆日期相对锚定日期的纪念日状态（窗口 -3 ~ +7 天，与生产一致）
    返回 {"status": today/upcoming/just_passed/out_of_window, "years": 周年数, "days": 相对天数}
    """
    anchor = datetime.strptime(anchor_str, "%Y-%m-%d")
    date_text = f"{fact.get('time_info', '')} {fact.get('event', '')}"
    event_date = _parse_date_from_text(date_text)
    if not event_date:
        return {"status": "no_date", "years": None, "days": None}

    try:
        this_year = event_date.replace(year=anchor.year)
    except ValueError:
        return {"status": "no_date", "years": None, "days": None}

    days = (this_year - anchor).days
    if days < -3:
        return {"status": "out_of_window", "years": anchor.year - event_date.year, "days": days}
    if days < 0:
        status = "just_passed"
    elif days == 0:
        status = "today"
    else:
        status = "upcoming"
    return {"status": status, "years": anchor.year - event_date.year, "days": days}


# ============ 3. 年度回忆 ============
YEARLY_PROMPT = """
基于以下{year}年的记忆时间线，写一段温暖的年度回忆总结，300字左右。
语气亲切，像老朋友回顾这一年，突出重要事件和情感。
不要编造时间线中没有的内容。

{timeline}
"""


def run_yearly_recap(sample: dict) -> str:
    """生成年度回忆故事"""
    year = sample["year"]
    memories = sample["memories"]
    timeline = ""
    for m in sorted(memories, key=lambda x: x["date"]):
        loc = f"（{m.get('location', '')}）" if m.get("location") else ""
        timeline += f"- {m['date']} {m['event']}{loc}\n"
    prompt = YEARLY_PROMPT.format(year=year, timeline=timeline)
    resp = extract_model.invoke(prompt)
    trace_llm_call(
        model=getattr(extract_model, "model_name", "extract_model"),
        prompt=prompt, output=resp.content,
        metadata={"eval": "年度回忆", "sample": sample["sample_id"]},
    )
    return resp.content
