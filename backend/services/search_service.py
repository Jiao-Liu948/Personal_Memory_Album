from sqlalchemy.orm import Session
from db.models import MemoryFact, Photo, Person
from services.vector_service import query_similar_facts


def _build_fact_dict(fact: MemoryFact, score: float = None) -> dict:
    """将MemoryFact转为字典，附带关联照片信息"""
    result = {
        "fact_id": fact.fact_id,
        "event": fact.event,
        "time_info": fact.time_info,
        "location": fact.location,
        "person_relation": fact.person_relation,
        "emotion": fact.emotion,
        "tags": fact.tags or [],
        "source": fact.source,
        "related_photo_ids": fact.related_photo_ids or [],
        "related_person_ids": fact.related_person_ids or [],
    }
    if score is not None:
        result["similarity_score"] = score
    return result


def vector_search(db: Session, query: str, top_k: int = 10, user_id: str = "default_user") -> list:
    """纯向量语义检索"""
    results = query_similar_facts(query, top_k=top_k, user_id=user_id)
    if not results:
        return []

    fact_ids = [r["fact_id"] for r in results]
    score_map = {r["fact_id"]: r["score"] for r in results}

    facts = db.query(MemoryFact).filter(
        MemoryFact.fact_id.in_(fact_ids),
        MemoryFact.is_valid == True
    ).all()

    # 按向量检索的相似度排序
    facts.sort(key=lambda f: score_map.get(f.fact_id, 1.0))
    return [_build_fact_dict(f, score_map.get(f.fact_id)) for f in facts]


def entity_filter_search(
    db: Session,
    person_ids: list = None,
    location: str = None,
    time_keyword: str = None,
    tags: list = None,
    user_id: str = "default_user"
) -> list:
    """MySQL实体条件检索：按人物/地点/时间/标签筛选"""
    query = db.query(MemoryFact).filter(
        MemoryFact.is_valid == True,
        MemoryFact.user_id == user_id
    )

    if person_ids:
        for pid in person_ids:
            query = query.filter(MemoryFact.related_person_ids.like(f'%{pid}%'))

    if location:
        query = query.filter(MemoryFact.location.like(f'%{location}%'))

    if time_keyword:
        query = query.filter(MemoryFact.time_info.like(f'%{time_keyword}%'))

    if tags:
        for tag in tags:
            query = query.filter(MemoryFact.tags.like(f'%{tag}%'))

    facts = query.order_by(MemoryFact.update_time.desc()).all()
    return [_build_fact_dict(f) for f in facts]


def hybrid_search(
    db: Session,
    query: str = "",
    person_ids: list = None,
    location: str = None,
    time_keyword: str = None,
    tags: list = None,
    top_k: int = 15,
    user_id: str = "default_user"
) -> dict:
    """
    双引擎融合检索：向量语义 + 实体条件过滤
    返回去重合并后的结果，附带关联照片详情
    """
    vector_results = []
    entity_results = []

    # 引擎1：向量语义检索（有查询文本时）
    if query and query.strip():
        vector_results = vector_search(db, query.strip(), top_k=top_k, user_id=user_id)

    # 引擎2：实体条件过滤（有筛选条件时）
    has_filter = any([person_ids, location, time_keyword, tags])
    if has_filter:
        entity_results = entity_filter_search(
            db, person_ids=person_ids, location=location,
            time_keyword=time_keyword, tags=tags, user_id=user_id
        )

    # 融合去重
    merged = {}
    for item in vector_results:
        merged[item["fact_id"]] = item
    for item in entity_results:
        if item["fact_id"] in merged:
            # 已存在则保留向量分数，补充实体匹配标记
            merged[item["fact_id"]]["entity_matched"] = True
        else:
            item["entity_matched"] = True
            merged[item["fact_id"]] = item

    results = list(merged.values())

    # 排序：有向量分数的按分数升序（cosine distance越小越相似），无分数的排后面
    results.sort(key=lambda x: x.get("similarity_score", 999))

    # 补充关联照片详情
    photo_ids_set = set()
    for r in results:
        photo_ids_set.update(r.get("related_photo_ids", []))

    photos = {}
    if photo_ids_set:
        db_photos = db.query(Photo).filter(Photo.photo_id.in_(list(photo_ids_set))).all()
        for p in db_photos:
            photos[p.photo_id] = {
                "photo_id": p.photo_id,
                "file_name": p.file_name,
                "upload_time": p.upload_time.isoformat() if p.upload_time else "",
                "image_url": f"/api/photo/image/{p.photo_id}",
                "vision": p.vision_analysis or {}
            }

    # 补充人物名称
    person_ids_set = set()
    for r in results:
        person_ids_set.update(r.get("related_person_ids", []))

    persons = {}
    if person_ids_set:
        db_persons = db.query(Person).filter(Person.person_id.in_(list(person_ids_set))).all()
        for p in db_persons:
            persons[p.person_id] = {"person_id": p.person_id, "name": p.name}

    return {
        "query": query,
        "total": len(results),
        "vector_count": len(vector_results),
        "entity_count": len(entity_results),
        "facts": results[:top_k],
        "related_photos": photos,
        "related_persons": persons
    }
