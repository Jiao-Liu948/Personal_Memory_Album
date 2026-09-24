import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import MemoryFact, Photo, Person
from services.vector_service import query_similar_facts
from services.memory_service import _build_fact_content


def detect_missing_info(db: Session, photo_id: str = None, user_id: str = "default_user") -> list:
    """
    信息补全检测：扫描记忆中关键字段缺失，返回需要补全的提示
    用于在对话中主动向用户提问补全
    """
    query = db.query(MemoryFact).filter(
        MemoryFact.is_valid == True,
        MemoryFact.user_id == user_id
    )
    if photo_id:
        query = query.filter(MemoryFact.related_photo_ids.like(f'%{photo_id}%'))

    facts = query.all()
    suggestions = []

    for fact in facts:
        missing = []
        if not fact.time_info:
            missing.append("时间")
        if not fact.location:
            missing.append("地点")
        if not fact.person_relation and fact.related_person_ids:
            missing.append("人物关系")
        if not fact.emotion:
            missing.append("情感/感受")

        if missing and fact.event:
            suggestions.append({
                "fact_id": fact.fact_id,
                "event": fact.event,
                "missing_fields": missing,
                "question": f"关于「{fact.event}」，你还记得{('、'.join(missing))}吗？可以补充一下。",
                "related_photo_ids": fact.related_photo_ids or []
            })

    # 按缺失字段数量排序，缺得多的优先
    suggestions.sort(key=lambda x: len(x["missing_fields"]), reverse=True)
    return suggestions[:10]


def recommend_similar_photos(db: Session, photo_id: str, top_k: int = 5, user_id: str = "default_user") -> list:
    """
    相似照片推荐：基于当前照片的记忆内容，推荐语义相似的其他照片
    """
    # 获取当前照片的所有记忆
    facts = db.query(MemoryFact).filter(
        MemoryFact.related_photo_ids.like(f'%{photo_id}%'),
        MemoryFact.is_valid == True,
        MemoryFact.user_id == user_id
    ).all()

    if not facts:
        # 没有记忆则用视觉描述做检索
        photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
        if not photo or not photo.vision_analysis:
            return []
        query_text = photo.vision_analysis.get("description", "") or photo.vision_analysis.get("scene", "")
    else:
        # 拼接所有记忆内容作为查询
        query_text = " ".join([_build_fact_content(f) for f in facts])

    if not query_text:
        return []

    # 向量检索相似记忆
    similar = query_similar_facts(query_text, top_k=top_k + 5, user_id=user_id)

    # 关键过滤：score 是 cosine distance，越小越相似。
    # 当记忆样本很少时，Chroma 会把库中全部记忆无差别返回，
    # 必须过滤掉语义距离过大的"硬凑"结果，否则会推荐毫不相关的照片。
    RECOMMEND_MAX_DIST = 0.60
    similar = [item for item in similar if item["score"] < RECOMMEND_MAX_DIST]

    # 提取关联照片，排除当前照片
    recommended_photo_ids = []
    for item in similar:
        fact = db.query(MemoryFact).filter(MemoryFact.fact_id == item["fact_id"]).first()
        if fact and fact.related_photo_ids:
            for pid in fact.related_photo_ids:
                if pid != photo_id and pid not in recommended_photo_ids:
                    recommended_photo_ids.append(pid)

    if not recommended_photo_ids:
        return []

    # 获取照片详情
    photos = db.query(Photo).filter(
        Photo.photo_id.in_(recommended_photo_ids[:top_k]),
        Photo.is_valid == True
    ).all()

    return [
        {
            "photo_id": p.photo_id,
            "file_name": p.file_name,
            "upload_time": p.upload_time.isoformat() if p.upload_time else "",
            "image_url": f"/api/photo/image/{p.photo_id}",
            "vision": p.vision_analysis or {}
        }
        for p in photos
    ]


def _parse_date_from_text(text: str) -> datetime:
    """从文本中尝试解析日期，支持多种格式"""
    if not text:
        return None
    # 尝试常见日期格式（含 EXIF 的冒号分隔，如 2024:07:14 00:05:08）
    patterns = [
        # 完整日期：2024-07-14 / 2024/07/14 / 2024年7月14日 / 2024:07:14
        r'(\d{4})[-/:年.](\d{1,2})[-/:月.](\d{1,2})',
        # 年+月：2024年7月 / 2024-07 / 2024:07
        r'(\d{4})[-/:年.](\d{1,2})月?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3)) if len(match.groups()) >= 3 else 1
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return datetime(year, month, day)
            except (ValueError, IndexError):
                continue
    return None


def check_anniversaries(db: Session, days_ahead: int = 7, user_id: str = "default_user") -> list:
    """
    纪念日提醒：扫描所有记忆中的日期，匹配未来N天内的周年纪念日
    """
    facts = db.query(MemoryFact).filter(
        MemoryFact.is_valid == True,
        MemoryFact.user_id == user_id
    ).all()

    today = datetime.now()
    reminders = []

    for fact in facts:
        # 从time_info和event中提取日期
        date_text = f"{fact.time_info} {fact.event}"
        event_date = _parse_date_from_text(date_text)

        if event_date:
            # 计算今年的周年日
            try:
                this_year_anniversary = event_date.replace(year=today.year)
            except ValueError:
                # 2月29日等特殊日期
                continue

            days_until = (this_year_anniversary - today).days

            # 未来N天内 或 刚过去N天内（补提醒）
            if -3 <= days_until <= days_ahead:
                years_passed = today.year - event_date.year
                if days_until < 0:
                    status = "just_passed"
                    days_text = f"已过去{abs(days_until)}天"
                elif days_until == 0:
                    status = "today"
                    days_text = "就是今天"
                else:
                    status = "upcoming"
                    days_text = f"还有{days_until}天"

                reminders.append({
                    "fact_id": fact.fact_id,
                    "event": fact.event,
                    "original_date": event_date.strftime("%Y-%m-%d"),
                    "anniversary_date": this_year_anniversary.strftime("%Y-%m-%d"),
                    "years_passed": years_passed,
                    "status": status,
                    "days_text": days_text,
                    "related_photo_ids": fact.related_photo_ids or []
                })

    # 按日期远近排序
    reminders.sort(key=lambda x: abs(datetime.strptime(x["anniversary_date"], "%Y-%m-%d") - today))
    return reminders


def generate_yearly_recap(db: Session, year: int = None, user_id: str = "default_user") -> dict:
    """
    年度回忆生成：按年份筛选所有照片与记忆，生成时间线式年度总结
    """
    if year is None:
        year = datetime.now().year - 1  # 默认上一年

    # 筛选该年的记忆（通过time_info中的年份匹配）
    all_facts = db.query(MemoryFact).filter(
        MemoryFact.is_valid == True,
        MemoryFact.user_id == user_id
    ).all()

    year_facts = []
    for fact in all_facts:
        date_text = f"{fact.time_info} {fact.event}"
        event_date = _parse_date_from_text(date_text)
        if event_date and event_date.year == year:
            year_facts.append(fact)

    # 筛选该年上传的照片
    year_photos = db.query(Photo).filter(
        Photo.is_valid == True,
        Photo.user_id == user_id,
        Photo.upload_time >= datetime(year, 1, 1),
        Photo.upload_time < datetime(year + 1, 1, 1)
    ).order_by(Photo.upload_time.asc()).all()

    # 按月分组
    monthly = {}
    for fact in year_facts:
        date_text = f"{fact.time_info} {fact.event}"
        event_date = _parse_date_from_text(date_text)
        if event_date:
            month = event_date.month
            if month not in monthly:
                monthly[month] = []
            monthly[month].append({
                "fact_id": fact.fact_id,
                "event": fact.event,
                "date": event_date.strftime("%m-%d"),
                "location": fact.location,
                "tags": fact.tags or [],
                "related_photo_ids": fact.related_photo_ids or []
            })

    # 统计
    tag_count = {}
    for fact in year_facts:
        for tag in (fact.tags or []):
            tag_count[tag] = tag_count.get(tag, 0) + 1

    top_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # 生成时间线故事（用LLM）
    timeline_text = ""
    for month in sorted(monthly.keys()):
        timeline_text += f"\n{month}月:\n"
        for item in monthly[month]:
            timeline_text += f"  - {item['date']} {item['event']}"
            if item['location']:
                timeline_text += f"（{item['location']}）"
            timeline_text += "\n"

    story_prompt = f"""
    基于以下{year}年的记忆时间线，写一段温暖的年度回忆总结，300字左右。
    语气亲切，像老朋友回顾这一年，突出重要事件和情感。
    不要编造时间线中没有的内容。

    {timeline_text if timeline_text else '（这一年没有记录到结构化记忆）'}
    """

    try:
        from langchain_openai import ChatOpenAI
        from config import settings
        model = ChatOpenAI(
            model=settings.MODEL_NAME,
            api_key=settings.MODEL_API_KEY,
            base_url=settings.MODEL_BASE_URL,
            temperature=0.8,
            request_timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
        )
        response = model.invoke(story_prompt)
        story = response.content
    except Exception as e:
        story = f"年度故事生成失败: {str(e)}"

    return {
        "year": year,
        "total_memories": len(year_facts),
        "total_photos": len(year_photos),
        "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
        "monthly_timeline": {str(k): v for k, v in sorted(monthly.items())},
        "photos": [
            {
                "photo_id": p.photo_id,
                "file_name": p.file_name,
                "upload_time": p.upload_time.isoformat() if p.upload_time else "",
                "image_url": f"/api/photo/image/{p.photo_id}"
            }
            for p in year_photos
        ],
        "yearly_story": story
    }
