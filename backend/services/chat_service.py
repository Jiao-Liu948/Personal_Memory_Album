import json
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config import settings
from db.models import Photo, EpisodeMemory
from services.memory_service import extract_memory_from_chat, get_photo_memory_facts
from utils.logger import logger

chat_model = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.MODEL_API_KEY,
    base_url=settings.MODEL_BASE_URL,
    temperature=0.7,
    request_timeout=settings.LLM_TIMEOUT,
    max_retries=settings.LLM_MAX_RETRIES,
)

# 上下文压缩阈值：历史消息超过该数量时，把早期对话压缩成摘要
MAX_HISTORY_MESSAGES = 20   # 超过 20 条（约 10 轮）触发压缩
KEEP_RECENT_MESSAGES = 12   # 压缩后保留最近 12 条


OPENING_PROMPT = """
你是用户的专属照片记忆助手。用户刚上传了一张照片，请你主动发起第一句对话，和用户聊聊这张照片。

要求：
1. 先用一句简短自然的话描述你看到的画面（挑重点，不要罗列全部细节）
2. 再提一个自然的引导问题，邀请用户讲述照片背后的故事
3. 语气亲切自然，像朋友聊天；总共 2~4 句话即可，不要用"作为AI助手"这类表述，不要用列表
4. 如果照片有明显的人物或特殊场景，可以自然地提到；如果画面比较普通，就聊聊氛围

照片信息：
- 场景：{scene}
- 画面人数：{people_count}人
- 描述：{description}
- 场景标签：{tags}
- 拍摄时间：{shoot_time}
"""


def generate_opening_message(photo: Photo, memory_facts: list = None) -> str:
    """
    生成智能体主动开场白：上传解析完成后，率先和用户聊这张照片。
    基于视觉解析 + 已抽取记忆，让 AI 主动开口引导用户讲述照片故事。
    """
    vision_info = photo.vision_analysis or {}
    exif_info = photo.exif_info or {}

    # 若有已抽取的记忆，附带一句自然引导（不直接暴露"系统识别"等字眼）
    fact_hint = ""
    if memory_facts:
        events = [f.get("event") for f in memory_facts if f.get("event")]
        if events:
            fact_hint = (
                "\n（系统已初步识别到相关线索："
                + "; ".join(events[:2])
                + "。可以自然带入对话拉近距离，但不要直接说“系统识别”这几个字）"
            )

    prompt = OPENING_PROMPT.format(
        scene=vision_info.get('scene', '未知'),
        people_count=vision_info.get('people_count', 0),
        description=vision_info.get('description', '未知'),
        tags=', '.join(vision_info.get('scene_tags', [])) or '无',
        shoot_time=exif_info.get('shoot_time', '未知'),
    ) + fact_hint

    try:
        response = chat_model.invoke(prompt)
        opening = response.content.strip()
        if not opening:
            raise ValueError("空开场白")
        return opening
    except Exception as e:
        logger.warning(f"开场白生成失败，使用回退模板: {e}")
        scene = vision_info.get('scene', '这张照片')
        desc = vision_info.get('description', '')
        base = f"我看到了一张{scene}的照片"
        if desc:
            base += f"：{desc[:40]}"
        return f"{base}。这是什么时候拍的呀？可以跟我讲讲它背后的故事吗？"


def build_chat_prompt(photo: Photo, history: list, user_query: str, summary: str = "", memory_facts: list = None) -> list:
    """构建对话上下文，幻觉抑制与早期摘要注入"""
    vision_info = photo.vision_analysis or {}
    exif_info = photo.exif_info or {}

    # 已抽取的确认记忆，注入给模型参考，增强一致性、抑制编造
    fact_text = "（暂无）"
    if memory_facts:
        fact_text = "\n".join([
            f"- {f.get('event') or '未描述'}" + (f" 地点:{f['location']}" if f.get("location") else "")
            for f in memory_facts[:5]
        ])

    system_text = f"""
你是用户的专属照片记忆助手，基于这张照片的信息、用户对话和已确认的记忆回答。

照片信息：
- 场景：{vision_info.get('scene', '未知')}
- 描述：{vision_info.get('description', '未知')}
- 拍摄时间：{exif_info.get('shoot_time', '未知')}
- 场景标签：{', '.join(vision_info.get('scene_tags', []))}

已确认的记忆事实：
{fact_text}

回答要求：
1. 只能依据上方"照片信息""记忆事实"和对话历史回答，严禁编造照片中不存在的内容
2. 用户对话中口述补充的信息可视为事实，但要说清是"你告诉我的"，不要当成照片里看得见的
3. 不确定的信息要明确说"这张照片里看不出来"，不要猜测
4. 语气自然亲切，像朋友聊天
5. 可以引导用户补充这张照片背后的故事
"""
    if summary:
        system_text += f"\n=== 早期对话摘要（仅作上下文参考）===\n{summary}\n"

    messages = [SystemMessage(content=system_text)]

    # 加载历史对话
    for msg in history:
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['content']))
        else:
            messages.append(AIMessage(content=msg['content']))

    messages.append(HumanMessage(content=user_query))
    return messages


def compress_history(episode: EpisodeMemory, history: list) -> list:
    """上下文动态压缩：历史过长时，把早期对话压成摘要，控制 token 成本"""
    if len(history) <= MAX_HISTORY_MESSAGES:
        return history

    old_part = history[:-KEEP_RECENT_MESSAGES]
    recent_part = history[-KEEP_RECENT_MESSAGES:]

    try:
        old_text = json.dumps(old_part, ensure_ascii=False)[:3000]
        resp = chat_model.invoke(
            "请把下面这段'用户与照片记忆助手'的早期对话压缩成一段简洁的中文摘要，"
            "保留关键事实、用户提到的照片故事细节和已确认的信息，200字以内：\n\n" + old_text
        )
        new_summary = resp.content.strip()
    except Exception as e:
        logger.warning(f"历史压缩失败，保留原历史: {e}")
        return history

    episode.summary = (episode.summary + "\n" + new_summary) if episode.summary else new_summary
    logger.info(f"历史压缩完成: {len(history)} 条 -> {len(recent_part)} 条")
    return recent_part


def chat_with_photo(db: Session, photo_id: str, user_query: str) -> dict:
    """和单张照片对话，返回回复并更新情景记忆"""
    # 1. 查询照片和情景记忆
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo:
        raise ValueError("照片不存在")

    episode = db.query(EpisodeMemory).filter(EpisodeMemory.photo_id == photo_id).first()
    if not episode:
        raise ValueError("情景记忆不存在")

    '''此处构建用户意图分析提示词，将用户意图拆解成关键词，在memory_fact表的tags字段进行检索，返回相关历史会话添加'''
    history = list(episode.full_chat_history or [])

    history = compress_history(episode, history)

    memory_facts = get_photo_memory_facts(db, photo_id)

    # 3. 构建prompt并调用模型
    messages = build_chat_prompt(photo, history, user_query, summary=episode.summary or "", memory_facts=memory_facts)
    response = chat_model.invoke(messages)
    ai_reply = response.content

    # 4. 更新对话历史到情景记忆
    history.append({"role": "user", "content": user_query})
    history.append({"role": "assistant", "content": ai_reply})
    episode.full_chat_history = history
    db.commit()
    logger.info(f"单照片对话完成 photo_id={photo_id} 历史消息数={len(history)}")

    try:
        extract_memory_from_chat(db, photo_id)
    except Exception as e:
        logger.error(f"记忆抽取失败: {str(e)}")

    return {
        "reply": ai_reply,
        "photo_id": photo_id
    }
