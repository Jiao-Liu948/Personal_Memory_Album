from sqlalchemy.orm import Session
from db.models import MemoryFact, Photo, Person
from services.vector_service import query_similar_facts


# ==================== 融合权重配置 ====================
# (实体权重, 向量权重)
#   statistic / relation：靠人物、地点、时间、标签这类实体精确匹配，实体应该主导
#   recall            ：模糊回忆，语义更像，向量主导
#   未指定意图        ：用默认权重（/api/search/hybrid 直接调用时走这里）
DEFAULT_WEIGHTS = (0.60, 0.40)
INTENT_WEIGHTS = {
    "statistic": (0.75, 0.25),
    "relation": (0.75, 0.25),
    "recall": (0.40, 0.60),
}

# 这些意图属于普通交流，不做记忆召回：
# 省一次 embedding 调用，也避免无关记忆污染上下文
SKIP_RECALL_INTENTS = {"general"}

# 单个实体条件最多召回多少条，避免某个宽泛条件（如地点="北京"）把候选集撑爆
ENTITY_RECALL_PER_CONDITION = 50


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


def _normalize_vector_score(distance) -> float:
    """
    把向量检索的分数转成 0~1 的相似度。

    Chroma 的 cosine space 返回的是「距离」(1 - 余弦相似度)，越小越相似；
    这里换算成相似度并夹到 [0, 1]，才能和实体匹配度加权求和。
    不用 min-max：单条结果会除零，且分数变成相对当前结果集的，跨查询不可比。
    """
    if distance is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - float(distance)))


def _parse_fact_datetime(fact: dict):
    """
    从记忆里解析出可比较的日期，用于时序重排。

    memory_fact.time_info 是自由文本（"2019年国庆"、"2024:07:14 00:05:08"、"去年暑假"），
    这里复用 proactive_service 已有的多格式解析器（纪念日检测用的就是它）。

    兜底：像「2019年国庆」这种只给年份的表述，该解析器拿不到月份，
    这里退化为当年 1 月 1 日 —— 只用于排序，不用于对外展示。
    完全无时间信息的返回 None，调用方单独处理。
    """
    import re
    from datetime import datetime

    from services.proactive_service import _parse_date_from_text

    text = f"{fact.get('time_info') or ''} {fact.get('event') or ''}"
    try:
        parsed = _parse_date_from_text(text)
    except Exception:
        parsed = None
    if parsed is not None:
        return parsed

    match = re.search(r"(?:19|20)\d{2}", text)
    if match:
        return datetime(int(match.group(0)), 1, 1)
    return None


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
    """
    MySQL实体条件检索：按人物/地点/时间/标签筛选。

    注意这是「AND 硬过滤」语义：返回的每条都满足全部条件，因此没有匹配度可言。
    需要匹配度打分请用 entity_match_search。
    """
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


def entity_match_search(
    db: Session,
    person_ids: list = None,
    location: str = None,
    time_keyword: str = None,
    tags: list = None,
    user_id: str = "default_user",
    per_condition_limit: int = ENTITY_RECALL_PER_CONDITION,
) -> tuple:
    """
    实体匹配召回（打分版）。

    与 entity_filter_search 的关键区别：
        后者是 AND 硬过滤，返回的每条都满足全部条件，无法区分匹配程度；
        这里改为「按单个条件分别召回，再统计每条记忆命中了哪些条件」，
        得到 0~1 的匹配度 = 命中条件数 / 提供的条件总数。

    例：查询带 人物:小明 + 地点:北京 + 标签:旅行 三个条件，
        只命中「标签:旅行」的记忆得 1/3，三条全中的得 1.0。

    返回 (结果列表, 条件总数)。结果项 = fact dict + entity_score + matched_conditions。
    """
    facts = {}
    matched = {}

    def _collect(rows, label):
        for fact in rows:
            facts[fact.fact_id] = fact
            matched.setdefault(fact.fact_id, []).append(label)

    def _base_query():
        # 每次都必须新建 Query：filter() 是累积 AND 的，复用会把条件串起来
        return db.query(MemoryFact).filter(
            MemoryFact.is_valid == True,
            MemoryFact.user_id == user_id,
        )

    total_conditions = 0

    for pid in (person_ids or []):
        total_conditions += 1
        _collect(
            _base_query()
            .filter(MemoryFact.related_person_ids.like(f'%{pid}%'))
            .order_by(MemoryFact.update_time.desc())
            .limit(per_condition_limit)
            .all(),
            f"人物:{pid}",
        )

    if location:
        total_conditions += 1
        _collect(
            _base_query()
            .filter(MemoryFact.location.like(f'%{location}%'))
            .order_by(MemoryFact.update_time.desc())
            .limit(per_condition_limit)
            .all(),
            f"地点:{location}",
        )

    if time_keyword:
        total_conditions += 1
        _collect(
            _base_query()
            .filter(MemoryFact.time_info.like(f'%{time_keyword}%'))
            .order_by(MemoryFact.update_time.desc())
            .limit(per_condition_limit)
            .all(),
            f"时间:{time_keyword}",
        )

    for tag in (tags or []):
        total_conditions += 1
        _collect(
            _base_query()
            .filter(MemoryFact.tags.like(f'%{tag}%'))
            .order_by(MemoryFact.update_time.desc())
            .limit(per_condition_limit)
            .all(),
            f"标签:{tag}",
        )

    if total_conditions == 0:
        return [], 0

    results = []
    for fact_id, fact in facts.items():
        hits = matched.get(fact_id, [])
        item = _build_fact_dict(fact)
        item["matched_conditions"] = hits
        item["entity_score"] = round(len(hits) / total_conditions, 4)
        results.append(item)

    return results, total_conditions


def hybrid_search(
    db: Session,
    query: str = "",
    person_ids: list = None,
    location: str = None,
    time_keyword: str = None,
    tags: list = None,
    top_k: int = 15,
    user_id: str = "default_user",
    intent: str = None,
    time_order: str = None,
) -> dict:
    """
    双层召回融合检索：向量语义 + 实体匹配，按意图加权统一排序。

    相比旧版的改动：
        旧版把两个引擎的结果简单去重后「只按向量距离升序排」，
        纯实体命中的记忆没有向量分，一律被压到 999 排到最后，
        而且实体匹配的程度（命中几个条件）完全没有被量化。

        现在：
        1. 实体侧给出 0~1 匹配度（命中条件数 / 条件总数）
        2. 向量侧把 cosine 距离换算成 0~1 相似度
        3. 按意图权重算综合分统一排序；同分时实体命中多的优先，
           使 statistic / relation 这类查询里实体结果更靠前
    """
    # 普通交流不检索记忆
    if intent in SKIP_RECALL_INTENTS:
        return {
            "query": query,
            "intent": intent,
            "skipped": True,
            "total": 0,
            "vector_count": 0,
            "entity_count": 0,
            "total_conditions": 0,
            "weights": None,
            "facts": [],
            "related_photos": {},
            "related_persons": {},
        }

    entity_weight, vector_weight = INTENT_WEIGHTS.get(intent or "", DEFAULT_WEIGHTS)

    # ---------- 引擎1：向量语义（多取一些候选，供融合阶段排序，成本不变） ----------
    vector_scores = {}
    vector_items = {}
    if query and query.strip():
        for item in vector_search(db, query.strip(), top_k=top_k * 2, user_id=user_id):
            fid = item["fact_id"]
            vector_scores[fid] = _normalize_vector_score(item.get("similarity_score"))
            vector_items[fid] = item

    # ---------- 引擎2：实体匹配 ----------
    entity_items, total_conditions = entity_match_search(
        db,
        person_ids=person_ids,
        location=location,
        time_keyword=time_keyword,
        tags=tags,
        user_id=user_id,
    )
    entity_score_map = {i["fact_id"]: i["entity_score"] for i in entity_items}

    # ---------- 融合去重 ----------
    merged = {}
    for fid, item in vector_items.items():
        merged[fid] = dict(item)
    for item in entity_items:
        fid = item["fact_id"]
        if fid in merged:
            # 向量结果里补上实体命中信息
            merged[fid]["matched_conditions"] = item.get("matched_conditions", [])
        else:
            merged[fid] = dict(item)

    results = []
    for fid, item in merged.items():
        vector_score = vector_scores.get(fid, 0.0)
        entity_score = entity_score_map.get(fid, 0.0)
        item["vector_score"] = round(vector_score, 4)
        item["entity_score"] = round(entity_score, 4)
        item["entity_matched"] = entity_score > 0
        item["final_score"] = round(entity_weight * entity_score + vector_weight * vector_score, 4)
        results.append(item)

    # 综合分降序；同分时实体命中更多的优先（"实体结果优先"）
    results.sort(key=lambda x: (x["final_score"], x["entity_score"]), reverse=True)

    # 时序重排：查询问的是「第一次/最早」或「最近/上次」时，用户要的是时间维度的答案。
    #
    # 关键设计：时间只在「相关度同档」的候选之间起决定作用，绝不覆盖相关度本身。
    # 实测教训：早期版本对整个候选池按时间排序，结果「上次吃火锅是在哪家店」的正确记忆
    # 本排第 2（0.376），却被一堆 2025 年但毫不相关的记忆（0.22）靠"时间更晚"挤出了 Top-8。
    # 而「第一次一起玩」那种场景，正确答案与前几名差距只有 0.03，同档内按时序排正好能纠正。
    if time_order in ("earliest", "latest"):
        pool_size = max(top_k * 2, 8)
        pool = results[:pool_size]
        BAND = 0.05  # 相关度档宽

        ordered, i = [], 0
        while i < len(pool):
            band_key = int(pool[i]["final_score"] / BAND)
            band = []
            while i < len(pool) and int(pool[i]["final_score"] / BAND) == band_key:
                band.append(pool[i])
                i += 1

            dated, undated = [], []
            for item in band:
                dt = _parse_fact_datetime(item)
                if dt is None:
                    undated.append(item)      # 解析不出时间的排在有时序的之后
                else:
                    dated.append((dt, item))
            dated.sort(key=lambda pair: pair[0], reverse=(time_order == "latest"))
            ordered.extend(item for _, item in dated)
            ordered.extend(undated)

        results = ordered + results[pool_size:]

    top_results = results[:top_k]

    # ---------- 补充关联照片 / 人物详情（只针对最终返回的结果） ----------
    photo_ids_set = set()
    for r in top_results:
        photo_ids_set.update(r.get("related_photo_ids", []))

    photos = {}
    if photo_ids_set:
        db_photos = db.query(Photo).filter(Photo.photo_id.in_(list(photo_ids_set))).all()
        for p in db_photos:
            photos[p.photo_id] = {
                "photo_id": p.photo_id,
                "file_name": p.file_name,
                "display_name": p.display_name or "",
                "upload_time": p.upload_time.isoformat() if p.upload_time else "",
                "image_url": f"/api/photo/image/{p.photo_id}",
                "vision": p.vision_analysis or {}
            }

    person_ids_set = set()
    for r in top_results:
        person_ids_set.update(r.get("related_person_ids", []))

    persons = {}
    if person_ids_set:
        db_persons = db.query(Person).filter(Person.person_id.in_(list(person_ids_set))).all()
        for p in db_persons:
            persons[p.person_id] = {"person_id": p.person_id, "name": p.name}

    return {
        "query": query,
        "intent": intent,
        "time_order": time_order if time_order in ("earliest", "latest") else "none",
        "skipped": False,
        "total": len(results),
        "vector_count": len(vector_items),
        "entity_count": len(entity_items),
        "total_conditions": total_conditions,
        "weights": {"entity": entity_weight, "vector": vector_weight},
        "facts": top_results,
        "related_photos": photos,
        "related_persons": persons,
    }
