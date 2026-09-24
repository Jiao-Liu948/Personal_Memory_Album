# -*- coding: utf-8 -*-
"""
主动提醒通知中心。

职责边界（重要）：
    触发与判定全部在后端（由 scheduler 按事件/时间驱动），
    前端只是「被动展示位」——读未读通知、显示红点、点击弹窗。
    前端不提供任何「生成/触发」按钮，否则会把该自动发生的事变成用户负担。

存储：storage/notifications.json（与 global_chat.json 同级的轻量持久化，无需建表）
"""
import json
import os
import uuid
from datetime import datetime

from utils.logger import logger

NOTIFY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "storage", "notifications.json"
)

MAX_KEEP = 200  # 最多保留条数，超出丢弃最旧的


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load() -> list:
    if os.path.exists(NOTIFY_FILE):
        try:
            with open(NOTIFY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"读取通知文件失败，按空处理: {str(e)}")
    return []


def _save(items: list) -> None:
    os.makedirs(os.path.dirname(NOTIFY_FILE), exist_ok=True)
    with open(NOTIFY_FILE, "w", encoding="utf-8") as f:
        json.dump(items[-MAX_KEEP:], f, ensure_ascii=False, indent=2)


def has_notification(dedup_key: str) -> bool:
    """幂等判断：用于「生成成本高的通知」在生成前先检查，避免重复调用模型"""
    if not dedup_key:
        return False
    return any(i.get("dedup_key") == dedup_key for i in _load())


def push_notification(
    n_type: str,
    title: str,
    body: str,
    payload: dict = None,
    dedup_key: str = None,
) -> bool:
    """
    写入一条通知。

    dedup_key 用于幂等：同一个事件（如某条记忆的某一年周年、某个年度的回忆）
    只推一次，避免每次调度都重复提醒。返回是否真正新增。
    """
    items = _load()
    if dedup_key and any(i.get("dedup_key") == dedup_key for i in items):
        return False

    items.append({
        "id": str(uuid.uuid4()),
        "type": n_type,
        "title": title,
        "body": body,
        "payload": payload or {},
        "dedup_key": dedup_key or "",
        "created_at": _now(),
        "read": False,
    })
    _save(items)
    logger.info(f"推送主动提醒 type={n_type} title={title}")
    return True


def list_notifications(unread_only: bool = False) -> dict:
    """读取通知列表（最新的在前）+ 未读数，供前端红点/弹窗使用"""
    items = _load()
    visible = [i for i in items if not i.get("read")] if unread_only else items
    return {
        "notifications": list(reversed(visible)),
        "unread_count": sum(1 for i in items if not i.get("read")),
        "total": len(items),
    }


def mark_read(ids: list = None) -> dict:
    """标记已读；ids 为空表示全部标记已读"""
    items = _load()
    changed = 0
    for item in items:
        if item.get("read"):
            continue
        if not ids or item.get("id") in ids:
            item["read"] = True
            changed += 1
    if changed:
        _save(items)
    return {"status": "success", "read": changed}
