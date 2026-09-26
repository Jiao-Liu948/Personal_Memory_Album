# -*- coding: utf-8 -*-
"""
三项关键指标的可复现度量工具。

用法（在 backend 目录下执行）：
    python -m evaluation.measure_metrics            # 跑全部三项
    python -m evaluation.measure_metrics token      # 仅上下文压缩 Token 节省率
    python -m evaluation.measure_metrics face       # 仅人脸聚类质量
    python -m evaluation.measure_metrics recall     # 仅 Top-K 检索召回率

三项指标各自的度量口径与方法学限制，见对应函数的 docstring。
所有数字均为实测值，不含预置数据。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import itertools
import json
import re

# ============================================================================
# 指标③：上下文压缩的 Token 节省率
# ============================================================================

def measure_token(rounds_list=(8, 11, 20, 30, 50)) -> dict:
    """
    度量口径：
        构造 N 轮多轮对话 → 调用生产环境的 chat_service.compress_history
        → 对比「压缩前全量历史」与「压缩后（摘要 + 保留的近期消息）」的 Token 数。
        Token 计数用 tiktoken(cl100k_base)，与主流模型分词口径一致。

    限制：
        节省率与「单条消息长度」强相关，不是一个固定常数；
        因此分档报告（短对话不触发压缩，长对话节省率更高）。
    """
    import tiktoken
    from db.models import EpisodeMemory
    from services.chat_service import (
        KEEP_RECENT_MESSAGES, MAX_HISTORY_MESSAGES, compress_history,
    )

    enc = tiktoken.get_encoding("cl100k_base")

    def count(messages):
        return sum(len(enc.encode(m.get("content") or "")) for m in messages)

    def make_history(rounds):
        history = []
        for i in range(rounds):
            history.append({"role": "user", "content": (
                f"第{i + 1}轮：这张是{i + 1}月初在海边拍的，那天我和几个大学同学一起过去，"
                f"天气很好，我们在沙滩上待到傍晚，还一起吃了烧烤，聊了很多以前的事。")})
            history.append({"role": "assistant", "content": (
                f"记录下来了：{i + 1}月初的海边之行，同行的是大学同学，傍晚在沙滩吃烧烤。"
                f"这段回忆的关键信息我已经抽取成结构化记忆，需要我再补充什么细节吗？")})
        return history

    print("=" * 78)
    print("指标③ 上下文压缩 Token 节省率")
    print(f"触发阈值：历史 > {MAX_HISTORY_MESSAGES} 条；压缩后保留最近 {KEEP_RECENT_MESSAGES} 条 + 摘要")
    print("=" * 78)
    print(f"{'轮数':<6}{'消息条数':<10}{'压缩前':<10}{'压缩后':<10}{'节省':<10}{'触发'}")
    print("-" * 78)

    rows = []
    for rounds in rounds_list:
        history = make_history(rounds)
        before = count(history)
        episode = EpisodeMemory(episode_id=f"m-{rounds}", photo_id="m", user_id="m",
                                full_chat_history=[], user_story="", summary="")
        compressed = compress_history(episode, history)
        after = count(compressed) + len(enc.encode(episode.summary or ""))
        triggered = len(history) > MAX_HISTORY_MESSAGES
        saved = (before - after) / before * 100 if before else 0
        print(f"{rounds:<6}{len(history):<10}{before:<10}{after:<10}{saved:>6.1f}%   {'是' if triggered else '否'}")
        if triggered:
            rows.append({"rounds": rounds, "messages": len(history), "before": before,
                         "after": after, "saved_pct": round(saved, 1),
                         "summary_tokens": len(enc.encode(episode.summary or ""))})

    avg = sum(r["saved_pct"] for r in rows) / len(rows) if rows else 0
    deep = [r for r in rows if r["rounds"] >= 20]
    avg_deep = sum(r["saved_pct"] for r in deep) / len(deep) if deep else 0
    print("-" * 78)
    print(f"触发压缩场景平均节省：{avg:.1f}%   |   长对话(≥20轮)平均节省：{avg_deep:.1f}%")
    return {"rows": rows, "avg_saved_pct": round(avg, 1), "deep_avg_saved_pct": round(avg_deep, 1)}


# ============================================================================
# 指标①：人脸聚类质量
# ============================================================================

def measure_face() -> dict:
    """
    度量口径（重要）：
        严格的「聚类准确率」需要人工标注「哪些脸是同一个人」，库里没有这种标注。
        因此这里只用两个物理上成立的约束量化：

        负样本：同一张照片里的两张脸必然是不同的人
                → 若被判为同一人物，即为「误合并」（确定性错误）
        正样本：用户已命名人物所关联照片中的人脸，最近邻分配应回归该人物
                （人物归属来自用户命名 = 人类标注，不是聚类结果的自证）

    限制：
        若数据中每张照片至多 1 张脸，则无法构造负样本，误合并率不可测；
        且簇数过少时，任何比率都不具备统计意义。
    """
    import cv2
    from db.database import SessionLocal
    from db.models import Person, Photo
    from services.face_service import SIMILARITY_THRESHOLD, cosine_similarity, face_app

    DET_MIN = 0.50  # 与生产 detect_and_cluster_faces 的低置信度过滤一致

    def nearest(embedding, persons, threshold):
        best_id, best_score = None, 0.0
        for p in persons:
            if not p.face_feature:
                continue
            s = cosine_similarity(embedding, p.face_feature)
            if s > threshold and s > best_score:
                best_id, best_score = p.person_id, s
        return best_id, best_score

    db = SessionLocal()
    try:
        photos = db.query(Photo).filter(Photo.is_valid == True).all()
        persons = db.query(Person).filter(Person.is_valid == True).all()

        print("=" * 78)
        print("指标① 人脸聚类质量")
        print(f"数据规模：照片 {len(photos)} 张 | 人物 {len(persons)} 个")
        print("=" * 78)

        photo_faces = {}
        for p in photos:
            img = cv2.imread(p.file_path)
            if img is None:
                continue
            detected = [f for f in face_app.get(img) if f.det_score >= DET_MIN]
            photo_faces[p.photo_id] = {
                "name": p.file_name,
                "embeddings": [f.embedding.tolist() for f in detected],
                "linked_persons": [pp.person_id for pp in p.persons],
            }

        total_faces = sum(len(v["embeddings"]) for v in photo_faces.values())
        print(f"\n检测到人脸 {total_faces} 张（置信度 >= {DET_MIN}）")
        for v in photo_faces.values():
            print(f"  {v['name'][:30]:<32} 人脸={len(v['embeddings'])}  关联人物={len(v['linked_persons'])}")

        # 负样本
        neg_pairs, mis = 0, 0
        for v in photo_faces.values():
            for i, j in itertools.combinations(range(len(v["embeddings"])), 2):
                neg_pairs += 1
                pi, _ = nearest(v["embeddings"][i], persons, SIMILARITY_THRESHOLD)
                pj, _ = nearest(v["embeddings"][j], persons, SIMILARITY_THRESHOLD)
                if pi is not None and pi == pj:
                    mis += 1
        print(f"\n【负样本】同照片人脸对（必然不同人）")
        if neg_pairs:
            print(f"  样本对 {neg_pairs} | 误合并 {mis} | 误合并率 {mis / neg_pairs * 100:.1f}%")
        else:
            print("  可构造样本对 0 —— 当前数据每张照片至多 1 张人脸，误合并率不可测")

        # 正样本
        correct, tested = 0, 0
        for v in photo_faces.values():
            if not v["linked_persons"]:
                continue
            for emb in v["embeddings"]:
                tested += 1
                pid, _ = nearest(emb, persons, SIMILARITY_THRESHOLD)
                correct += int(pid in v["linked_persons"])
        if tested:
            print(f"\n【正样本】已命名人物关联照片的人脸，最近邻分配是否回归")
            print(f"  可测 {tested} 张 | 正确 {correct} 张 | 命中率 {correct / tested * 100:.1f}%")

        # 簇内一致性
        intra = []
        for person in persons:
            for v in photo_faces.values():
                if person.person_id in v["linked_persons"]:
                    for emb in v["embeddings"]:
                        intra.append(cosine_similarity(emb, person.face_feature))
        if intra:
            print(f"\n【簇内一致性】均值 {sum(intra) / len(intra):.4f}  最小 {min(intra):.4f}  最大 {max(intra):.4f}")

        # 簇间分离度
        inter = [cosine_similarity(a.face_feature, b.face_feature)
                 for a, b in itertools.combinations(persons, 2)
                 if a.face_feature and b.face_feature]
        if inter:
            print(f"【簇间分离度】最大 {max(inter):.4f}  均值 {sum(inter) / len(inter):.4f}")

        margin = None
        if intra and inter:
            margin = min(intra) - max(inter)
            print(f"\n判定间隔 margin = 簇内最小 - 簇间最大 = {margin:+.4f}  "
                  f"{'✅ 线性可分' if margin > 0 else '⚠️ 存在重叠'}")

        return {"faces": total_faces, "persons": len(persons), "neg_pairs": neg_pairs,
                "mis_merged": mis, "positive_tested": tested, "positive_correct": correct,
                "intra_min": round(min(intra), 4) if intra else None,
                "inter_max": round(max(inter), 4) if inter else None,
                "margin": round(margin, 4) if margin is not None else None}
    finally:
        db.close()


# ============================================================================
# 指标②：Top-K 检索召回率
# ============================================================================

def measure_recall(top_k=5) -> dict:
    """
    度量口径：
        数据用 evaluation/data_reason.py 的 30 条跨照片推理样本，其中
        memory_materials 带「关联照片:P001」真值，standard_answer 部分写明答案照片。

        口径 A（严格·照片级）：仅取 standard_answer 中明确含照片 ID 的样本，
                              看 Top-K 结果照片是否命中真值（n≈9，样本量小）
        口径 B（相关性·样本级）：全部样本，看 Top-K 是否召回「该查询自身的记忆条目」
                                （候选库为全部样本混合，随机命中概率低）

    限制：
        评测集是**合成语料**（虚构人物与 Pxxx 编号），度量的是检索算法在该语料上的
        行为，不等价于真实相册上的表现。
    """
    import chromadb
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from db.database import Base
    from db.models import MemoryFact
    from evaluation.data_reason import REASON_SAMPLES
    from services.vector_service import _fact_to_document
    from utils.embedding_client import embedding_client
    import services.global_chat_service as gcs
    import services.search_service as ss

    USER, BATCH, CACHE = "eval_user", 20, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "reports", "_recall_cache.json")

    def parse_material(text):
        fields = {}
        for part in text.split("|"):
            if ":" in part:
                k, v = part.split(":", 1)
                fields[k.strip()] = v.strip()
        return fields

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    docs_map = {}
    for sample in REASON_SAMPLES:
        for idx, material in enumerate(sample["memory_materials"]):
            f = parse_material(material)
            photo = f.get("关联照片", "")
            fact = MemoryFact(
                fact_id=f"{sample['sample_id']}_m{idx}", user_id=USER,
                event=f.get("事件", ""), time_info=f.get("时间", ""), location=f.get("地点", ""),
                tags=[t.strip() for t in f.get("标签", "").split(",") if t.strip()],
                related_photo_ids=[photo] if photo else [],
                related_person_ids=[], source="eval", is_valid=True)
            db.add(fact)
            docs_map[fact.fact_id] = _fact_to_document(fact)
    db.commit()

    print("=" * 78)
    print("指标② Top-K 检索召回率")
    print(f"查询 {len(REASON_SAMPLES)} 条 | 候选记忆库 {len(docs_map)} 条（混合，非单样本内检索）")
    print("=" * 78)

    collection = chromadb.EphemeralClient().get_or_create_collection(
        "eval_facts", metadata={"hnsw:space": "cosine"})
    fact_ids = list(docs_map.keys())
    fact_docs = [docs_map[i] for i in fact_ids]
    vectors = []
    for i in range(0, len(fact_docs), BATCH):
        vectors.extend(embedding_client.embed_batch(fact_docs[i:i + BATCH]))
    collection.add(ids=fact_ids, embeddings=vectors, documents=fact_docs,
                   metadatas=[{"fact_id": i, "user_id": USER} for i in fact_ids])
    print(f"向量化 {len(fact_ids)} 条记忆完成（{BATCH} 条/批）")

    def fake_query(query_text, top_k=10, user_id="default_user"):
        r = collection.query(query_embeddings=[embedding_client.embed(query_text)],
                             n_results=top_k, where={"user_id": user_id})
        if not r or not r.get("ids") or not r["ids"][0]:
            return []
        return [{"fact_id": f, "score": float(s), "document": d}
                for f, s, d in zip(r["ids"][0], r["distances"][0], r["documents"][0])]

    ss.query_similar_facts = fake_query
    records = []
    print("\n解析意图 + 融合检索中（每条 query 一次 LLM 调用）...")
    for i, sample in enumerate(REASON_SAMPLES, 1):
        info = gcs._parse_intent(sample["query"])
        res = ss.hybrid_search(
            db, query=info.get("query") or sample["query"],
            location=info.get("location") or None, time_keyword=info.get("time_keyword") or None,
            tags=info.get("tags") or None, top_k=top_k, user_id=USER,
            intent=info.get("intent"), time_order=info.get("time_order"))
        records.append({
            "sample_id": sample["sample_id"], "query": sample["query"],
            "standard_answer": sample["standard_answer"], "intent": info.get("intent"),
            "time_order": res.get("time_order"),
            "skipped": bool(res.get("skipped")),
            "top_fact_ids": [f["fact_id"] for f in res["facts"]],
            "top_events": [f.get("event", "") for f in res["facts"]],
            "top_photos": [f.get("related_photo_ids") or [] for f in res["facts"]],
        })
        print(f"  {i}/{len(REASON_SAMPLES)}", end="\r")
    print(f"  完成 {len(records)} 条           ")

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as fp:
        json.dump(records, fp, ensure_ascii=False, indent=2)
    print(f"中间结果：{CACHE}")

    result = {"by_photo": {}, "by_sample": {}}

    rows_a = [{**r, "truth": sorted(set(re.findall(r"P\d+", r["standard_answer"])))}
              for r in records]
    rows_a = [r for r in rows_a if r["truth"]]
    print()
    print("-" * 78)
    print(f"口径 A（照片级，standard_answer 含照片 ID 的样本，n={len(rows_a)}）")
    for k in (1, 3, 5):
        h = sum(1 for r in rows_a
                if set(r["truth"]) & {p for ph in r["top_photos"][:k] for p in ph})
        result["by_photo"][f"recall@{k}"] = round(h / len(rows_a) * 100, 1) if rows_a else 0
        print(f"  Recall@{k} = {h}/{len(rows_a)} = {result['by_photo'][f'recall@{k}']}%")
    for r in rows_a:
        ok = bool(set(r["truth"]) & {p for ph in r["top_photos"][:3] for p in ph})
        print(f"    {'✅' if ok else '❌'} {r['sample_id']:<12} 真值={r['truth']} intent={r['intent']}")
        if not ok:
            print(f"        查询：{r['query']}")
            for ev in r["top_events"][:3]:
                print(f"        Top：{ev[:52]}")

    print()
    print("-" * 78)
    print(f"口径 B（样本级：Top-K 是否召回该查询自身的记忆，n={len(records)}）")
    for k in (1, 3, 5):
        h = sum(1 for r in records if any(f.startswith(r["sample_id"]) for f in r["top_fact_ids"][:k]))
        result["by_sample"][f"recall@{k}"] = round(h / len(records) * 100, 1)
        print(f"  Recall@{k} = {h}/{len(records)} = {result['by_sample'][f'recall@{k}']}%")
    print("\n  逐条（Top3）：")
    for r in records:
        hit = any(f.startswith(r["sample_id"]) for f in r["top_fact_ids"][:3])
        print(f"    {'✅' if hit else '❌'} {r['sample_id']:<12} intent={str(r['intent']):<10} "
              f"time_order={str(r.get('time_order')):<9} {r['query'][:34]}")

    db.close()
    return result


def main():
    parser = argparse.ArgumentParser(description="三项关键指标的实测工具")
    parser.add_argument("metric", nargs="?", default="all",
                        choices=["all", "token", "face", "recall"])
    args = parser.parse_args()

    summary = {}
    if args.metric in ("all", "token"):
        summary["token"] = measure_token()
        print()
    if args.metric in ("all", "face"):
        summary["face"] = measure_face()
        print()
    if args.metric in ("all", "recall"):
        summary["recall"] = measure_recall()
        print()

    if args.metric == "all":
        print("=" * 78)
        print("汇总")
        print("=" * 78)
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
