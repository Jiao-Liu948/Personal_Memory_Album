# -*- coding: utf-8 -*-
"""评测数据集汇总：共80条（记忆抽取20 / 冲突更新20 / 跨照片推理30 / 主动交互10）"""
from evaluation.data_extract import EXTRACT_SAMPLES
from evaluation.data_conflict import CONFLICT_SAMPLES
from evaluation.data_reason import REASON_SAMPLES
from evaluation.data_proactive import PROACTIVE_SAMPLES

EVAL_DATASET = EXTRACT_SAMPLES + CONFLICT_SAMPLES + REASON_SAMPLES + PROACTIVE_SAMPLES

DIMENSION_STATS = {
    "记忆抽取": len(EXTRACT_SAMPLES),
    "冲突更新": len(CONFLICT_SAMPLES),
    "跨照片推理": len(REASON_SAMPLES),
    "主动交互": len(PROACTIVE_SAMPLES),
}

if __name__ == "__main__":
    total = len(EVAL_DATASET)
    print(f"评测数据集总数: {total} 条")
    for dim, cnt in DIMENSION_STATS.items():
        print(f"  - {dim}: {cnt} 条")
    assert total == 80, f"数据集条数异常: {total}"
    print("数据集条数校验通过 (80)")
