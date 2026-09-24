# -*- coding: utf-8 -*-
"""
Langfuse 观测埋点（可观测性，非业务必需）。

设计原则：
    埋点是"旁路"，绝对不能反过来影响业务或评测主流程。
    所以这里做两件事：
    1) 兼容不同版本的 Langfuse API（4.x 移除了 Langfuse.generation）
    2) 任何异常一律吞掉并记 warning，最坏情况只是没有埋点数据

调用方全部在 evaluation/ 目录下（评测流程），生产链路不依赖本模块。
"""
from langfuse import Langfuse

from config import settings
from utils.logger import logger


def _build_client():
    """按需创建客户端；未配置或初始化失败时返回 None（等于关闭埋点）"""
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.info("Langfuse 未配置 public/secret key，已关闭链路埋点")
        return None
    try:
        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST or None,
        )
    except Exception as e:
        logger.warning(f"Langfuse 客户端初始化失败，已关闭链路埋点: {str(e)}")
        return None


langfuse_client = _build_client()


def trace_llm_call(model: str, prompt: str, output: str, metadata: dict = None):
    """
    记录一次 LLM 调用。

    - Langfuse 3.x / 旧版：使用 client.generation(...)
    - Langfuse 4.x：generation 已被移除，改用 start_observation(as_type="generation")
    - 都不支持，或调用出错：只记日志，不影响调用方
    """
    if langfuse_client is None:
        return

    meta = metadata or {}
    try:
        # 旧版 API
        generation = getattr(langfuse_client, "generation", None)
        if callable(generation):
            generation(name="llm_call", model=model, input=prompt, output=output, metadata=meta)
            return

        # Langfuse 4.x
        start_observation = getattr(langfuse_client, "start_observation", None)
        if callable(start_observation):
            observation = start_observation(
                name="llm_call",
                as_type="generation",
                model=model,
                input=prompt,
                output=output,
                metadata=meta,
            )
            # 新版的 observation 需要显式结束才会被提交
            end = getattr(observation, "end", None)
            if callable(end):
                end()
            return

        logger.warning("当前 Langfuse 客户端不支持 generation / start_observation，跳过埋点")
    except Exception as e:
        # 埋点失败绝不能影响业务与评测
        logger.warning(f"Langfuse 埋点失败（已忽略）: {str(e)}")
