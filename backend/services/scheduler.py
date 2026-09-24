# -*- coding: utf-8 -*-
"""
主动提醒调度器。

职责：在后台按固定间隔判定「此刻是否该主动提醒用户」，判定通过就写入通知中心。
前端不参与触发，只负责把通知显示成红点/弹窗。

两类提醒：
1. 纪念日   —— 规则匹配，无模型调用，每次调度都可以跑
2. 年度回忆 —— 需要调用 LLM 生成故事，因此在这里「预生成并缓存」，
               一年只生成一次；前端只读取成品，避免用户每点一次就烧一次 token

实现说明：
- 用轻量守护线程，不引入 APScheduler 等额外依赖（requirements.txt 里没有）
- start_production.bat 用 --workers 2，多进程会各起一个线程导致重复提醒，
  因此用「原子创建 + 陈旧超时」的锁文件保证同一时刻只有一个调度器在跑
"""
import json
import os
import atexit
import random
import threading
import time
from datetime import datetime

from db.database import SessionLocal
from services.notification_service import has_notification, push_notification
from services.proactive_service import check_anniversaries, generate_yearly_recap
from utils.logger import logger

CHECK_INTERVAL_SECONDS = 6 * 3600      # 每 6 小时检查一次
ANNIVERSARY_DAYS_AHEAD = 7             # 纪念日提醒窗口
FIRST_RUN_DELAY_SECONDS = 20           # 启动后稍等再首跑，避免和启动流程抢资源
LOCK_STALE_SECONDS = CHECK_INTERVAL_SECONDS * 2 + 3600   # 锁过期时间（含余量）

LOCK_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "storage", ".scheduler.lock"
)


# ==================== 单实例锁 ====================

def _acquire_singleton() -> bool:
    """
    只让一个进程运行调度器。

    用 os.open(..., O_CREAT | O_EXCL) 原子创建锁文件，避免并发创建；
    锁文件 mtime 作为心跳，超过 LOCK_STALE_SECONDS 视为上次异常退出的陈旧锁，可被接管。
    """
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)

    if os.path.exists(LOCK_FILE):
        try:
            if time.time() - os.path.getmtime(LOCK_FILE) < LOCK_STALE_SECONDS:
                return False          # 已有活跃调度器
            os.remove(LOCK_FILE)      # 陈旧锁，清理后重试
        except OSError:
            return False

    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _heartbeat() -> None:
    """刷新锁文件 mtime，表示调度器仍活着"""
    try:
        os.utime(LOCK_FILE, None)
    except OSError:
        pass


def _release_singleton() -> None:
    """进程正常退出时释放锁，避免残留锁挡住下一次启动（异常退出由陈旧超时兜底）"""
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass


# ==================== 各类提醒判定 ====================

def _check_anniversaries(db) -> int:
    """纪念日提醒：同一条记忆的同一周年只提醒一次"""
    pushed = 0
    for reminder in check_anniversaries(db, days_ahead=ANNIVERSARY_DAYS_AHEAD):
        key = f"anniversary:{reminder['fact_id']}:{reminder['anniversary_date']}"
        if push_notification(
            n_type="anniversary",
            title=f"🎂 {reminder['event'] or '纪念日'} · {reminder['years_passed']} 周年",
            body=f"{reminder['days_text']}（{reminder['anniversary_date']}，原日期 {reminder['original_date']}）",
            payload=reminder,
            dedup_key=key,
        ):
            pushed += 1
    return pushed


def _check_yearly_recap(db) -> int:
    """
    年度回忆：为上一年度预生成故事并推送，同一年度只推一次。

    生成失败（模型不可用等）时不推送，留给下一轮调度重试，
    避免把一条「生成失败」的通知塞给用户。
    """
    target_year = datetime.now().year - 1
    key = f"yearly_recap:{target_year}"

    if has_notification(key):
        return 0

    recap = generate_yearly_recap(db, year=target_year)

    if not recap.get("total_photos") and not recap.get("total_memories"):
        return 0  # 该年度没有任何素材，不打扰用户

    story = (recap.get("yearly_story") or "").strip()
    if not story or story.startswith("年度故事生成失败"):
        logger.warning(f"[主动提醒] {target_year} 年度故事生成失败，本轮不推送，等待下次重试")
        return 0

    body = story[:120] + ("…" if len(story) > 120 else "")
    pushed = push_notification(
        n_type="yearly_recap",
        title=f"📅 {target_year} 年度回忆",
        body=body,
        payload=recap,
        dedup_key=key,
    )
    return 1 if pushed else 0


def run_once() -> dict:
    """执行一轮判定（也可手动调用用于调试）"""
    db = SessionLocal()
    try:
        anniversaries = _check_anniversaries(db)
        recap = _check_yearly_recap(db)
        result = {"anniversary": anniversaries, "yearly_recap": recap}
        if anniversaries or recap:
            logger.info(f"[主动提醒] 本轮新增通知 {result}")
        return result
    except Exception as e:
        logger.error(f"[主动提醒] 判定失败: {str(e)}")
        return {"anniversary": 0, "yearly_recap": 0, "error": str(e)}
    finally:
        db.close()


def _loop() -> None:
    # 加一点随机抖动，进一步降低多 worker 同时命中的概率
    time.sleep(FIRST_RUN_DELAY_SECONDS + random.uniform(0, 10))
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error(f"[主动提醒] 调度异常: {str(e)}")
        finally:
            _heartbeat()
        time.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler() -> bool:
    """启动调度线程；若已有调度器在运行则跳过（多 worker 场景）"""
    if not _acquire_singleton():
        logger.info("主动提醒调度器已由其它进程启动，本进程跳过")
        return False
    atexit.register(_release_singleton)
    threading.Thread(target=_loop, daemon=True, name="proactive-scheduler").start()
    logger.info(f"主动提醒调度器已启动（每 {CHECK_INTERVAL_SECONDS // 3600} 小时检查一次）")
    return True
