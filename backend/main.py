import os
import uuid
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from config import settings
from db.database import get_db
from db.models import Photo, EpisodeMemory
from services.memory_service import get_photo_memory_facts, extract_memory_from_vision
from services.face_service import detect_and_cluster_faces, get_photo_persons, rename_person, merge_similar_persons
from services.vision_service import parse_exif, analyze_photo_content
from services.chat_service import chat_with_photo, generate_opening_message
from services.photo_service import get_photo_detail, get_photo_image_path, get_photos_by_person
from services.search_service import hybrid_search
from services.global_chat_service import global_chat, get_global_history, clear_global_history
from services.proactive_service import (
    detect_missing_info, recommend_similar_photos,
    check_anniversaries, generate_yearly_recap
)
from services.notification_service import list_notifications, mark_read
from services.scheduler import start_scheduler
from utils.logger import logger

app = FastAPI(title="Personal Memory Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.STORAGE_ROOT, exist_ok=True)


# ==================== 启动自检：模型端点 ====================
def _log_model_endpoints():
    """
    启动时打印实际解析到的模型端点。
    用途：.env 里少写一个 MODEL_BASE_URL，就会静默回退到 OpenAI 官方地址，
    导致对话接口 100% 失败（401 或连接超时后返回 500），这里主动暴露出来。
    """
    def _st(v):
        return "已配置" if v else "未配置"

    logger.info("模型端点自检 | 对话=%s | base_url=%s | key=%s",
                settings.MODEL_NAME, settings.MODEL_BASE_URL, _st(settings.MODEL_API_KEY))
    logger.info("模型端点自检 | 视觉=%s | base_url=%s | key=%s",
                settings.VISION_MODEL_NAME, settings.VISION_MODEL_BASE_URL, _st(settings.VISION_MODEL_API_KEY))
    logger.info("模型端点自检 | 向量=%s | base_url=%s | key=%s",
                settings.EMBEDDING_MODEL_NAME, settings.EMBEDDING_BASE_URL, _st(settings.EMBEDDING_API_KEY))

    if not os.getenv("MODEL_BASE_URL"):
        logger.warning(
            "MODEL_BASE_URL 未在 .env 中配置，已回退到默认值 %s。"
            "若对话模型使用千问/豆包等 OpenAI 兼容接口，请补上 MODEL_BASE_URL，"
            "否则 /api/chat/send、/api/global/chat 会返回 401 或长时间超时（前端表现为 500）。",
            settings.MODEL_BASE_URL,
        )
    if not settings.MODEL_API_KEY:
        logger.warning("MODEL_API_KEY 未配置，对话与记忆抽取接口不可用。")
    if not settings.VISION_MODEL_BASE_URL:
        logger.warning("VISION_MODEL_BASE_URL 未配置，照片解析接口不可用。")
    if not settings.EMBEDDING_BASE_URL or not settings.EMBEDDING_API_KEY:
        logger.warning("EMBEDDING_* 未配置，向量检索将不可用（退回实体条件检索）。")
    if settings.MODEL_BASE_URL.rstrip("/") in ("https://api.openai.com/v1", "https://api.openai.com"):
        logger.warning("当前对话模型指向 OpenAI 官方地址，若并非使用 OpenAI 官方服务，请立即修正 MODEL_BASE_URL。")


_log_model_endpoints()

# 启动主动提醒调度器（纪念日 / 年度回忆）。
# start_production.bat 用 --workers 2，多进程只会有一个真正跑起来（见 services/scheduler.py 的锁）。
start_scheduler()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "personal-memory-agent"}


@app.post("/api/photo/upload")
def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.jpg', '.jpeg', '.png', '.webp']:
        raise HTTPException(status_code=400, detail="仅支持图片格式")

    photo_id = str(uuid.uuid4())
    save_name = f"{photo_id}{file_ext}"
    save_path = os.path.normpath(os.path.join(settings.STORAGE_ROOT, save_name))

    with open(save_path, "wb") as f:
        f.write(file.file.read())

    photo = Photo(
        photo_id=photo_id,
        user_id="default_user",
        file_path=save_path,
        file_name=file.filename
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    try:
        exif_info = parse_exif(save_path)
        vision_result = analyze_photo_content(save_path)
        photo.exif_info = exif_info
        photo.vision_analysis = vision_result
        photo.parse_status = "success"

        face_result = detect_and_cluster_faces(db, photo_id, save_path)
        logger.info(f"人脸解析结果: {face_result}")

        # 从视觉解析自动抽取初始事实记忆
        try:
            vision_mem = extract_memory_from_vision(db, photo_id)
            logger.info(f"视觉记忆抽取: {vision_mem}")
        except Exception as e:
            logger.error(f"视觉记忆抽取失败: {str(e)}")

        episode = EpisodeMemory(
            episode_id=str(uuid.uuid4()),
            photo_id=photo_id,
            user_id="default_user",
            full_chat_history=[],
            user_story="",
            summary=""
        )
        db.add(episode)

        # 智能体主动发起开场白：解析完成后率先和用户聊这张照片
        try:
            memory_facts = get_photo_memory_facts(db, photo_id)
            opening = generate_opening_message(photo, memory_facts)
            episode.full_chat_history = [{"role": "assistant", "content": opening}]
            logger.info(f"主动开场白已生成 photo_id={photo_id}: {opening[:60]}")
        except Exception as e:
            logger.error(f"主动开场白生成失败: {str(e)}")

        db.commit()
    except Exception as e:
        photo.parse_status = "failed"
        db.commit()
        logger.error(f"照片解析失败: {str(e)}")

    return {
        "photo_id": photo_id,
        "file_name": file.filename,
        "parse_status": photo.parse_status,
        "vision": photo.vision_analysis
    }


@app.get("/api/photo/list")
def get_photo_list(db: Session = Depends(get_db)):
    photos = db.query(Photo).filter(
        Photo.is_valid == True,
        Photo.user_id == "default_user"
    ).order_by(Photo.upload_time.desc()).all()

    return [
        {
            "photo_id": p.photo_id,
            "file_name": p.file_name,
            "upload_time": p.upload_time.isoformat() if p.upload_time else "",
            "parse_status": p.parse_status,
            "image_url": f"/api/photo/image/{p.photo_id}"
        }
        for p in photos
    ]


@app.get("/api/photo/detail")
def get_photo_detail_api(photo_id: str, db: Session = Depends(get_db)):
    detail = get_photo_detail(db, photo_id)
    if not detail:
        raise HTTPException(status_code=404, detail="照片不存在")
    return detail


@app.get("/api/photo/image/{photo_id}")
def get_photo_image(photo_id: str, db: Session = Depends(get_db)):
    """返回照片图片文件（用于前端缩略图展示）"""
    file_path = get_photo_image_path(db, photo_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(file_path)


@app.get("/api/photo/persons")
def get_photo_persons_api(photo_id: str, db: Session = Depends(get_db)):
    persons = get_photo_persons(db, photo_id)
    return {"photo_id": photo_id, "persons": persons}


@app.get("/api/person/photos")
def get_person_photos_api(person_id: str, db: Session = Depends(get_db)):
    photos = get_photos_by_person(db, person_id)
    return {"person_id": person_id, "photos": photos}


@app.put("/api/person/rename")
def rename_person_api(person_id: str, name: str, db: Session = Depends(get_db)):
    success = rename_person(db, person_id, name)
    if not success:
        raise HTTPException(status_code=404, detail="人物不存在")
    return {"status": "success", "person_id": person_id, "name": name}


@app.post("/api/person/merge-similar")
def merge_similar_persons_api(db: Session = Depends(get_db)):
    """合并相似度过高的人物，修复历史错误聚类"""
    result = merge_similar_persons(db)
    return result


# ==================== 单照片对话 ====================

@app.post("/api/chat/send")
def send_chat(photo_id: str, query: str, db: Session = Depends(get_db)):
    try:
        result = chat_with_photo(db, photo_id, query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history")
def get_chat_history(photo_id: str, db: Session = Depends(get_db)):
    episode = db.query(EpisodeMemory).filter(EpisodeMemory.photo_id == photo_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"photo_id": photo_id, "history": episode.full_chat_history or []}


@app.get("/api/memory/photo")
def get_photo_memory(photo_id: str, db: Session = Depends(get_db)):
    facts = get_photo_memory_facts(db, photo_id)
    return {"photo_id": photo_id, "facts": facts}


# ==================== 阶段3：全局搜索 ====================

@app.post("/api/search/hybrid")
def hybrid_search_api(
    query: str = "",
    person_ids: str = "",
    location: str = "",
    time_keyword: str = "",
    tags: str = "",
    top_k: int = 15,
    db: Session = Depends(get_db)
):
    """双引擎融合搜索：向量语义 + 实体条件过滤"""
    pid_list = [p.strip() for p in person_ids.split(",") if p.strip()] if person_ids else None
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    result = hybrid_search(
        db,
        query=query,
        person_ids=pid_list,
        location=location or None,
        time_keyword=time_keyword or None,
        tags=tag_list,
        top_k=top_k
    )
    return result


# ==================== 阶段3：全局跨照片问答 ====================

@app.post("/api/global/chat")
def global_chat_api(query: str, db: Session = Depends(get_db)):
    """全局跨照片问答入口"""
    if not query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    try:
        result = global_chat(db, query.strip())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/global/history")
def get_global_chat_history_api():
    """获取全局对话历史"""
    return {"history": get_global_history()}


@app.delete("/api/global/history")
def clear_global_chat_history_api():
    """清空全局对话历史"""
    return clear_global_history()


# ==================== 阶段3：主动交互能力 ====================

@app.get("/api/proactive/missing-info")
def proactive_missing_info_api(
    photo_id: str = "",
    db: Session = Depends(get_db)
):
    """信息补全检测：返回需要用户补充的记忆提示"""
    result = detect_missing_info(db, photo_id=photo_id or None)
    return {"suggestions": result}


@app.get("/api/proactive/similar-photos")
def proactive_similar_photos_api(
    photo_id: str,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    """相似照片推荐"""
    if not photo_id:
        raise HTTPException(status_code=400, detail="photo_id不能为空")
    result = recommend_similar_photos(db, photo_id, top_k=top_k)
    return {"photo_id": photo_id, "recommendations": result}


@app.get("/api/proactive/anniversaries")
def proactive_anniversaries_api(
    days_ahead: int = 7,
    db: Session = Depends(get_db)
):
    """纪念日提醒"""
    result = check_anniversaries(db, days_ahead=days_ahead)
    return {"reminders": result, "days_ahead": days_ahead}


@app.post("/api/proactive/yearly-recap")
def proactive_yearly_recap_api(
    year: int = None,
    db: Session = Depends(get_db)
):
    """年度回忆生成（即时生成，调试用；正式提醒走调度器预生成 + 通知）"""
    result = generate_yearly_recap(db, year=year)
    return result


# ==================== 主动提醒通知 ====================
# 触发与判定全部在后端（见 services/scheduler.py），这里只提供只读展示通道：
# 读未读通知 → 前端显示红点 → 点击弹窗。前端不提供任何「生成/触发」入口。

@app.get("/api/proactive/notifications")
def get_notifications_api(unread_only: bool = False):
    """读取主动提醒（纪念日 / 年度回忆），供前端红点与弹窗展示"""
    return list_notifications(unread_only=unread_only)


@app.post("/api/proactive/notifications/read")
def read_notifications_api(ids: str = ""):
    """标记通知已读；ids 为空表示全部已读（多个用逗号分隔）"""
    id_list = [i.strip() for i in ids.split(",") if i.strip()] if ids else None
    return mark_read(id_list)


# ============================================================
# 评测体系端点：POST /api/eval/run 触发评测（合成数据集，非真实测评），后台运行
# ============================================================
import threading
from datetime import datetime as _dt

_eval_state = {
    "status": "idle",          # idle / running / done / error
    "started_at": None,
    "finished_at": None,
    "dimension": None,         # 本次评测范围：None=全量
    "summary": None,           # 总体指标摘要
    "reports": None,           # {"md": path, "json": path}
    "message": "",
}
_eval_lock = threading.Lock()


def _extract_summary(res: dict) -> dict:
    """从评测结果中提取总体指标摘要（供端点快速返回）"""
    ex, cf, rs, pa = res["extract"], res["conflict"], res["reason"], res["proactive"]
    mi, an, yr = pa.get("missing_info", {}), pa.get("anniversary", {}), pa.get("yearly_recap", {})
    yr_rows = yr.get("rows", [])
    summary = {
        "记忆抽取": {
            "样本数": ex.get("total", 0),
            "字段覆盖": round((ex.get("avg_coverage") or 0) * 100, 2),
            "硬一致": round((ex.get("avg_exact") or 0) * 100, 2),
            "Judge": ex.get("avg_judge"),
        },
        "冲突更新": {
            "样本数": cf.get("total", 0),
            "决策准确率": round((cf.get("accuracy") or 0) * 100, 2),
            "决策分布": cf.get("decision_stat", {}),
        },
        "跨照片推理": {
            "样本数": rs.get("total", 0),
            "Judge": rs.get("avg_judge"),
        },
        "主动交互": {
            "信息补全": f"{mi.get('correct', 0)}/{mi.get('total', 0)}",
            "纪念日识别": f"{an.get('correct', 0)}/{an.get('total', 0)}",
            "年度覆盖": round((yr.get("avg_coverage") or 0) * 100, 2) if yr.get("avg_coverage") is not None else None,
            "年度样本": len(yr_rows),
        },
    }
    return summary


def _run_eval_background(dimension: str = None):
    """后台执行评测（合成数据集），结果写入全局 _eval_state"""
    from evaluation.runner import run_all_evaluation, run_dimension_eval, build_report, save_reports
    try:
        if dimension:
            res = run_dimension_eval(dimension, judge_enabled=True)
        else:
            res = run_all_evaluation(judge_enabled=True)
        md_text = build_report(res)
        paths = save_reports(res)
        with _eval_lock:
            _eval_state.update(
                status="done",
                finished_at=_dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                summary=_extract_summary(res),
                reports=paths,
                message="评测完成",
            )
        logger.info(f"[评测] 完成，报告：{paths['md']}")
    except Exception as e:
        logger.error(f"[评测] 失败: {e}")
        with _eval_lock:
            _eval_state.update(status="error", finished_at=_dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                               summary=None, reports=None, message=f"评测失败: {e}")


@app.post("/api/eval/run")
def run_evaluation_api(
    dimension: str = Query(None, description="可选维度：记忆抽取/冲突更新/跨照片推理/主动交互；不传则全量80条")
):
    """触发评测（后台运行，耗时较长），立即返回任务状态"""
    if dimension and dimension not in ["记忆抽取", "冲突更新", "跨照片推理", "主动交互"]:
        raise HTTPException(status_code=400, detail="dimension 仅支持：记忆抽取/冲突更新/跨照片推理/主动交互")
    with _eval_lock:
        if _eval_state["status"] == "running":
            return {"status": "running", "message": "评测已在运行中，请查询 /api/eval/status",
                    "started_at": _eval_state["started_at"], "dimension": _eval_state["dimension"]}
        _eval_state.update(status="running",
                           started_at=_dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                           finished_at=None, dimension=dimension,
                           summary=None, reports=None, message="")
    t = threading.Thread(target=_run_eval_background, kwargs={"dimension": dimension}, daemon=True)
    t.start()
    return {"status": "started",
            "message": "评测已启动（后台运行），请通过 GET /api/eval/status 查询进度",
            "started_at": _eval_state["started_at"], "dimension": dimension}


@app.get("/api/eval/status")
def eval_status_api():
    """查询最近一次评测状态与结果摘要"""
    with _eval_lock:
        return dict(_eval_state)
