# -*- coding: utf-8 -*-
"""记忆抽取评测执行器：复用生产 EXTRACT_PROMPT，从视觉描述+对话抽取结构化记忆"""
import json
from services.memory_service import EXTRACT_PROMPT, extract_model
from utils.langfuse_client import trace_llm_call

EXTRACT_FIELDS = ["time_info", "location", "event", "person_relation", "emotion", "tags"]


def _clean_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:].strip()
    if content.startswith("```"):
        content = content[3:].strip()
    if content.endswith("```"):
        content = content[:-3].strip()
    return content


def run_extraction(sample: dict) -> dict:
    """执行单条记忆抽取，返回模型抽取的结构化结果"""
    photo_info = sample["photo_resource"]
    chat_history = sample["user_dialogue"]
    prompt = EXTRACT_PROMPT.format(
        photo_info=photo_info,
        chat_history=json.dumps(chat_history, ensure_ascii=False)
    )
    resp = extract_model.invoke(prompt)
    trace_llm_call(
        model=getattr(extract_model, "model_name", "extract_model"),
        prompt=prompt, output=resp.content,
        metadata={"eval": "记忆抽取", "sample": sample["sample_id"]},
    )
    result = json.loads(_clean_json(resp.content))
    # 保证 tags 是列表
    if not isinstance(result.get("tags"), list):
        result["tags"] = [result["tags"]] if result.get("tags") else []
    return result


def compare_extraction(pred: dict, standard: dict) -> dict:
    """
    字段级比对：
    - coverage_rate: 标准要求的非空字段中，模型正确给出了内容的比例（含语义一致判断交给 judge）
    - exact_rate: 六个字段硬一致率（标准为空则模型也应为空；tags 按集合相等）
    - nonempty_hit: 标准非空字段被模型非空覆盖的字段名
    - empty_hit: 标准为空字段模型也为空的字段名
    """
    std_nonempty = [f for f in EXTRACT_FIELDS if standard.get(f)]
    hit = [f for f in std_nonempty if pred.get(f)]
    coverage = (len(hit) / len(std_nonempty)) if std_nonempty else 1.0

    exact = 0
    exact_detail = {}
    for f in EXTRACT_FIELDS:
        std_val = standard.get(f)
        pred_val = pred.get(f)
        if not std_val:
            ok = not pred_val
        else:
            if f == "tags":
                ok = set(pred_val or []) == set(std_val)
            else:
                ok = str(pred_val or "").strip() == str(std_val).strip()
        exact += 1 if ok else 0
        exact_detail[f] = ok

    return {
        "coverage_rate": round(coverage, 4),
        "exact_rate": round(exact / len(EXTRACT_FIELDS), 4),
        "nonempty_hit": hit,
        "missing": [f for f in std_nonempty if not pred.get(f)],
        "exact_detail": exact_detail,
    }
