import json
import os
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config import settings
from db.models import MemoryFact, Photo, Person
from services.search_service import hybrid_search
from utils.logger import logger

# 全局对话模型
chat_model = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.MODEL_API_KEY,
    base_url=settings.MODEL_BASE_URL,
    temperature=0.7,
    request_timeout=settings.LLM_TIMEOUT,
    max_retries=settings.LLM_MAX_RETRIES,
)

# 全局对话历史持久化文件
GLOBAL_CHAT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "global_chat.json")


def _load_global_history() -> list:
    """加载全局对话历史"""
    if os.path.exists(GLOBAL_CHAT_FILE):
        try:
            with open(GLOBAL_CHAT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_global_history(history: list):
    """保存全局对话历史"""
    os.makedirs(os.path.dirname(GLOBAL_CHAT_FILE), exist_ok=True)
    # 只保留最近50轮，避免文件过大
    history = history[-100:]
    with open(GLOBAL_CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


INTENT_PROMPT = """
你是一个问题意图解析器。根据用户的问题，判断问题类型并提取检索条件。
严格输出JSON，不要多余文字：
{{
    "intent": "recall | statistic | compare | relation | general",
    "query": "用于语义检索的核心查询词，去掉疑问词",
    "person_names": ["问题中提到的人名，没有则空数组"],
    "location": "问题中提到的地点，没有则空字符串",
    "time_keyword": "问题中提到的时间关键词，如'去年''生日''2023年'，没有则空字符串",
    "tags": ["问题中隐含的事件标签，如'旅行''聚会''生日'，没有则空数组"],
    "time_order": "earliest | latest | none。问'第一次/最早/最初'填 earliest；问'最近/上次/最后一次'填 latest；其余填 none"
}}

intent 判定规则（按顺序判断）：
1. statistic —— 统计数量（几次、多少、几个）
2. compare   —— 对比（有什么不同、变化）
3. relation  —— 人物关系（谁、和谁）
4. recall    —— 询问用户本人任何信息的回溯性问题：人物、地点、事件、物品、状态、偏好。
   **即使是现在时提问，只要问的是用户自己的情况，就属于 recall**，
   例如「我现在在哪个健身房？」「我的狗叫什么？」「我住哪儿？」。
5. general   —— 仅限与用户个人记忆完全无关的寒暄闲聊，例如「你好」「你是谁」「谢谢」。
   **拿不准时不要填 general，一律按 recall 处理。**

用户问题：{user_query}
输出JSON：
"""


def _parse_intent(user_query: str) -> dict:
    """解析用户问题意图，提取检索条件"""
    prompt = INTENT_PROMPT.format(user_query=user_query)
    try:
        response = chat_model.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        parsed = json.loads(content)
        # time_order 兜底：模型可能漏字段或给出非预期值
        if parsed.get("time_order") not in ("earliest", "latest"):
            parsed["time_order"] = "none"
        return parsed
    except Exception as e:
        logger.warning(f"[global_chat] 意图解析失败: {str(e)}")
        return {
            "intent": "recall",   # 解析失败时按 recall 处理，宁可多检索也不要漏答
            "query": user_query,
            "person_names": [],
            "location": "",
            "time_keyword": "",
            "tags": [],
            "time_order": "none",
        }


def _name_to_person_ids(db: Session, names: list) -> list:
    """根据人名模糊匹配人物ID"""
    if not names:
        return []
    person_ids = []
    for name in names:
        matched = db.query(Person).filter(
            Person.name.like(f'%{name}%'),
            Person.is_valid == True
        ).all()
        person_ids.extend([p.person_id for p in matched])
    return list(set(person_ids))


GLOBAL_CHAT_SYSTEM = """
你是用户的专属记忆管家，能够跨越多张照片和所有记忆，回答用户关于过去的问题。

回答规则：
1. **必须基于提供的记忆素材回答**。如果素材显示"未检索到相关记忆"，必须直接说明"我的记忆中没有相关记录"，严禁编造任何回忆
2. 只能引用素材中出现的照片ID和记忆内容；素材中没有的细节，哪怕看起来合理，也不能补全
3. **严禁补充素材中未明确出现的具体信息**，包括但不限于：具体年月日、照片编号、人名、地名、物品细节、事件经过、数字统计。素材里没有的就是没有，宁可回答得简洁朴素，也绝不可添油加醋
4. 回答中提到具体事件时，要自然地关联到相关照片（仅限素材中出现过的照片ID）
5. 如果素材中有多个相关记忆，要整合起来给出完整的回答
6. 语气亲切自然，像一个了解用户过去的老朋友
7. 如果用户的问题比较模糊，可以主动询问更具体的方向
8. 回答末尾可以用 [照片:照片ID] 的形式标注引用的照片，只标注素材中出现过的ID，不要自行编造ID

以下是检索到的相关记忆素材：
{memory_context}
"""


# general 意图不检索记忆，素材必然是空的。
# 若继续用上面的 prompt，模型会被"必须说没有相关记录"这条规则逼着答非所问
# （用户说"你好"会被回成"我的记忆中没有相关记录"），所以单独给一套宽松规则。
GLOBAL_CHAT_CHITCHAT_SYSTEM = """
你是用户的专属记忆管家。用户这句话不涉及回忆检索，属于普通交流。

回答规则：
1. 自然地回应用户，像老朋友一样简短亲切，一两句话即可，不要用列表
2. 不要编造任何关于用户过去的回忆、事件、人物或细节
3. 如果用户其实是想回忆某段过去，可以顺势引导他把问题问得更具体一点
   （比如带上人物、地点或时间），这样我才能去记忆里找
"""


def global_chat(db: Session, user_query: str) -> dict:
    """全局跨照片问答"""
    # 1. 意图解析
    intent_info = _parse_intent(user_query)

    # 2. 人名转人物ID
    person_ids = _name_to_person_ids(db, intent_info.get("person_names", []))

    # 3. 双引擎检索（把已解析出的意图传下去，由它决定权重、是否跳过召回、是否按时序重排）
    search_result = hybrid_search(
        db,
        query=intent_info.get("query", user_query),
        person_ids=person_ids if person_ids else None,
        location=intent_info.get("location") or None,
        time_keyword=intent_info.get("time_keyword") or None,
        tags=intent_info.get("tags") or None,
        top_k=15,
        intent=intent_info.get("intent"),
        time_order=intent_info.get("time_order"),
    )

    facts = search_result.get("facts", [])
    photos = search_result.get("related_photos", {})

    logger.info(
        f"全局问答 query={user_query!r} | intent={intent_info.get('intent')} "
        f"| 召回记忆={len(facts)} | 向量={search_result.get('vector_count', 0)} "
        f"实体={search_result.get('entity_count', 0)} "
        f"权重={search_result.get('weights')} 跳过召回={search_result.get('skipped', False)}"
    )

    # 4. 构建记忆上下文
    context_parts = []
    for i, fact in enumerate(facts, 1):
        part = f"[记忆{i}] 事件:{fact.get('event', '无')}"
        if fact.get("location"):
            part += f" | 地点:{fact['location']}"
        if fact.get("time_info"):
            part += f" | 时间:{fact['time_info']}"
        if fact.get("person_relation"):
            part += f" | 人物:{fact['person_relation']}"
        if fact.get("tags"):
            part += f" | 标签:{','.join(fact['tags'])}"
        if fact.get("related_photo_ids"):
            part += f" | 关联照片:{','.join(fact['related_photo_ids'])}"
        context_parts.append(part)

    memory_context = "\n".join(context_parts) if context_parts else "（未检索到相关记忆）"

    # 5. 加载全局对话历史
    history = _load_global_history()

    # 6. 构建prompt
    #    跳过召回的意图（general）素材必然为空，走闲聊规则，
    #    否则会被"必须说没有相关记录"的规则逼着答非所问。
    if search_result.get("skipped"):
        system_text = GLOBAL_CHAT_CHITCHAT_SYSTEM
    else:
        system_text = GLOBAL_CHAT_SYSTEM.format(memory_context=memory_context)
    messages = [SystemMessage(content=system_text)]

    for msg in history[-20:]:  # 只带最近20轮
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_query))

    # 7. 调用模型
    response = chat_model.invoke(messages)
    ai_reply = response.content

    # 8. 保存对话历史
    history.append({"role": "user", "content": user_query})
    history.append({"role": "assistant", "content": ai_reply})
    _save_global_history(history)

    return {
        "reply": ai_reply,
        "intent": intent_info.get("intent", "general"),
        "matched_facts": len(facts),
        "related_photos": list(photos.values()),
        "search_summary": {
            "vector_count": search_result.get("vector_count", 0),
            "entity_count": search_result.get("entity_count", 0),
            "total": search_result.get("total", 0),
            "weights": search_result.get("weights"),
            "skipped": search_result.get("skipped", False),
        }
    }


def get_global_history() -> list:
    """获取全局对话历史"""
    return _load_global_history()


def clear_global_history() -> dict:
    """清空全局对话历史"""
    _save_global_history([])
    return {"status": "success"}
