import os
import uuid
import threading
import numpy as np
import cv2
from sqlalchemy.orm import Session
from insightface.app import FaceAnalysis
from db.models import Person, Photo, MemoryFact
from config import settings
from utils.logger import logger

# 初始化人脸分析模型，首次运行会自动下载模型
face_app = FaceAnalysis(providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))

# 相似度阈值：insightface buffalo_l 模型同一个人不同照片的余弦相似度
# 通常在 0.4~0.8，0.65 偏严格会导致同一个人分裂成多个人物。
# 0.40 为官方常用阈值，在"不漏同一个人"与"不误合并不同人"之间更平衡。
SIMILARITY_THRESHOLD = 0.40

def cosine_similarity(vec1: list, vec2: list) -> float:
    """计算余弦相似度"""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

def detect_and_cluster_faces(db: Session, photo_id: str, image_path: str) -> dict:
    """检测照片人脸，自动聚类并绑定人物ID"""
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo:
        return {"status": "error", "msg": "照片不存在"}

    try:
        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            return {"status": "error", "msg": "图片读取失败"}
        
        # 人脸检测+特征提取
        faces = face_app.get(img)
        if len(faces) == 0:
            photo.face_parse_status = "success"
            db.commit()
            return {"status": "success", "face_count": 0, "persons": []}

        person_ids = []
        # 逐个人脸匹配已有库
        for face in faces:
            # 低置信度人脸过滤：检测分过低的疑似误检，不参与聚类，避免污染人物基准特征
            if face.det_score < 0.50:
                logger.info(f"跳过低置信度人脸 photo_id={photo_id} det_score={face.det_score:.3f}")
                continue

            feature = face.embedding.tolist()
            
            # 查询所有有效人物
            all_persons = db.query(Person).filter(
                Person.user_id == "default_user",
                Person.is_valid == True
            ).all()

            matched = False
            best_person = None
            best_score = 0

            for p in all_persons:
                if not p.face_feature:
                    continue
                score = cosine_similarity(feature, p.face_feature)
                if score > SIMILARITY_THRESHOLD and score > best_score:
                    best_score = score
                    best_person = p

            if best_person:
                # 匹配成功，更新特征基准值（取平均）
                avg_feature = np.mean([np.array(best_person.face_feature), np.array(feature)], axis=0).tolist()
                best_person.face_feature = avg_feature
                best_person.photo_count += 1
                person_ids.append(best_person.person_id)
                matched = True

            if not matched:
                # 新建匿名人物
                new_person = Person(
                    person_id=str(uuid.uuid4()),
                    user_id="default_user",
                    name=f"人物{len(all_persons)+1}",
                    face_feature=feature,
                    photo_count=1
                )
                db.add(new_person)
                db.flush()
                person_ids.append(new_person.person_id)

        # 绑定照片与人物关系（多对多）
        photo.persons = db.query(Person).filter(Person.person_id.in_(person_ids)).all()
        photo.face_parse_status = "success"
        db.commit()

        # 自动合并重复人物。
        # 上面的逐脸匹配每次命中都会把基准特征取平均（见 best_person.face_feature 更新），
        # 基准会持续漂移，所以「同一个人被拆成 人物1/人物2」是必然会出现的。
        # 这是数据一致性修复，属于聚类流水线自己的职责，不该交给用户手动点按钮触发。
        merged = 0
        try:
            merged = merge_similar_persons(db, threshold=SIMILARITY_THRESHOLD).get("merged", 0)
            if merged:
                logger.info(f"自动合并重复人物 photo_id={photo_id} merged={merged}")
        except Exception as e:
            # 合并失败不能影响本次照片解析结果
            logger.warning(f"自动合并人物失败（不影响本次解析）: {str(e)}")

        # 合并可能删除了本次刚建的人物，重新从库里读一遍，避免回传已失效的 person_id
        db.expire_all()
        photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
        final_persons = [
            {"person_id": p.person_id, "name": p.name}
            for p in (photo.persons if photo else [])
        ]

        return {
            "status": "success",
            "face_count": len(faces),
            "person_ids": [p["person_id"] for p in final_persons],
            "persons": final_persons,
            "merged": merged,
        }

    except Exception as e:
        photo.face_parse_status = "failed"
        db.commit()
        return {"status": "error", "msg": str(e)}

def merge_similar_persons(db: Session, threshold: float = 0.40, user_id: str = "default_user") -> dict:
    """
    合并相似度过高的人物，修复历史错误聚类（例如阈值过高导致同一人被拆成多个）。
    保留先创建的人物及其命名，把后创建人物的照片关联转移过去后删除。
    """
    persons = db.query(Person).filter(
        Person.user_id == user_id,
        Person.is_valid == True
    ).all()

    merged = 0
    i = 0
    while i < len(persons):
        p = persons[i]
        if not p.is_valid or not p.face_feature:
            i += 1
            continue
        j = i + 1
        while j < len(persons):
            q = persons[j]
            if q.is_valid and q.face_feature:
                score = cosine_similarity(p.face_feature, q.face_feature)
                if score > threshold:
                    # 转移照片关联到 p（去重）
                    for photo in list(q.photos):
                        if photo not in p.photos:
                            p.photos.append(photo)
                    p.photo_count += q.photo_count
                    # 同步更新记忆表中的关联人物ID（q → p）
                    related_facts = db.query(MemoryFact).filter(
                        MemoryFact.user_id == user_id,
                        MemoryFact.related_person_ids.like(f'%{q.person_id}%')
                    ).all()
                    for fact in related_facts:
                        ids = set(fact.related_person_ids or [])
                        ids.discard(q.person_id)
                        ids.add(p.person_id)
                        fact.related_person_ids = list(ids)
                    # 基准特征融合（取平均，避免漂移过大）
                    avg_feature = np.mean(
                        [np.array(p.face_feature), np.array(q.face_feature)],
                        axis=0
                    ).tolist()
                    p.face_feature = avg_feature
                    # 清空 q 的关联并删除
                    q.photos = []
                    db.delete(q)
                    merged += 1
                    persons.pop(j)
                    continue
            j += 1
        i += 1

    db.commit()
    return {"status": "success", "merged": merged}


def rename_person(db: Session, person_id: str, new_name: str) -> bool:
    """
    人物重命名。

    用户给的称呼是「权威标注」：它不只是改个显示名，后续检索与对话都要能用上，
    所以改名成功后异步把关联记忆里的旧称呼一并替换掉，并重建对应向量。
    同步阶段只做改名本身，传播放到后台线程，不拖慢接口响应。
    """
    person = db.query(Person).filter(Person.person_id == person_id).first()
    if not person:
        return False

    old_name = person.name or ""
    new_name = (new_name or "").strip()
    person.name = new_name
    db.commit()

    if new_name and old_name and new_name != old_name:
        threading.Thread(
            target=_propagate_person_rename,
            args=(person_id, old_name, new_name),
            daemon=True,
        ).start()
        logger.info(f"人物重命名 person_id={person_id} 「{old_name}」→「{new_name}」，已派发后台信息同步")

    return True


def _propagate_person_rename(person_id: str, old_name: str, new_name: str) -> None:
    """
    后台线程：把人物的新称呼同步到关联的事实记忆。

    只做「确定性的文本替换 + 重建向量」，不做语义改写（那是 LLM 的事，颗粒度另议）：
    - person_relation / event / source_context 中出现旧称呼的，替换为新称呼
    - 被改动的记忆重建向量，保证语义检索所用文本与库中一致
    用独立 Session，避免复用请求连接。
    """
    from db.database import SessionLocal
    from services.vector_service import upsert_fact_vector

    session = SessionLocal()
    try:
        facts = session.query(MemoryFact).filter(
            MemoryFact.related_person_ids.like(f'%{person_id}%')
        ).all()

        changed = []
        for fact in facts:
            touched = False
            for field in ("person_relation", "event", "source_context"):
                value = getattr(fact, field, None)
                if value and old_name in value:
                    setattr(fact, field, value.replace(old_name, new_name))
                    touched = True
            if touched:
                changed.append(fact)

        if not changed:
            logger.info(f"人物信息同步：无需替换 person_id={person_id} 关联记忆={len(facts)}")
            return

        session.commit()  # 先落库，再更新向量，避免向量更新了而库未提交

        vector_failed = 0
        for fact in changed:
            try:
                upsert_fact_vector(fact)
            except Exception as e:
                vector_failed += 1
                logger.warning(f"重命名后向量更新失败 fact_id={fact.fact_id}: {str(e)}")

        logger.info(
            f"人物信息同步完成 person_id={person_id} 命中记忆={len(facts)} "
            f"更新={len(changed)} 向量失败={vector_failed}"
        )
    except Exception as e:
        session.rollback()
        logger.error(f"人物信息同步失败 person_id={person_id}: {str(e)}")
    finally:
        session.close()

def get_photo_persons(db: Session, photo_id: str) -> list:
    """获取照片识别到的人物列表"""
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo:
        return []
    return [
        {
            "person_id": p.person_id,
            "name": p.name
        }
        for p in photo.persons
    ]
