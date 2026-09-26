import os
from sqlalchemy.orm import Session
from db.models import Photo, MemoryFact, Person
from services.memory_service import get_photo_memory_facts


def get_photo_detail(db: Session, photo_id: str) -> dict:
    """获取照片完整详情：基础信息+EXIF+视觉解析+人物+记忆"""
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo:
        return {}

    persons = [
        {"person_id": p.person_id, "name": p.name, "photo_count": p.photo_count}
        for p in photo.persons
    ]

    facts = get_photo_memory_facts(db, photo_id)

    return {
        "photo_id": photo.photo_id,
        "file_name": photo.file_name,
        "display_name": photo.display_name or "",
        "upload_time": photo.upload_time.isoformat() if photo.upload_time else "",
        "parse_status": photo.parse_status,
        "face_parse_status": photo.face_parse_status,
        "exif_info": photo.exif_info or {},
        "vision_analysis": photo.vision_analysis or {},
        "persons": persons,
        "memory_facts": facts,
        "image_url": f"/api/photo/image/{photo.photo_id}"
    }


def rename_photo(db: Session, photo_id: str, name: str) -> bool:
    """
    设置照片的用户自定义名称。

    只写 display_name，不动 file_name（原始文件名保留，便于溯源）。
    name 传空字符串表示清除自定义名称，展示时回退到原始文件名。
    """
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo:
        return False
    photo.display_name = (name or "").strip()[:255]
    db.commit()
    return True


def get_photo_image_path(db: Session, photo_id: str) -> str:
    """根据photo_id获取图片文件路径"""
    photo = db.query(Photo).filter(Photo.photo_id == photo_id).first()
    if not photo:
        return ""
    return photo.file_path


def get_photos_by_person(db: Session, person_id: str) -> list:
    """获取某人物出现的所有照片"""
    person = db.query(Person).filter(Person.person_id == person_id).first()
    if not person:
        return []
    return [
        {
            "photo_id": p.photo_id,
            "file_name": p.file_name,
            "display_name": p.display_name or "",
            "upload_time": p.upload_time.isoformat() if p.upload_time else "",
            "image_url": f"/api/photo/image/{p.photo_id}"
        }
        for p in person.photos if p.is_valid
    ]
