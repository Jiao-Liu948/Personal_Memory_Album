# -*- coding: utf-8 -*-
"""
记忆冲突更新评测执行器：
与生产 merge_memory_fact 决策逻辑保持一致（纯函数版，无需数据库）：
1. event 完全一致 → skip
2. embedding 余弦距离 < 0.15 → merge（语义等价）
3. 结构强匹配（时间+地点一致、标签重叠>50%、事件重合）→ merge
4. 距离 >= 0.45 → add（无关）
5. 0.15 ~ 0.45 → LLM 兜底裁决（skip/merge/archive/add）
"""
import numpy as np
from db.models import MemoryFact
from utils.embedding_client import embedding_client
from services.memory_service import (
    MERGE_SIM_THRESHOLD, LLM_SIM_THRESHOLD,
    _strong_struct_match, _llm_adjudicate, _normalize_time,
)

FACT_FIELDS = ("time_info", "location", "event", "person_relation", "emotion", "tags")


def _to_obj(d: dict) -> MemoryFact:
    return MemoryFact(**{k: v for k, v in d.items() if k in FACT_FIELDS})


def _text(d: dict) -> str:
    parts = []
    if d.get("event"):
        parts.append(d["event"])
    if d.get("person_relation"):
        parts.append(d["person_relation"])
    if d.get("location"):
        parts.append(f"地点:{d['location']}")
    if d.get("time_info"):
        parts.append(f"时间:{d['time_info']}")
    if d.get("tags"):
        parts.append("标签:" + ",".join(d["tags"]))
    return " ".join(parts)


def _cosine_distance(d1: dict, d2: dict):
    """语义向量余弦距离（与 Chroma cosine space 一致），embedding 不可用返回 None"""
    if not embedding_client.available:
        return None
    v1 = embedding_client.embed(_text(d1))
    v2 = embedding_client.embed(_text(d2))
    sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    return 1.0 - sim


def resolve_conflict(old: dict, new: dict) -> str:
    """返回决策：skip / merge / archive / add"""
    old_obj, new_obj = _to_obj(old), _to_obj(new)

    # 1) 事件完全一致，且时间不冲突（时间相同或任一为空）才算重复
    if old.get("event") and new.get("event") and old["event"].strip() == new["event"].strip():
        old_t = _normalize_time(old.get("time_info"))
        new_t = _normalize_time(new.get("time_info"))
        if not (old_t and new_t and old_t != new_t):
            return "skip"

    # 语义向量距离（embedding 不可用时为 None）
    dist = _cosine_distance(old, new)

    # 2) 极度相似 → 语义等价合并（时间都明确且不同除外）
    if dist is not None and dist < MERGE_SIM_THRESHOLD:
        old_t = _normalize_time(old.get("time_info"))
        new_t = _normalize_time(new.get("time_info"))
        if not (old_t and new_t and old_t != new_t):
            return "merge"
    # 3) 结构强匹配 → 合并
    if _strong_struct_match(old_obj, new_obj):
        return "merge"
    # 4) 几乎无关 → 新增
    if dist is not None and dist >= LLM_SIM_THRESHOLD:
        return "add"
    # 5) 0.15~0.45（或语义相似但时间冲突）→ LLM 兜底
    decision, _ = _llm_adjudicate(old_obj, new_obj)
    return decision
