# -*- coding: utf-8 -*-
"""
系统概览：为影像知识管理控制台提供运行期指标。

设计原则：
    所有指标都从库里/配置里现算，不写任何静态假数据，
    保证界面上每个数字都能追溯到真实来源。

多租户维度：
    全部查询按 user_id 过滤，当前默认 default_user；
    接入团队协作时只要把 user_id 透传进来即可，无需改这里。
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from config import settings
from db.models import MemoryFact, Person, Photo
from utils.embedding_client import embedding_client
from utils.logger import logger

TIMELINE_DAYS = 7
TOP_N = 6


def _model_binding(name: str, base_url: str, api_key: str) -> dict:
    """模型端点绑定情况（供控制台展示「私有化部署」的实际指向）"""
    return {
        "name": name or "",
        "base_url": base_url or "",
        "configured": bool(name and base_url and api_key),
    }


def build_overview(db: Session, user_id: str = "default_user") -> dict:
    """汇总资产、知识、来源、模型与处理管线指标"""
    # ---------- 影像资产 ----------
    photos = db.query(Photo).filter(Photo.is_valid == True, Photo.user_id == user_id).all()
    parsed = sum(1 for p in photos if p.parse_status == "success")
    failed = sum(1 for p in photos if p.parse_status == "failed")
    pending = len(photos) - parsed - failed

    # ---------- 知识沉淀 ----------
    facts = db.query(MemoryFact).filter(
        MemoryFact.is_valid == True, MemoryFact.user_id == user_id
    ).all()
    persons = db.query(Person).filter(
        Person.is_valid == True, Person.user_id == user_id
    ).count()

    tag_counter, location_counter, source_counter = {}, {}, {}
    photo_ids_with_facts = set()
    for f in facts:
        for tag in (f.tags or []):
            tag_counter[tag] = tag_counter.get(tag, 0) + 1
        if f.location:
            location_counter[f.location] = location_counter.get(f.location, 0) + 1
        if f.source:
            source_counter[f.source] = source_counter.get(f.source, 0) + 1
        photo_ids_with_facts.update(f.related_photo_ids or [])

    top_tags = sorted(tag_counter.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    top_locations = sorted(location_counter.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]

    # ---------- 近 N 天处理量 ----------
    today = datetime.now().date()
    buckets = {(today - timedelta(days=i)).isoformat(): 0 for i in range(TIMELINE_DAYS - 1, -1, -1)}
    for p in photos:
        if p.upload_time:
            key = p.upload_time.date().isoformat()
            if key in buckets:
                buckets[key] += 1

    # ---------- 处理管线（每个阶段都挂真实计数） ----------
    pipeline = [
        {"stage": "影像入库", "value": len(photos), "unit": "张"},
        {"stage": "多模态解析", "value": parsed, "unit": "张"},
        {"stage": "人物聚类", "value": persons, "unit": "人"},
        {"stage": "记忆抽取", "value": len(facts), "unit": "条"},
    ]

    return {
        "assets": {
            "total": len(photos),
            "parsed": parsed,
            "pending": pending,
            "failed": failed,
            "parse_rate": round(parsed / len(photos) * 100, 1) if photos else 0.0,
        },
        "knowledge": {
            "persons": persons,
            "facts": len(facts),
            "tags": len(tag_counter),
            "locations": len(location_counter),
            "linked_photos": len(photo_ids_with_facts),
        },
        "sources": [
            {"source": k, "count": v}
            for k, v in sorted(source_counter.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
        "top_locations": [{"location": l, "count": c} for l, c in top_locations],
        "timeline": [{"date": d, "count": c} for d, c in buckets.items()],
        "pipeline": pipeline,
        "models": {
            "chat": _model_binding(settings.MODEL_NAME, settings.MODEL_BASE_URL, settings.MODEL_API_KEY),
            "vision": _model_binding(
                settings.VISION_MODEL_NAME, settings.VISION_MODEL_BASE_URL, settings.VISION_MODEL_API_KEY
            ),
            "embedding": _model_binding(
                settings.EMBEDDING_MODEL_NAME, settings.EMBEDDING_BASE_URL, settings.EMBEDDING_API_KEY
            ),
        },
        "capabilities": {
            # 语义检索依赖向量服务；不可用时检索会退回实体条件匹配
            "vector_search": embedding_client.available,
            "face_cluster": True,
            "proactive": True,
        },
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
