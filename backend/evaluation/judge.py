# -*- coding: utf-8 -*-
"""
LLM-as-judge 评分器（文档 7.3）
- 固定评判模型（JUDGE_MODEL，未配置回退主模型，temperature=0 保证一致性）
- 5分制：信息准确率(0-2) + 信息完整率(0-2) + 可溯源性(0-1)
- 另有年度回忆"关键事件覆盖检查"专用 judge
"""
import json
from langchain_openai import ChatOpenAI
from config import settings
from utils.logger import logger
from utils.langfuse_client import trace_llm_call

JUDGE_PROMPT = """
你是专业的记忆智能体评测裁判，严格按照标准打分，仅输出分数和简短理由。
评分维度：
1. 信息准确率（0-2分）：无错误、无幻觉、无冲突得2分，少量误差1分，严重错误0分；
2. 信息完整率（0-2分）：覆盖所有关键记忆信息得2分，缺失次要信息1分，缺失核心信息0分；
3. 可溯源性（0-1分）：所有内容均来自记忆素材得1分，存在编造0分；

总分=三项相加，满分5分。
标准参考答案：{standard}
模型输出结果：{output}
请严格输出JSON（不要多余文字）：
{{"score": 总分, "accuracy": 分项1, "completeness": 分项2, "traceability": 分项3, "reason": "简短理由"}}
"""

COVERAGE_PROMPT = """
你是记忆智能体评测裁判。检查模型生成的"年度回忆故事"是否覆盖了指定年份的关键事件。
关键事件：{events}
故事内容：{story}
请逐项判断故事中是否明确提到了每个关键事件（允许同义表述）。
请严格输出JSON：
{{"covered_events": ["被覆盖的事件"], "missing_events": ["未被覆盖的事件"], "hallucinated": true/false, "reason": "简短说明"}}
其中 hallucinated 表示故事中是否出现了关键事件列表之外的编造事件。
"""


def get_judge_model():
    """固定评判模型：优先 JUDGE_MODEL_* 配置，未配置回退主抽取模型"""
    if settings.JUDGE_MODEL_NAME:
        return ChatOpenAI(
            model=settings.JUDGE_MODEL_NAME,
            api_key=settings.JUDGE_MODEL_API_KEY or settings.MODEL_API_KEY,
            base_url=settings.JUDGE_MODEL_BASE_URL or settings.MODEL_BASE_URL,
            temperature=0,
            request_timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
        )
    from services.memory_service import extract_model
    return extract_model


def _clean_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:].strip()
    if content.startswith("```"):
        content = content[3:].strip()
    if content.endswith("```"):
        content = content[:-3].strip()
    return content


def judge_score(standard: str, output: str) -> dict:
    """5分制评分，返回分数与分项"""
    prompt = JUDGE_PROMPT.format(standard=standard, output=output)
    model = get_judge_model()
    try:
        resp = model.invoke(prompt)
        trace_llm_call(
            model=getattr(model, "model_name", "judge_model"),
            prompt=prompt, output=resp.content,
            metadata={"eval": "judge_5score", "sample": ""},
        )
        result = json.loads(_clean_json(resp.content))
        return {
            "score": float(result.get("score", 0)),
            "accuracy": float(result.get("accuracy", 0)),
            "completeness": float(result.get("completeness", 0)),
            "traceability": float(result.get("traceability", 0)),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        logger.error(f"judge 评分失败: {e}")
        return {"score": 0.0, "accuracy": 0.0, "completeness": 0.0, "traceability": 0.0, "reason": f"评分异常: {e}"}


def judge_coverage(events: list, story: str) -> dict:
    """年度回忆关键事件覆盖检查"""
    prompt = COVERAGE_PROMPT.format(events="、".join(events), story=story)
    model = get_judge_model()
    try:
        resp = model.invoke(prompt)
        trace_llm_call(
            model=getattr(model, "model_name", "judge_model"),
            prompt=prompt, output=resp.content,
            metadata={"eval": "judge_coverage", "sample": ""},
        )
        result = json.loads(_clean_json(resp.content))
        return {
            "covered_events": result.get("covered_events", []),
            "missing_events": result.get("missing_events", []),
            "hallucinated": bool(result.get("hallucinated", False)),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        logger.error(f"覆盖率 judge 失败: {e}")
        return {"covered_events": [], "missing_events": events, "hallucinated": False, "reason": f"judge异常: {e}"}
