# -*- coding: utf-8 -*-
"""
评测体系 CLI 入口
用法（在 backend 目录下执行）：
    python -m evaluation.run_evaluation                 # 全量评测（含 judge）
    python -m evaluation.run_evaluation --no-judge      # 关闭 LLM-as-judge（只跑规则指标）
    python -m evaluation.run_evaluation --limit 5       # 每个维度只跑前 N 条（快速验证）
    python -m evaluation.run_evaluation --dimension 记忆抽取   # 只跑指定维度
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")

from evaluation.dataset import EVAL_DATASET
from evaluation.runner import (
    run_extract_eval, run_conflict_eval, run_reason_eval,
    run_proactive_eval, build_report, save_reports,
)
from evaluation.dataset import DIMENSION_STATS


def main():
    parser = argparse.ArgumentParser(description="Personal Memory Agent 评测体系")
    parser.add_argument("--dimension", choices=["记忆抽取", "冲突更新", "跨照片推理", "主动交互"], default=None)
    parser.add_argument("--limit", type=int, default=None, help="每个维度只跑前 N 条")
    parser.add_argument("--no-judge", action="store_true", help="关闭 LLM-as-judge 评分")
    parser.add_argument("--report-dir", default=None, help="报告输出目录")
    args = parser.parse_args()

    judge_enabled = not args.no_judge
    samples = EVAL_DATASET
    if args.dimension:
        samples = [s for s in samples if s["eval_dimension"] == args.dimension]
        print(f"只评测维度: {args.dimension}（{len(samples)} 条）")
    else:
        print(f"全量评测 {sum(DIMENSION_STATS.values())} 条样本 | judge={'开' if judge_enabled else '关'}")

    res = {}
    order = ["记忆抽取", "冲突更新", "跨照片推理", "主动交互"]
    for dim in order:
        sub = [s for s in samples if s["eval_dimension"] == dim]
        if not sub:
            continue
        if dim == "记忆抽取":
            res["extract"] = run_extract_eval(sub, judge_enabled, args.limit)
        elif dim == "冲突更新":
            res["conflict"] = run_conflict_eval(sub, args.limit)
        elif dim == "跨照片推理":
            res["reason"] = run_reason_eval(sub, judge_enabled, args.limit)
        elif dim == "主动交互":
            res["proactive"] = run_proactive_eval(sub, judge_enabled, args.limit)

    # 仅保留有数据的分区，统一 key 便于 build_report
    full = {"extract": res.get("extract", {"total": 0, "avg_coverage": 0, "avg_exact": 0, "avg_judge": None, "rows": []}),
            "conflict": res.get("conflict", {"total": 0, "accuracy": 0, "rows": []}),
            "reason": res.get("reason", {"total": 0, "avg_judge": None, "rows": []}),
            "proactive": res.get("proactive", {"missing_info": {"correct": 0, "total": 0}, "anniversary": {"correct": 0, "total": 0}, "yearly_recap": {"rows": []}})}

    print("\n" + "=" * 60)
    print(build_report(full))
    print("=" * 60)

    paths = save_reports(full, args.report_dir)
    print(f"\n报告已保存：\n  {paths['md']}\n  {paths['json']}")


if __name__ == "__main__":
    main()
