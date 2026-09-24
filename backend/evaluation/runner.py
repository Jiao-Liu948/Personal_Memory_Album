# -*- coding: utf-8 -*-
"""批量评测执行器：四维执行 + judge 评分 + 汇总报告（markdown + json）"""
import json
import os
import random
from datetime import datetime

from evaluation.dataset import EVAL_DATASET, DIMENSION_STATS
from evaluation.extractor import run_extraction, compare_extraction
from evaluation.conflict import resolve_conflict
from evaluation.reasoning import run_reasoning
from evaluation.proactive import detect_missing_fields, check_anniversary, run_yearly_recap
from evaluation.judge import judge_score, judge_coverage
from utils.logger import logger

# ============================================================
# 指标基线（文档 7.3.3）：版本迭代时对比是否达标
# ============================================================
BASELINES = {
    "记忆抽取": {"judge": 3.5, "coverage": 0.90},
    "冲突更新": {"accuracy": 0.95},
    "跨照片推理": {"judge": 4.0},
    "主动交互": {"missing_info": 0.95, "anniversary": 0.90, "yearly_coverage": 0.90},
}

# 人工抽检参数（文档 7.3.3：抽 20% 样本人工复核，固定种子保证可复现）
MANUAL_CHECK_RATIO = 0.2
MANUAL_SEED = 42


def _dims(dimension: str, samples):
    return [s for s in samples if s["eval_dimension"] == dimension]


def run_extract_eval(samples, judge_enabled=True, limit=None):
    batch = samples if limit is None else samples[:limit]
    rows = []
    coverage_sum = exact_sum = 0.0
    for s in batch:
        try:
            pred = run_extraction(s)
        except Exception as e:
            logger.error(f"[评测] {s['sample_id']} 抽取执行失败: {e}")
            rows.append({"sample_id": s["sample_id"], "error": str(e), "coverage_rate": 0, "exact_rate": 0, "judge_score": 0})
            continue
        cmp = compare_extraction(pred, s["standard_answer"])
        jd = judge_score(json.dumps(s["standard_answer"], ensure_ascii=False),
                         json.dumps(pred, ensure_ascii=False)) if judge_enabled else {}
        coverage_sum += cmp["coverage_rate"]
        exact_sum += cmp["exact_rate"]
        rows.append({
            "sample_id": s["sample_id"],
            "coverage_rate": cmp["coverage_rate"],
            "exact_rate": cmp["exact_rate"],
            "missing": cmp["missing"],
            "judge_score": jd.get("score"),
            "pred": pred,
        })
    n = len(rows)
    return {
        "dimension": "记忆抽取", "total": n,
        "avg_coverage": round(coverage_sum / n, 4) if n else 0,
        "avg_exact": round(exact_sum / n, 4) if n else 0,
        "avg_judge": round(sum(r["judge_score"] or 0 for r in rows) / n, 4) if n and judge_enabled else None,
        "rows": rows,
    }


def run_conflict_eval(samples, limit=None):
    batch = samples if limit is None else samples[:limit]
    rows = []
    correct = 0
    decision_stat = {}
    for s in batch:
        try:
            decision = resolve_conflict(s["old_memory"], s["new_memory"])
        except Exception as e:
            logger.error(f"[评测] {s['sample_id']} 冲突执行失败: {e}")
            rows.append({"sample_id": s["sample_id"], "error": str(e), "correct": False, "decision": None})
            continue
        ok = decision == s["standard_decision"]
        correct += 1 if ok else 0
        decision_stat[decision] = decision_stat.get(decision, 0) + 1
        rows.append({
            "sample_id": s["sample_id"],
            "decision": decision,
            "standard": s["standard_decision"],
            "correct": ok,
            "reason": s["standard_reason"],
        })
    n = len(rows)
    return {
        "dimension": "冲突更新", "total": n,
        "accuracy": round(correct / n, 4) if n else 0,
        "decision_stat": decision_stat,
        "rows": rows,
    }


def run_reason_eval(samples, judge_enabled=True, limit=None):
    batch = samples if limit is None else samples[:limit]
    rows = []
    score_sum = 0.0
    for s in batch:
        try:
            answer = run_reasoning(s)
        except Exception as e:
            logger.error(f"[评测] {s['sample_id']} 推理执行失败: {e}")
            rows.append({"sample_id": s["sample_id"], "error": str(e), "judge_score": 0})
            continue
        jd = judge_score(s["standard_answer"], answer) if judge_enabled else {}
        score_sum += jd.get("score", 0)
        rows.append({
            "sample_id": s["sample_id"],
            "judge_score": jd.get("score"),
            "accuracy": jd.get("accuracy"),
            "completeness": jd.get("completeness"),
            "traceability": jd.get("traceability"),
            "reason": jd.get("reason"),
            "answer": answer,
        })
    n = len(rows)
    return {
        "dimension": "跨照片推理", "total": n,
        "avg_judge": round(score_sum / n, 4) if n else 0,
        "rows": rows,
    }


def run_proactive_eval(samples, judge_enabled=True, limit=None):
    batch = samples if limit is None else samples[:limit]
    mi_correct = mi_total = 0
    an_correct = an_total = 0
    mi_rows, an_rows = [], []
    recap_rows = []
    for s in batch:
        s_type = s["type"]
        if s_type == "missing_info":
            missing = detect_missing_fields(s["memory"])
            ok = sorted(missing) == sorted(s["standard_missing_fields"])
            mi_correct += 1 if ok else 0
            mi_total += 1
            mi_rows.append({"sample_id": s["sample_id"], "detected": missing,
                            "standard": s["standard_missing_fields"], "correct": ok})
        elif s_type == "anniversary":
            r = check_anniversary(s["memory"], s["anchor_date"])
            ok_status = r["status"] == s["standard_status"]
            ok_years = (r["years"] == s["standard_years"])
            ok = ok_status and ok_years
            an_correct += 1 if ok else 0
            an_total += 1
            an_rows.append({"sample_id": s["sample_id"], "status": r["status"], "years": r["years"],
                            "standard_status": s["standard_status"], "standard_years": s["standard_years"],
                            "correct": ok})
        elif s_type == "yearly_recap":
            try:
                story = run_yearly_recap(s)
                cov = judge_coverage(s["standard_cover_events"], story) if judge_enabled else {}
                covered = len(cov.get("covered_events", []))
                total_ev = len(s["standard_cover_events"])
                recap_rows.append({
                    "sample_id": s["sample_id"],
                    "coverage_rate": round(covered / total_ev, 4) if total_ev else 1.0,
                    "covered": cov.get("covered_events", []),
                    "missing": cov.get("missing_events", []),
                    "hallucinated": cov.get("hallucinated", False),
                    "story": story,
                })
            except Exception as e:
                logger.error(f"[评测] {s['sample_id']} 年度回忆失败: {e}")
                recap_rows.append({"sample_id": s["sample_id"], "error": str(e), "coverage_rate": 0})
    recap_ok = [r for r in recap_rows if r.get("coverage_rate", 0) == 1.0 and not r.get("hallucinated")]
    return {
        "dimension": "主动交互",
        "missing_info": {"correct": mi_correct, "total": mi_total, "rows": mi_rows,
                         "accuracy": round(mi_correct / mi_total, 4) if mi_total else None},
        "anniversary": {"correct": an_correct, "total": an_total, "rows": an_rows,
                        "accuracy": round(an_correct / an_total, 4) if an_total else None},
        "yearly_recap": {"rows": recap_rows,
                         "avg_coverage": round(sum(r.get("coverage_rate", 0) for r in recap_rows) / len(recap_rows), 4) if recap_rows else None,
                         "full_cover_ratio": round(len(recap_ok) / len(recap_rows), 4) if recap_rows else None},
    }


def _fmt(v):
    return "-" if v is None else f"{v:.2f}"


def run_all_evaluation(judge_enabled=True, limit=None) -> dict:
    """执行全部四维评测，返回结构化结果"""
    samples = EVAL_DATASET
    extract_res = run_extract_eval(_dims("记忆抽取", samples), judge_enabled, limit)
    conflict_res = run_conflict_eval(_dims("冲突更新", samples), limit)
    reason_res = run_reason_eval(_dims("跨照片推理", samples), judge_enabled, limit)
    proactive_res = run_proactive_eval(_dims("主动交互", samples), judge_enabled, limit)
    return {"extract": extract_res, "conflict": conflict_res, "reason": reason_res, "proactive": proactive_res}


def _empty_result() -> dict:
    """空结果结构（单维度运行时其余维度为空，保持 build_report 兼容）"""
    return {
        "extract": {"dimension": "记忆抽取", "total": 0, "avg_coverage": 0, "avg_exact": 0, "avg_judge": None, "rows": []},
        "conflict": {"dimension": "冲突更新", "total": 0, "accuracy": 0, "decision_stat": {}, "rows": []},
        "reason": {"dimension": "跨照片推理", "total": 0, "avg_judge": None, "rows": []},
        "proactive": {"dimension": "主动交互",
                      "missing_info": {"correct": 0, "total": 0, "rows": [], "accuracy": None},
                      "anniversary": {"correct": 0, "total": 0, "rows": [], "accuracy": None},
                      "yearly_recap": {"rows": [], "avg_coverage": None, "full_cover_ratio": None}},
    }


def run_dimension_eval(dimension: str, judge_enabled=True, limit=None) -> dict:
    """只跑指定维度的评测，返回与 run_all_evaluation 相同结构（其余维度为空）"""
    res = _empty_result()
    samples = _dims(dimension, EVAL_DATASET)
    if dimension == "记忆抽取":
        res["extract"] = run_extract_eval(samples, judge_enabled, limit)
    elif dimension == "冲突更新":
        res["conflict"] = run_conflict_eval(samples, limit)
    elif dimension == "跨照片推理":
        res["reason"] = run_reason_eval(samples, judge_enabled, limit)
    elif dimension == "主动交互":
        res["proactive"] = run_proactive_eval(samples, judge_enabled, limit)
    return res


def build_baseline_section(res: dict) -> list:
    """基线达标情况（文档 7.3.3）"""
    B = BASELINES
    rows = []
    ex, cf, rs, pa = res["extract"], res["conflict"], res["reason"], res["proactive"]

    # 记忆抽取
    if ex["total"]:
        rows.append(("记忆抽取", "Judge 均分(≥3.5)", ex.get("avg_judge"), B["记忆抽取"]["judge"]))
        rows.append(("记忆抽取", "字段覆盖(≥90%)", (ex.get("avg_coverage") or 0), B["记忆抽取"]["coverage"]))
    # 冲突更新
    if cf["total"]:
        rows.append(("冲突更新", "决策准确率(≥95%)", cf.get("accuracy"), B["冲突更新"]["accuracy"]))
    # 跨照片推理
    if rs["total"]:
        rows.append(("跨照片推理", "Judge 均分(≥4.0)", rs.get("avg_judge"), B["跨照片推理"]["judge"]))
    # 主动交互
    pa_mi, pa_an, pa_yr = pa["missing_info"], pa["anniversary"], pa["yearly_recap"]
    if pa_mi["total"]:
        rows.append(("主动交互", "信息补全(≥95%)", pa_mi.get("accuracy"), B["主动交互"]["missing_info"]))
    if pa_an["total"]:
        rows.append(("主动交互", "纪念日识别(≥90%)", pa_an.get("accuracy"), B["主动交互"]["anniversary"]))
    if pa_yr.get("rows"):
        rows.append(("主动交互", "年度覆盖(≥90%)", pa_yr.get("avg_coverage"), B["主动交互"]["yearly_coverage"]))

    L = ["## 三、基线达标情况（文档 7.3.3）\n",
         "| 维度 | 指标 | 实测 | 基线 | 达标 |", "|---|---|---|---|---|"]
    for dim, metric, actual, base in rows:
        ok = (actual or 0) >= base
        L.append(f"| {dim} | {metric} | {_fmt(actual)} | {_fmt(base)} | {'✅' if ok else '❌'} |")
    return L


def build_manual_check_section(res: dict) -> list:
    """人工抽检 20%：抽取随机样本，列出模型输出与标准答案对照，供人工复核（文档 7.3.3）"""
    rng = random.Random(MANUAL_SEED)
    L = ["## 四、人工抽检清单（文档 7.3.3，随机抽 20%，固定种子可复现）\n",
         "人工核对以下样本，在「人工判定」列填 通过/不通过，并回写结论到版本迭代记录。\n"]

    def _sample_rows(rows):
        if not rows:
            return []
        k = max(1, round(len(rows) * MANUAL_CHECK_RATIO))
        return rng.sample(rows, min(k, len(rows)))

    # 记忆抽取
    ex_rows = _sample_rows(res["extract"].get("rows", []))
    if ex_rows:
        L.append("### 记忆抽取抽检\n")
        L.append("| 样本 | 标准答案 | 模型抽取结果 | 人工判定 |")
        L.append("|---|---|---|---|")
        for r in ex_rows:
            s = next((x for x in EVAL_DATASET if x["sample_id"] == r["sample_id"]), {})
            std = json.dumps(s.get("standard_answer", {}), ensure_ascii=False)
            pred = json.dumps(r.get("pred", {}), ensure_ascii=False)
            L.append(f"| {r['sample_id']} | {std} | {pred} |  |")

    # 冲突更新
    cf_rows = _sample_rows(res["conflict"].get("rows", []))
    if cf_rows:
        L.append("### 冲突更新抽检\n")
        L.append("| 样本 | 标准决策 | 系统决策 | 人工判定 |")
        L.append("|---|---|---|---|")
        for r in cf_rows:
            L.append(f"| {r['sample_id']} | {r['standard']} | {r['decision']} |  |")

    # 跨照片推理
    rs_rows = _sample_rows(res["reason"].get("rows", []))
    if rs_rows:
        L.append("### 跨照片推理抽检\n")
        L.append("| 样本 | 问题 | 标准要点 | 模型回答 | 人工判定 |")
        L.append("|---|---|---|---|---|")
        for r in rs_rows:
            s = next((x for x in EVAL_DATASET if x["sample_id"] == r["sample_id"]), {})
            L.append(f"| {r['sample_id']} | {s.get('question', '')} | {s.get('standard_answer', '')} "
                     f"| {r.get('answer', '')} |  |")

    # 主动交互
    mi_rows = _sample_rows(res["proactive"]["missing_info"].get("rows", []))
    an_rows = _sample_rows(res["proactive"]["anniversary"].get("rows", []))
    yr_rows = _sample_rows(res["proactive"]["yearly_recap"].get("rows", []))
    if mi_rows or an_rows or yr_rows:
        L.append("### 主动交互抽检\n")
    for r in mi_rows:
        L.append(f"- **{r['sample_id']}**（信息补全）检测={r['detected']} 标准={r['standard']} 人工判定：____")
    for r in an_rows:
        L.append(f"- **{r['sample_id']}**（纪念日）系统={r['status']}年{r['years']} 标准={r['standard_status']}年{r['standard_years']} 人工判定：____")
    for r in yr_rows:
        s = next((x for x in EVAL_DATASET if x["sample_id"] == r["sample_id"]), {})
        L.append(f"- **{r['sample_id']}**（年度回忆）应覆盖 {s.get('standard_cover_events', [])}\n  模型故事：{r.get('story', '')}\n  人工判定：____")
    return L


def build_report(res: dict) -> str:
    """生成 markdown 报告"""
    L = []
    L.append("# Personal Memory Agent 评测报告")
    L.append(f"\n- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"- 数据集规模：{sum(DIMENSION_STATS.values())} 条"
             f"（{'、'.join(f'{k}{v}条' for k, v in DIMENSION_STATS.items())}）\n")

    L.append("## 一、总体指标\n")
    L.append("| 维度 | 样本数 | 核心指标 | 说明 |")
    L.append("|---|---|---|---|")
    ex = res["extract"]
    cf = res["conflict"]
    rs = res["reason"]
    pa = res["proactive"]
    L.append(f"| 记忆抽取 | {ex['total']} | 字段覆盖 {_fmt((ex.get('avg_coverage') or 0)*100)}% / 硬一致 {_fmt((ex.get('avg_exact') or 0)*100)}%"
             f"{' / Judge ' + _fmt(ex.get('avg_judge')) if ex.get('avg_judge') is not None else ''} | 六字段抽取正确率/完整率 |")
    L.append(f"| 冲突更新 | {cf['total']} | 决策准确率 {_fmt((cf.get('accuracy') or 0)*100)}% | skip/merge/archive/add 正确率 |")
    L.append(f"| 跨照片推理 | {rs['total']} | Judge {_fmt(rs.get('avg_judge'))}/5 | 准确率+完整率+可溯源 |")
    mi = pa.get("missing_info", {})
    an = pa.get("anniversary", {})
    yr = pa.get("yearly_recap", {})
    yr_rows = yr.get("rows", [])
    mi_acc = "-" if mi.get("total", 0) == 0 else f"{_fmt((mi.get('accuracy') or 0)*100)}%"
    an_acc = "-" if an.get("total", 0) == 0 else f"{_fmt((an.get('accuracy') or 0)*100)}%"
    yr_avg = yr.get("avg_coverage")
    yr_disp = "-" if yr_avg is None else f"{_fmt(yr_avg*100)}%"
    L.append(f"| 主动交互 | {mi.get('total',0)+an.get('total',0)+len(yr_rows)} | 补全 {mi_acc} / 纪念日 {an_acc} / 年度覆盖 {yr_disp} | 三类子能力 |")

    L.append("\n## 二、分维度明细\n")

    # 记忆抽取
    L.append("### 记忆抽取\n")
    L.append("| sample | 字段覆盖 | 硬一致 | Judge | 缺失字段 |")
    L.append("|---|---|---|---|---|")
    for r in ex.get("rows", []):
        L.append(f"| {r['sample_id']} | {_fmt(r['coverage_rate']*100)}% | {_fmt(r['exact_rate']*100)}% "
                 f"| {_fmt(r.get('judge_score'))} | {'、'.join(r.get('missing') or [])} |")

    # 冲突更新
    L.append("\n### 冲突更新\n")
    L.append(f"决策分布：{cf.get('decision_stat', {})}\n")
    L.append("| sample | 系统决策 | 标准决策 | 正确 | 标准理由 |")
    L.append("|---|---|---|---|---|")
    for r in cf.get("rows", []):
        L.append(f"| {r['sample_id']} | {r['decision']} | {r['standard']} | {'✅' if r['correct'] else '❌'} | {r['reason']} |")

    # 跨照片推理
    L.append("\n### 跨照片推理\n")
    L.append("| sample | Judge | 准确 | 完整 | 溯源 | 理由 |")
    L.append("|---|---|---|---|---|---|")
    for r in rs.get("rows", []):
        L.append(f"| {r['sample_id']} | {_fmt(r.get('judge_score'))} | {_fmt(r.get('accuracy'))} | "
                 f"{_fmt(r.get('completeness'))} | {_fmt(r.get('traceability'))} | {r.get('reason') or ''} |")

    # 主动交互
    L.append("\n### 主动交互\n")
    L.append(f"- 信息补全：{mi.get('correct', 0)}/{mi.get('total', 0)} 正确\n")
    L.append(f"- 纪念日识别：{an.get('correct', 0)}/{an.get('total', 0)} 正确\n")
    L.append("| sample | 年度覆盖 | 覆盖事件 | 缺失事件 | 幻觉 |")
    L.append("|---|---|---|---|---|")
    for r in yr_rows:
        L.append(f"| {r['sample_id']} | {_fmt(r.get('coverage_rate', 0)*100)}% | {'、'.join(r.get('covered') or [])} "
                 f"| {'、'.join(r.get('missing') or [])} | {'是' if r.get('hallucinated') else '否'} |")

    L.append("")
    L += build_baseline_section(res)
    L.append("")
    L += build_manual_check_section(res)

    return "\n".join(L)


def save_reports(res: dict, report_dir: str = None) -> dict:
    """保存 markdown 与 json 报告，返回路径"""
    if report_dir is None:
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(report_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(report_dir, f"eval_report_{ts}.md")
    json_path = os.path.join(report_dir, f"eval_report_{ts}.json")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(build_report(res))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=str)
    return {"md": md_path, "json": json_path}
