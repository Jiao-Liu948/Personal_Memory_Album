import os
import chromadb
from config import settings
from utils.embedding_client import embedding_client

# 确保向量库目录存在
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

_chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
_collection = None


def get_collection():
    """获取或创建Chroma集合（懒加载，避免embedding未配置时报错）"""
    global _collection
    if _collection is None:
        _collection = _chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def _fact_to_document(fact) -> str:
    """将事实记忆转为用于向量化的文本"""
    parts = []
    if fact.event:
        parts.append(fact.event)
    if fact.person_relation:
        parts.append(fact.person_relation)
    if fact.location:
        parts.append(f"在{fact.location}")
    if fact.time_info:
        parts.append(f"时间:{fact.time_info}")
    if fact.emotion:
        parts.append(f"情感:{fact.emotion}")
    if fact.tags:
        parts.append("标签:" + ",".join(fact.tags))
    return " ".join(parts) if parts else fact.fact_id


def upsert_fact_vector(fact) -> bool:
    """写入/更新单条事实记忆的向量"""
    if not embedding_client.available:
        return False
    try:
        doc = _fact_to_document(fact)
        vector = embedding_client.embed(doc)
        collection = get_collection()

        metadata = {
            "fact_id": fact.fact_id,
            "user_id": fact.user_id or "default_user",
            "source": fact.source or "unknown",
            "location": fact.location or "",
            "time_info": fact.time_info or "",
            "emotion": fact.emotion or "",
        }
        # tags 和 photo_ids 转为字符串存入metadata（Chroma不支持list类型metadata）
        if fact.tags:
            metadata["tags"] = ",".join(fact.tags)
        if fact.related_photo_ids:
            metadata["photo_ids"] = ",".join(fact.related_photo_ids)
        if fact.related_person_ids:
            metadata["person_ids"] = ",".join(fact.related_person_ids)

        collection.upsert(
            ids=[fact.fact_id],
            embeddings=[vector],
            documents=[doc],
            metadatas=[metadata]
        )
        return True
    except Exception as e:
        print(f"[vector_service] upsert失败: {str(e)}")
        return False


def delete_fact_vector(fact_id: str) -> bool:
    """删除向量"""
    try:
        collection = get_collection()
        collection.delete(ids=[fact_id])
        return True
    except Exception as e:
        print(f"[vector_service] delete失败: {str(e)}")
        return False


def query_similar_facts(query_text: str, top_k: int = 10, user_id: str = "default_user") -> list:
    """语义检索：根据查询文本返回最相关的事实记忆ID列表和分数"""
    if not embedding_client.available:
        return []
    try:
        query_vector = embedding_client.embed(query_text)
        collection = get_collection()
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={"user_id": user_id}
        )
        if not results or not results["ids"] or not results["ids"][0]:
            return []
        return [
            {"fact_id": fid, "score": float(score), "document": doc}
            for fid, score, doc in zip(
                results["ids"][0],
                results["distances"][0],
                results["documents"][0]
            )
        ]
    except Exception as e:
        print(f"[vector_service] query失败: {str(e)}")
        return []


def rebuild_all_vectors(facts: list) -> dict:
    """全量重建向量库（用于数据迁移或修复）"""
    if not embedding_client.available:
        return {"status": "error", "msg": "Embedding未配置"}
    success = 0
    failed = 0
    for fact in facts:
        if upsert_fact_vector(fact):
            success += 1
        else:
            failed += 1
    return {"status": "success", "success": success, "failed": failed}
