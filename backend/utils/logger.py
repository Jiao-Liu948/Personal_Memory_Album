# -*- coding: utf-8 -*-
"""
统一日志模块：控制台 + 按天文件双输出。
后续所有服务的可观测信息统一走这里，替代散落的 print。
"""
import logging
import os
import sys
from datetime import datetime

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def setup_logger(name: str = "app", log_dir: str = _LOG_DIR, level: int = logging.INFO):
    """配置日志：控制台 + 按天文件。同名字的 logger 只初始化一次，避免重复 handler。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出（uvicorn 窗口直接可见）
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 按天文件输出（backend/logs/app_YYYYMMDD.log）
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # 文件不可写时仅保留控制台输出
        pass

    return logger


# 全局默认 logger
logger = setup_logger()
