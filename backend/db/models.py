from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# 照片-人物多对多关联表
photo_person = Table(
    "photo_person",
    Base.metadata,
    Column("photo_id", String(64), ForeignKey("photo.photo_id"), primary_key=True),
    Column("person_id", String(64), ForeignKey("person.person_id"), primary_key=True)
)

class User(Base):
    __tablename__ = "user"
    id = Column(String(64), primary_key=True, comment="用户ID")
    username = Column(String(64), nullable=False, unique=True, comment="用户名")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

class Photo(Base):
    __tablename__ = "photo"
    photo_id = Column(String(64), primary_key=True, comment="照片唯一ID")
    user_id = Column(String(64), nullable=False, index=True, comment="所属用户ID")
    file_path = Column(Text, nullable=False, comment="本地文件路径")
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    upload_time = Column(DateTime, default=datetime.now, comment="上传时间")
    is_valid = Column(Boolean, default=True, comment="是否有效")
    exif_info = Column(JSON, comment="EXIF原始信息JSON")
    vision_analysis = Column(JSON, comment="多模态视觉解析结果JSON")
    parse_status = Column(String(32), default="pending", comment="解析状态:pending/success/failed")
    face_parse_status = Column(String(32), default="pending", comment="人脸解析状态")
    persons = relationship("Person", secondary=photo_person, backref="photos")

class EpisodeMemory(Base):
    __tablename__ = "episode_memory"
    episode_id = Column(String(64), primary_key=True, comment="情景记忆ID")
    photo_id = Column(String(64), nullable=False, index=True, comment="绑定照片ID")
    user_id = Column(String(64), nullable=False, index=True, comment="所属用户ID")
    full_chat_history = Column(JSON, comment="该照片完整对话历史列表")
    user_story = Column(Text, comment="用户补充的故事汇总")
    summary = Column(Text, comment="对话记忆摘要")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

class Person(Base):
    __tablename__ = "person"
    person_id = Column(String(64), primary_key=True, comment="人物唯一ID")
    user_id = Column(String(64), nullable=False, index=True, comment="所属用户ID")
    name = Column(String(64), default="", comment="人物备注名，初始为匿名")
    face_feature = Column(JSON, comment="人脸特征向量基准值")
    photo_count = Column(Integer, default=1, comment="关联照片数量")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    is_valid = Column(Boolean, default=True, comment="是否有效")

class MemoryFact(Base):
    __tablename__ = "memory_fact"
    fact_id = Column(String(64), primary_key=True, comment="事实记忆唯一ID")
    user_id = Column(String(64), nullable=False, index=True, comment="所属用户ID")
    related_photo_ids = Column(JSON, comment="关联照片ID列表")
    related_person_ids = Column(JSON, comment="关联人物ID列表")
    time_info = Column(String(255), default="", comment="结构化时间")
    location = Column(String(255), default="", comment="地点")
    event = Column(String(512), default="", comment="核心事件")
    person_relation = Column(String(255), default="", comment="人物关系描述")
    emotion = Column(String(64), default="", comment="情感标签")
    tags = Column(JSON, comment="事件标签列表")
    content_vector = Column(JSON, comment="语义向量，第三阶段填充")
    source = Column(String(32), default="vision", comment="来源:vision/chat/user_supplement")
    source_context = Column(Text, comment="原始溯源文本")
    is_valid = Column(Boolean, default=True, comment="是否有效")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    merge_count = Column(Integer, default=0, comment="累计合并次数，超过阈值触发记忆精炼")
