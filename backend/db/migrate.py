# -*- coding: utf-8 -*-
"""
轻量增量迁移。

为什么需要它：
    db/init_db.py 走的是 Base.metadata.drop_all() + create_all()，
    那是「重建库」，会把已有数据全部清掉，不能用来给已存在的表加字段。

这里只做幂等的「缺列就补」，启动时自动执行，
用户不需要手动改表，也不需要重跑 init_database.bat。
"""
from sqlalchemy import inspect, text

from db.database import engine
from utils.logger import logger

# 需要确保存在的列：(表名, 列名, 建列 DDL 片段)
_REQUIRED_COLUMNS = [
    ("photo", "display_name", "VARCHAR(255) NULL COMMENT '用户自定义名称'"),
]


def ensure_schema() -> list:
    """检查并补齐缺失的列；返回本次实际新增的列（形如 photo.display_name）"""
    added = []

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
    except Exception as e:
        logger.warning(f"[迁移] 数据库结构检查失败，跳过自动迁移: {str(e)}")
        return added

    for table, column, ddl in _REQUIRED_COLUMNS:
        if table not in existing_tables:
            # 表还没建（全新环境会由 create_all 建出来），无需补列
            continue
        try:
            columns = {c["name"] for c in inspector.get_columns(table)}
            if column in columns:
                continue
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            added.append(f"{table}.{column}")
            logger.info(f"[迁移] 已新增列 {table}.{column}")
        except Exception as e:
            logger.warning(f"[迁移] 新增列 {table}.{column} 失败: {str(e)}")

    return added
