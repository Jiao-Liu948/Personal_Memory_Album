import uuid
import json
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from config import settings
from db.models import Photo, EpisodeMemory, MemoryFact, Person
from services.vector_service import upsert_fact_vector, delete_fact_vector, query_similar_facts
from utils.embedding_client import embedding_client
from utils.logger import logger

# 抽取专用低成本模型
extract_model = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.MODEL_API_KEY,
    base_url=settings.MODEL_BASE_URL,
    temperature=0,
    request_timeout=settings.LLM_TIMEOUT,
    max_retries=settings.LLM_MAX_RETRIES,
)

EXTRACT_PROMPT = """
你是专业的记忆抽取助手，从给定的照片信息和对话历史中，抽取结构化事实记忆。
严格按照以下JSON格式输出，不要多余文字，不要markdown代码块：
{{
    "time_info": "具体时间或模糊时间，如'2023年8月'、'去年暑假'、'生日当天'，没有则留空字符串",
    "location": "地点信息，没有则留空字符串",
    "event": "核心事件一句话描述，必须客观事实，不要主观推测",
    "person_relation": "人物关系描述，如'朋友聚会、家人出游'，没有人物则留空",
    "emotion": "情感标签，可选值：开心/感动/遗憾/平淡/其他，没有则留空",
    "tags": ["标签1", "标签2"]
}}

抽取规则（严格遵守）：
1. 只抽取【用户明确口述或照片明确可见】的事实，严禁编造、猜测、脑补
2. 用户口述的内容优先级高于照片识别内容
3. 不要把用户的疑问句、闲聊当作事件抽取
4. event 必须是一句客观描述，不要加"用户说""用户分享"这类前缀
5. 信息不足的字段一律留空字符串，不要瞎填
6. tags 最多3个，如生日、旅行、聚会、工作、日常
7. 语言简洁，控制在80字以内

=== 照片基础信息 ===
{photo_info}

=== 对话历史 ===
{chat_history}

输出JSON：
"""

VISION_EXTRACT_PROMPT = """
你是专业的记忆抽取助手，仅根据照片的视觉解析结果，抽取初始结构化事实记忆。
严格按照以下JSON格式输出，不要多余文字，不要markdown代码块：
{{
    "time_info": "",
    "location": "从场景描述中推断的地点，不确定则留空",
    "event": "基于画面内容的客观事件描述，如'多人在餐厅聚餐'，不确定则留空",
    "person_relation": "根据人数和场景推断的关系，如'朋友聚会'，不确定则留空",
    "emotion": "",
    "tags": ["从场景标签中选取，最多2个"]
}}

规则：
1. 只能基于视觉信息，严禁编造画面中没有的内容
2. 不确定的字段一律留空字符串
3. 不要添加主观推测、不要描述人物身份猜测（如'明星''老板'）
4. 如果画面信息过于简单（如单只宠物、纯风景），event 和 tags 都要如实、克制

=== 视觉解析结果 ===
{vision_info}

=== EXIF信息 ===
{exif_info}

输出JSON：
"""

# ==================== 冲突消解三层策略 ====================
# 粗筛：Chroma 语义召回，cosine 距离越小越相似
MERGE_SIM_THRESHOLD = 0.15    # 距离 < 0.15 → 极度相似，语义等价直接合并
LLM_SIM_THRESHOLD = 0.45      # 距离 >= 0.45 → 几乎无相似，无关新增；0.15~0.45 → LLM 兜底裁决
COARSE_TOP_K = 8              # 粗筛召回候选数量
TAG_OVERLAP_RATIO = 0.5       # 标签重叠率阈值（相对较小集合）
EVENT_JACCARD_FOR_MERGE = 0.3 # 时间地点标签合并规则中的"事件重合"Jaccard阈值

# 记忆精炼（防合并爆炸）
REFINE_MERGE_COUNT = 3        # 累计合并次数 > 3 触发精炼
REFINE_EVENT_LEN = 100        # event 长度超过 100 字触发精炼
REFINE_EVENT_MAX = 40         # 精炼后 event 目标长度上限

# 单张照片最多保留的有效记忆条数，超出后合并到最旧一条，避免冗余累积
MAX_FACTS_PER_PHOTO = 5


def _get_photo_person_ids(db: Session, photo_id: str) -> list:
    """获取照片关联的人物ID列表"""
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo:
        return []
    return [p.person_id for p in photo.persons]


def _build_fact_content(fact: MemoryFact) -> str:
    """构建用于向量化的文本内容"""
    parts = []
    if fact.event:
        parts.append(fact.event)
    if fact.person_relation:
        parts.append(fact.person_relation)
    if fact.location:
        parts.append(f"地点:{fact.location}")
    if fact.time_info:
        parts.append(f"时间:{fact.time_info}")
    if fact.tags:
        parts.append("标签:" + ",".join(fact.tags))
    return " ".join(parts)


def extract_memory_from_vision(db: Session, photo_id: str) -> dict:
    """上传照片后，从视觉解析结果中自动抽取初始事实记忆"""
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo or not photo.vision_analysis:
        return {"status": "skip", "msg": "无视觉解析结果"}

    vision_str = json.dumps(photo.vision_analysis or {}, ensure_ascii=False)
    exif_str = json.dumps(photo.exif_info or {}, ensure_ascii=False)

    prompt = VISION_EXTRACT_PROMPT.format(vision_info=vision_str, exif_info=exif_str)

    try:
        response = extract_model.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        result = json.loads(content)
    except Exception as e:
        return {"status": "error", "msg": f"视觉记忆抽取失败: {str(e)}"}

    if not result.get("event") and not result.get("location") and not result.get("tags"):
        return {"status": "skip", "msg": "视觉信息不足，未生成记忆"}

    person_ids = _get_photo_person_ids(db, photo_id)

    new_fact = MemoryFact(
        fact_id=str(uuid.uuid4()),
        user_id="default_user",
        related_photo_ids=[photo_id],
        related_person_ids=person_ids,
        time_info=result.get("time_info", ""),
        location=result.get("location", ""),
        event=result.get("event", ""),
        person_relation=result.get("person_relation", ""),
        emotion=result.get("emotion", ""),
        tags=result.get("tags", []),
        source="vision",
        source_context=f"视觉解析抽取: {vision_str[:200]}"
    )

    final_fact, action = merge_memory_fact(db, photo_id, new_fact)
    if action != "skip":
        db.add(final_fact)
        db.commit()
        db.refresh(final_fact)
        try:
            upsert_fact_vector(final_fact)
        except Exception as e:
            logger.warning(f"向量写入失败(视觉抽取): {str(e)}")
        # 合并后检查是否需要记忆精炼
        _maybe_trigger_refine(final_fact, action)

    return {"status": "success", "action": action, "fact_id": final_fact.fact_id}


def extract_memory_from_chat(db: Session, photo_id: str) -> dict:
    """从单张照片的对话中抽取事实记忆，并自动处理冲突合并"""
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    episode = db.query(EpisodeMemory).filter(EpisodeMemory.photo_id == photo_id).first()
    if not photo or not episode:
        return {"status": "error", "msg": "数据不存在"}

    chat_history = episode.full_chat_history or []
    if len(chat_history) < 2:
        return {"status": "skip", "msg": "对话量不足，暂不抽取"}

    photo_info_str = json.dumps(photo.vision_analysis or {}, ensure_ascii=False)
    chat_str = json.dumps(chat_history, ensure_ascii=False)

    prompt = EXTRACT_PROMPT.format(photo_info=photo_info_str, chat_history=chat_str)

    try:
        response = extract_model.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        extract_result = json.loads(content)
    except Exception as e:
        return {"status": "error", "msg": f"抽取失败: {str(e)}"}

    person_ids = _get_photo_person_ids(db, photo_id)

    new_fact = MemoryFact(
        fact_id=str(uuid.uuid4()),
        user_id="default_user",
        related_photo_ids=[photo_id],
        related_person_ids=person_ids,
        time_info=extract_result.get("time_info", ""),
        location=extract_result.get("location", ""),
        event=extract_result.get("event", ""),
        person_relation=extract_result.get("person_relation", ""),
        emotion=extract_result.get("emotion", ""),
        tags=extract_result.get("tags", []),
        source="chat",
        source_context=f"对话抽取: {chat_str[-200:]}"
    )

    final_fact, action = merge_memory_fact(db, photo_id, new_fact)
    if action != "skip":
        db.add(final_fact)
        db.commit()
        db.refresh(final_fact)
        # 同步写入向量库
        try:
            upsert_fact_vector(final_fact)
        except Exception as e:
            logger.warning(f"向量写入失败(对话抽取): {str(e)}")
        # 合并后检查是否需要记忆精炼
        _maybe_trigger_refine(final_fact, action)

    return {"status": "success", "action": action, "fact_id": final_fact.fact_id}


# ==================== 记忆精炼（防合并爆炸） ====================

REFINE_PROMPT = """
你是记忆整理助手。下面是一条事实记忆，因为被多次合并变得冗长、啰嗦、像流水账。
请把它重新凝练成一句简洁的核心事件描述。
要求：
1. 保留核心信息：人物、地点、时间、核心动作
2. 一句话表述，不超过{max_len}字
3. 去除重复、细枝末节和流水账式罗列（如"在餐厅吃饭，和Mike，点了披萨，喝了可乐"应凝练为"和朋友Mike在餐厅聚餐"）
严格输出JSON，不要多余文字：
{{"event": "凝练后的一句话核心事件"}}

原文本：
{event}
"""


def _refine_fact(event: str) -> str:
    """用 LLM 将杂糅合并文本凝练为一句话核心事件，失败返回原文"""
    if not event or not event.strip():
        return event
    try:
        prompt = REFINE_PROMPT.format(event=event, max_len=REFINE_EVENT_MAX)
        response = extract_model.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        result = json.loads(content)
        refined = (result.get("event") or "").strip()
        if refined:
            return refined
    except Exception as e:
        logger.warning(f"记忆精炼调用失败: {str(e)}")
    return event


def _maybe_trigger_refine(fact: MemoryFact, action: str) -> None:
    """合并后检查触发条件，满足则异步触发记忆精炼（不阻塞主流程）"""
    if action != "merge":
        return
    merge_count = fact.merge_count or 0
    event_len = len(fact.event or "")
    if merge_count <= REFINE_MERGE_COUNT and event_len <= REFINE_EVENT_LEN:
        return
    threading.Thread(target=_async_refine, args=(fact.fact_id,), daemon=True).start()
    logger.info(f"触发记忆精炼 fact_id={fact.fact_id} 合并次数={merge_count} 事件长度={event_len}")


def _async_refine(fact_id: str) -> None:
    """后台线程：独立Session精炼冗长记忆，避免占用请求连接"""
    from db.database import SessionLocal
    session = SessionLocal()
    try:
        fact = session.query(MemoryFact).filter(MemoryFact.fact_id == fact_id).first()
        if not fact or not fact.is_valid:
            return
        merge_count = fact.merge_count or 0
        event_len = len(fact.event or "")
        if merge_count <= REFINE_MERGE_COUNT and event_len <= REFINE_EVENT_LEN:
            return  # 主流程触发后已被处理/精炼过，跳过

        refined = _refine_fact(fact.event or "")
        if refined and refined != (fact.event or ""):
            fact.event = refined
            fact.merge_count = 0  # 精炼后重置合并计数，避免反复触发
            session.commit()
            try:
                upsert_fact_vector(fact)
            except Exception as e:
                logger.warning(f"精炼后向量更新失败: {str(e)}")
            logger.info(f"记忆精炼完成 fact_id={fact_id}: {refined}")
    except Exception as e:
        logger.error(f"记忆精炼失败 fact_id={fact_id}: {str(e)}")
    finally:
        session.close()


# ==================== 三层冲突消解 ====================

ADJUDICATE_PROMPT = """
你是记忆冲突裁决助手。判断两条"事实记忆"是否指向同一件事。
记忆A（库中已存在的记忆）：
- 事件：{a_event}
- 时间：{a_time}
- 地点：{a_location}
- 人物关系：{a_relation}
- 标签：{a_tags}
记忆B（新抽取的记忆）：
- 事件：{b_event}
- 时间：{b_time}
- 地点：{b_location}
- 人物关系：{b_relation}
- 标签：{b_tags}

请裁决记忆B应如何处理。严格输出JSON（不要多余文字、不要markdown代码块）：
{{"decision": "skip" | "add" | "merge" | "archive", "reason": "一句话说明理由"}}

decision 含义：
- "skip": B 与 A 完全重复，B 无需入库
- "add": B 是与 A 不相关的新事件，B 应作为新记忆入库
- "merge": B 与 A 指向同一件事或可互相补充，B 应合并进 A
- "archive": B 与 A 明显冲突或修正 A 的错误信息，应归档 A（置为无效）并由 B 替换

判断要点：
1. 事件语义是核心，时间/地点/人物/标签作为辅助
2. "merge"典型：A"在餐厅聚餐"与B"和朋友在餐厅吃饭点了披萨" → 合并
3. "skip"典型：A 与 B 的事件文本几乎一致（且时间一致或均无时间）
4. "archive"典型：A"去年去了北京"与B"去年去了上海"（地点矛盾）或 A 明显有误
5. 无法明确判断时，倾向 "merge"
6. **事件几乎一致但时间明确不同的（如 2023 年和 2024 年都"去北京旅行"），是两次独立事件，应判 "add"，不得合并**
"""


def _normalize_time(t: str) -> str:
    """归一化时间：去空格、统一大小写"""
    return (t or "").replace(" ", "").strip().lower()


def _normalize_location(loc: str) -> str:
    """归一化地点：去空格、统一大小写"""
    return (loc or "").replace(" ", "").strip().lower()


def _tags_overlap_ratio(old_tags: list, new_tags: list) -> float:
    """标签重叠率：交集大小 / 较小集合大小（相对更严格的度量）"""
    if not old_tags or not new_tags:
        return 0.0
    inter = set(old_tags) & set(new_tags)
    return len(inter) / min(len(old_tags), len(new_tags))


def _event_jaccard(old_event: str, new_event: str) -> float:
    """事件字符级 Jaccard 相似度"""
    if not old_event or not new_event:
        return 0.0
    old_chars = set(old_event)
    new_chars = set(new_event)
    union = old_chars | new_chars
    return (len(old_chars & new_chars) / len(union)) if union else 0.0


def _strong_struct_match(old: MemoryFact, new_fact: MemoryFact) -> bool:
    """
    结构强匹配：归一化时间+地点完全一致，且标签重叠 > 50%，且事件重合。
    满足即视为同一件事，直接合并。
    """
    if not (_normalize_time(old.time_info) == _normalize_time(new_fact.time_info)
            and _normalize_time(old.time_info)):
        return False
    if not (_normalize_location(old.location) == _normalize_location(new_fact.location)
            and _normalize_location(old.location)):
        return False
    if _tags_overlap_ratio(old.tags or [], new_fact.tags or []) <= TAG_OVERLAP_RATIO:
        return False
    if _event_jaccard(old.event, new_fact.event) <= EVENT_JACCARD_FOR_MERGE:
        return False
    return True


def _llm_adjudicate(old: MemoryFact, new_fact: MemoryFact) -> tuple:
    """LLM 兜底裁决：返回 (decision, reason)，decision ∈ skip/add/merge/archive"""
    prompt = ADJUDICATE_PROMPT.format(
        a_event=old.event or "",
        a_time=old.time_info or "",
        a_location=old.location or "",
        a_relation=old.person_relation or "",
        a_tags=",".join(old.tags or []),
        b_event=new_fact.event or "",
        b_time=new_fact.time_info or "",
        b_location=new_fact.location or "",
        b_relation=new_fact.person_relation or "",
        b_tags=",".join(new_fact.tags or []),
    )
    try:
        response = extract_model.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        result = json.loads(content)
        decision = (result.get("decision") or "").strip().lower()
        if decision not in ("skip", "add", "merge", "archive"):
            raise ValueError(f"非法裁决: {decision}")
        return decision, result.get("reason", "")
    except Exception as e:
        logger.warning(f"LLM 裁决失败，默认合并: {str(e)}")
        return "merge", "裁决异常，保守合并"


def _facts_conflict(old: MemoryFact, new_fact: MemoryFact) -> bool:
    """
    回退用：判断两条记忆是否指向同一件事（字符级）。
    判定依据：事件语义重合，或 时间/地点/标签 至少两项一致。
    """
    # 1. 事件字符级 Jaccard 相似度
    if _event_jaccard(old.event, new_fact.event) > 0.5:
        return True

    # 2. 辅助字段一致性：时间/地点/标签 至少两项相同则视为同一件事
    score = 0
    if old.time_info and new_fact.time_info and old.time_info == new_fact.time_info:
        score += 1
    if old.location and new_fact.location and old.location == new_fact.location:
        score += 1
    old_tags = set(old.tags or [])
    new_tags = set(new_fact.tags or [])
    if old_tags and new_tags and (old_tags & new_tags):
        score += 1
    return score >= 2


def _coarse_filter(db: Session, new_fact: MemoryFact):
    """
    粗筛：用新记忆文本到向量库语义召回候选。
    返回 [(old_fact, distance), ...]（按相似度升序）；embedding 不可用时返回 None（走回退）。
    """
    if not embedding_client.available:
        return None
    query_text = _build_fact_content(new_fact)
    if not query_text:
        return None
    try:
        results = query_similar_facts(query_text, top_k=COARSE_TOP_K, user_id=new_fact.user_id or "default_user")
    except Exception as e:
        logger.warning(f"向量召回失败，走回退: {str(e)}")
        return None

    candidates = []
    for r in results:
        dist = r["score"]
        # 只保留存在一定相似度的候选（< LLM_SIM_THRESHOLD），其余视为无关
        if dist >= LLM_SIM_THRESHOLD:
            continue
        old = db.query(MemoryFact).filter(
            MemoryFact.fact_id == r["fact_id"],
            MemoryFact.is_valid == True
        ).first()
        if old:
            candidates.append((old, dist))
    return sorted(candidates, key=lambda x: x[1])


def _merge_into(old: MemoryFact, new_fact: MemoryFact, keep_old_event: bool = False) -> MemoryFact:
    """
    把新记忆合并进旧记忆。
    keep_old_event=True：语义等价合并，保留旧 event（已确认更可信），只补充其他字段；
    keep_old_event=False：补充合并，event 取较长更完整的一条，随后由记忆精炼兜底防冗长。
    """
    if new_fact.time_info:
        old.time_info = new_fact.time_info
    if new_fact.location:
        old.location = new_fact.location
    if not keep_old_event:
        # 补充合并：取较长更完整的事件描述
        if new_fact.event and len(new_fact.event) > len(old.event or ""):
            old.event = new_fact.event
    elif not old.event and new_fact.event:
        old.event = new_fact.event
    if new_fact.person_relation:
        old.person_relation = new_fact.person_relation
    if new_fact.emotion:
        old.emotion = new_fact.emotion
    if new_fact.tags:
        old.tags = list(set((old.tags or []) + new_fact.tags))[:5]
    old_persons = set(old.related_person_ids or [])
    old_persons.update(new_fact.related_person_ids or [])
    old.related_person_ids = list(old_persons)
    old_photos = set(old.related_photo_ids or [])
    old_photos.update(new_fact.related_photo_ids or [])
    old.related_photo_ids = list(old_photos)
    old.source = "merged"
    old.source_context = new_fact.source_context
    old.merge_count = (old.merge_count or 0) + 1
    return old


def _no_conflict_handle(db: Session, photo_id: str, new_fact: MemoryFact) -> tuple:
    """无相似候选时的兜底：数量治理（单张照片超限合并到最旧），否则新增"""
    old_facts = db.query(MemoryFact).filter(
        MemoryFact.related_photo_ids.like(f'%{photo_id}%'),
        MemoryFact.is_valid == True,
        MemoryFact.user_id == new_fact.user_id
    ).all()
    if len(old_facts) >= MAX_FACTS_PER_PHOTO:
        oldest = min(old_facts, key=lambda x: x.create_time or datetime.min)
        logger.info(f"记忆数量达上限({MAX_FACTS_PER_PHOTO})，合并到 {oldest.fact_id}")
        return _merge_into(oldest, new_fact, keep_old_event=False), "merge"
    return new_fact, "add"


def _fallback_merge(db: Session, photo_id: str, new_fact: MemoryFact) -> tuple:
    """embedding 不可用时的回退：同照片字符级冲突判定 + 数量治理"""
    old_facts = db.query(MemoryFact).filter(
        MemoryFact.related_photo_ids.like(f'%{photo_id}%'),
        MemoryFact.is_valid == True,
        MemoryFact.user_id == new_fact.user_id
    ).all()

    for old in old_facts:
        if _facts_conflict(old, new_fact):
            return _merge_into(old, new_fact, keep_old_event=False), "merge"

    return _no_conflict_handle(db, photo_id, new_fact)


def merge_memory_fact(db: Session, photo_id: str, new_fact: MemoryFact) -> tuple:
    """
    三层冲突消解，返回 (最终记忆对象, 操作类型)。
    操作类型：add / skip / merge / archive
    - 粗筛：向量库语义召回候选（distance < 0.45）
    - 精筛：Skip / 语义等价Merge / 结构强匹配Merge / LLM兜底裁决 / 无关Add
    - 归档保留溯源：is_valid=False + 删除向量，不物理删除
    """
    # 粗筛：全局语义召回候选
    candidates = _coarse_filter(db, new_fact)

    if candidates is None:
        # embedding 不可用 → 回退到同照片字符级匹配
        return _fallback_merge(db, photo_id, new_fact)

    if not candidates:
        # 全局无相似候选 → 新增（含数量治理）
        return _no_conflict_handle(db, photo_id, new_fact)

    # 精筛：按相似度从高到低逐一判定
    llm_waiting = []
    for old, dist in candidates:
        # 1) Skip：事件完全一致，且时间不冲突（时间相同或任一为空）才算重复。
        #    若时间都明确且不同（如两次去同一地点旅行），是不同事件，不能跳过。
        if old.event and new_fact.event and old.event.strip() == new_fact.event.strip():
            old_t = _normalize_time(old.time_info)
            new_t = _normalize_time(new_fact.time_info)
            if not (old_t and new_t and old_t != new_t):
                logger.info(f"冲突消解[skip] 完全重复 fact_id={old.fact_id}")
                return old, "skip"

        # 2) Merge：极度相似（向量距离 < 0.15）→ 语义等价直接合并。
        #    例外：时间都明确且不同（如两次去同一地点旅行）→ 是不同事件，交后续判断
        if dist < MERGE_SIM_THRESHOLD:
            old_t = _normalize_time(old.time_info)
            new_t = _normalize_time(new_fact.time_info)
            if old_t and new_t and old_t != new_t:
                logger.info(f"冲突消解[time-conflict] 语义相似但时间不同，交后续判断 dist={dist:.3f}")
            else:
                logger.info(f"冲突消解[merge-语义等价] dist={dist:.3f} fact_id={old.fact_id}")
                return _merge_into(old, new_fact, keep_old_event=True), "merge"

        # 3) Merge：归一化时间+地点完全一致，且标签重叠>50%，事件重合
        if _strong_struct_match(old, new_fact):
            logger.info(f"冲突消解[merge-结构强匹配] fact_id={old.fact_id}")
            return _merge_into(old, new_fact, keep_old_event=False), "merge"

        # 4) LLM 兜底：0.15 ~ 0.45 之间无法确定
        if dist < LLM_SIM_THRESHOLD:
            llm_waiting.append((old, dist))

        # 5) dist >= 0.45：几乎无相似 → 无关，跳过该候选

    # LLM 兜底裁决：对候选中较相似的一组逐个裁决，直到得出非 add 结论
    if llm_waiting:
        for old, dist in llm_waiting:
            decision, reason = _llm_adjudicate(old, new_fact)
            logger.info(f"冲突消解[LLM裁决] decision={decision} dist={dist:.3f} reason={reason}")
            if decision == "skip":
                return old, "skip"
            if decision == "merge":
                return _merge_into(old, new_fact, keep_old_event=False), "merge"
            if decision == "archive":
                # 归档旧记忆（保留溯源，置无效）+ 删除向量，由新记忆替换
                old.is_valid = False
                old.source_context = f"{old.source_context or ''}\n[归档] 被 {new_fact.event or ''} 替换: {reason}"
                try:
                    delete_fact_vector(old.fact_id)
                except Exception as e:
                    logger.warning(f"归档向量删除失败: {str(e)}")
                logger.info(f"冲突消解[archive] 归档旧记忆 {old.fact_id}，由新记忆替换")
                return new_fact, "archive"
            # decision == "add"：与当前候选无关，继续裁决下一个候选
        # 所有候选均裁决为 add → 新增
        return _no_conflict_handle(db, photo_id, new_fact)

    # 无任何候选命中 → 新增
    return _no_conflict_handle(db, photo_id, new_fact)


def get_photo_memory_facts(db: Session, photo_id: str) -> list:
    """获取单张照片的所有有效事实记忆"""
    facts = db.query(MemoryFact).filter(
        MemoryFact.related_photo_ids.like(f'%{photo_id}%'),
        MemoryFact.is_valid == True
    ).order_by(MemoryFact.update_time.desc()).all()

    return [
        {
            "fact_id": f.fact_id,
            "event": f.event,
            "time_info": f.time_info,
            "location": f.location,
            "emotion": f.emotion,
            "tags": f.tags,
            "source": f.source,
            "person_relation": f.person_relation
        }
        for f in facts
    ]


def get_all_memory_facts(db: Session, user_id: str = "default_user") -> list:
    """获取用户所有有效事实记忆（用于全局检索）"""
    facts = db.query(MemoryFact).filter(
        MemoryFact.is_valid == True,
        MemoryFact.user_id == user_id
    ).order_by(MemoryFact.update_time.desc()).all()
    return facts
