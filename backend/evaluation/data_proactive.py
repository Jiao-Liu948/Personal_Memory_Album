# -*- coding: utf-8 -*-
"""
主动交互评测样本（10条）
分三类：
1. 信息补全（3条）：memory + standard_missing_fields（期望识别缺失字段）
2. 纪念日识别（3条）：memory（含日期）+ anchor_date（锚定今天，保证可复现）+ 期望状态/周年
3. 年度回忆（4条）：year + memories + 期望覆盖的关键事件
"""
PROACTIVE_SAMPLES = [
    # ===== 信息补全（3条）=====
    {
        "sample_id": "proactive_001", "eval_dimension": "主动交互", "type": "missing_info",
        "memory": {"event": "和朋友去爬山", "time_info": "", "location": "", "person_relation": "朋友", "emotion": "", "tags": ["旅行"]},
        "standard_missing_fields": ["时间", "地点", "情感"],
        "standard_reason": "该记忆缺时间、地点、情感三个字段",
        "key_metric": ["信息补全准确率"]
    },
    {
        "sample_id": "proactive_002", "eval_dimension": "主动交互", "type": "missing_info",
        "memory": {"event": "参加同事婚礼", "time_info": "上个月", "location": "", "person_relation": "同事", "emotion": "开心", "tags": ["婚礼"]},
        "standard_missing_fields": ["地点"],
        "standard_reason": "仅缺地点字段",
        "key_metric": ["信息补全准确率"]
    },
    {
        "sample_id": "proactive_003", "eval_dimension": "主动交互", "type": "missing_info",
        "memory": {"event": "给妈妈过生日", "time_info": "", "location": "家", "person_relation": "家人", "emotion": "", "tags": ["生日"]},
        "standard_missing_fields": ["时间", "情感"],
        "standard_reason": "缺时间和情感字段",
        "key_metric": ["信息补全准确率"]
    },

    # ===== 纪念日识别（3条，锚定今天 2026-08-31 可复现）=====
    {
        "sample_id": "proactive_004", "eval_dimension": "主动交互", "type": "anniversary",
        "memory": {"event": "和女朋友的恋爱纪念日", "time_info": "2022年8月31日", "location": "", "person_relation": "情侣", "emotion": "开心", "tags": ["纪念日"]},
        "anchor_date": "2026-08-31",
        "standard_status": "today",
        "standard_years": 4,
        "standard_reason": "2022-08-31 在 2026-08-31 正好满4周年，今天应提醒",
        "key_metric": ["纪念日识别准确率"]
    },
    {
        "sample_id": "proactive_005", "eval_dimension": "主动交互", "type": "anniversary",
        "memory": {"event": "爸爸的生日", "time_info": "2024年9月3日", "location": "家", "person_relation": "家人", "emotion": "", "tags": ["生日"]},
        "anchor_date": "2026-08-31",
        "standard_status": "upcoming",
        "standard_years": 2,
        "standard_reason": "2026-09-03 距 2026-08-31 还有3天，属于未来N天内的周年提醒",
        "key_metric": ["纪念日识别准确率"]
    },
    {
        "sample_id": "proactive_006", "eval_dimension": "主动交互", "type": "anniversary",
        "memory": {"event": "毕业周年", "time_info": "2024年8月29日", "location": "学校", "person_relation": "同学", "emotion": "感动", "tags": ["毕业"]},
        "anchor_date": "2026-08-31",
        "standard_status": "just_passed",
        "standard_years": 2,
        "standard_reason": "2026-08-29 距 2026-08-31 已过去2天，在刚过去的补提醒窗口内",
        "key_metric": ["纪念日识别准确率"]
    },

    # ===== 年度回忆（4条）=====
    {
        "sample_id": "proactive_007", "eval_dimension": "主动交互", "type": "yearly_recap",
        "year": 2024,
        "memories": [
            {"date": "2024-02-14", "event": "和女朋友情人节约会", "location": "西餐厅"},
            {"date": "2024-06-20", "event": "毕业典礼合影", "location": "学校"},
            {"date": "2024-08-31", "event": "去成都旅行", "location": "成都"},
            {"date": "2024-11-23", "event": "第一次跑马拉松", "location": "赛道"},
        ],
        "standard_cover_events": ["情人节", "毕业", "成都旅行", "马拉松"],
        "standard_reason": "年度故事应覆盖这4个关键事件",
        "key_metric": ["回忆覆盖完整率", "无编造"]
    },
    {
        "sample_id": "proactive_008", "eval_dimension": "主动交互", "type": "yearly_recap",
        "year": 2023,
        "memories": [
            {"date": "2023-04-12", "event": "考研上岸收到录取通知", "location": "家"},
            {"date": "2023-07-20", "event": "去三亚旅行", "location": "三亚"},
            {"date": "2023-12-31", "event": "独自跨年", "location": "家"},
        ],
        "standard_cover_events": ["考研上岸", "三亚旅行", "跨年"],
        "standard_reason": "年度故事应覆盖考研上岸、三亚旅行、跨年",
        "key_metric": ["回忆覆盖完整率", "无编造"]
    },
    {
        "sample_id": "proactive_009", "eval_dimension": "主动交互", "type": "yearly_recap",
        "year": 2022,
        "memories": [
            {"date": "2022-08-31", "event": "和女朋友确定恋爱关系", "location": "校园"},
            {"date": "2022-10-15", "event": "去黄姚古镇旅行", "location": "黄姚古镇"},
        ],
        "standard_cover_events": ["确定恋爱关系", "黄姚古镇旅行"],
        "standard_reason": "年度故事应覆盖恋爱开始和古镇旅行",
        "key_metric": ["回忆覆盖完整率", "无编造"]
    },
    {
        "sample_id": "proactive_010", "eval_dimension": "主动交互", "type": "yearly_recap",
        "year": 2025,
        "memories": [
            {"date": "2025-05-01", "event": "和舍友毕业旅行", "location": "大理"},
            {"date": "2025-09-10", "event": "入职第一份工作", "location": "公司"},
            {"date": "2025-12-25", "event": "圣诞节和朋友聚餐", "location": "餐厅"},
        ],
        "standard_cover_events": ["毕业旅行", "入职", "圣诞聚餐"],
        "standard_reason": "年度故事应覆盖毕业旅行、入职、圣诞聚餐",
        "key_metric": ["回忆覆盖完整率", "无编造"]
    },
]
