# -*- coding: utf-8 -*-
"""
跨照片推理评测执行器：
将样本提供的记忆素材按全局问答上下文格式注入，复用 GLOBAL_CHAT_SYSTEM，
调用主对话模型回答，交由 judge 按标准答案打分（准确/完整/可溯源/无幻觉）。
"""
from langchain_core.messages import HumanMessage, SystemMessage
from services.global_chat_service import GLOBAL_CHAT_SYSTEM, chat_model
from utils.langfuse_client import trace_llm_call


def format_materials(materials: list) -> str:
    """把素材列表格式化为与 global_chat 一致的记忆上下文"""
    parts = []
    for i, m in enumerate(materials, 1):
        parts.append(f"[记忆{i}] {m}")
    return "\n".join(parts)


def run_reasoning(sample: dict) -> str:
    """执行单条跨照片推理，返回模型回答文本"""
    context = format_materials(sample["memory_materials"])
    system = GLOBAL_CHAT_SYSTEM.format(memory_context=context)
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=sample["query"]),
    ]
    resp = chat_model.invoke(messages)
    trace_llm_call(
        model=getattr(chat_model, "model_name", "chat_model"),
        prompt=system + "\n" + sample["query"], output=resp.content,
        metadata={"eval": "跨照片推理", "sample": sample["sample_id"]},
    )
    return resp.content
