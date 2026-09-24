# -*- coding: utf-8 -*-
"""
记忆冲突更新评测样本（20条）
字段：
- sample_id
- eval_dimension: "冲突更新"
- old_memory: 旧记忆 {time_info, location, event, person_relation, emotion, tags}
- new_memory: 新抽取记忆（同结构）
- standard_decision: 期望决策 skip/merge/archive/add
- standard_reason: 期望理由
- key_metric: ["决策准确率"]
"""
CONFLICT_SAMPLES = [
    {
        "sample_id": "conflict_001",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "去年暑假", "location": "三亚", "event": "和爸妈去三亚旅行", "person_relation": "家人", "emotion": "开心", "tags": ["旅行"]},
        "new_memory": {"time_info": "去年暑假", "location": "三亚", "event": "和爸妈去三亚旅行", "person_relation": "家人", "emotion": "开心", "tags": ["旅行"]},
        "standard_decision": "skip",
        "standard_reason": "新旧记忆完全重复，直接丢弃新记忆",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_002",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "", "location": "餐厅", "event": "在餐厅聚餐", "person_relation": "", "emotion": "", "tags": ["聚会"]},
        "new_memory": {"time_info": "", "location": "餐厅", "event": "和朋友在餐厅吃饭点了披萨", "person_relation": "朋友", "emotion": "开心", "tags": ["聚会", "朋友"]},
        "standard_decision": "merge",
        "standard_reason": "指向同一顿饭，新记忆补充了人物和细节，语义等价应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_003",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "上周末", "location": "岳麓山", "event": "去爬岳麓山", "person_relation": "", "emotion": "", "tags": ["旅行"]},
        "new_memory": {"time_info": "上周末", "location": "岳麓山", "event": "和同事爬岳麓山，山顶吃了零食", "person_relation": "同事", "emotion": "开心", "tags": ["旅行", "同事"]},
        "standard_decision": "merge",
        "standard_reason": "同一时间同一地点同一事件，新记忆补充人物和细节，应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_004",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "2023年生日", "location": "海底捞", "event": "生日和朋友在海底捞庆祝", "person_relation": "朋友", "emotion": "开心", "tags": ["生日"]},
        "new_memory": {"time_info": "2023年生日", "location": "烤肉店", "event": "那年生日其实是和朋友在烤肉店庆祝的", "person_relation": "朋友", "emotion": "开心", "tags": ["生日"]},
        "standard_decision": "archive",
        "standard_reason": "同一次生日的庆祝地点被用户更正，旧记忆地点错误应归档，由新记忆替换",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_005",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "", "location": "公园", "event": "在公园散步", "person_relation": "", "emotion": "", "tags": ["日常"]},
        "new_memory": {"time_info": "秋天傍晚", "location": "公园", "event": "秋天傍晚和妈妈在公园散步", "person_relation": "家人", "emotion": "平淡", "tags": ["日常", "家人"]},
        "standard_decision": "merge",
        "standard_reason": "同一地点同一事件，新记忆补充了时间和人物，应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_006",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "", "location": "餐厅", "event": "在餐厅聚餐", "person_relation": "", "emotion": "", "tags": ["聚会"]},
        "new_memory": {"time_info": "今年", "location": "健身房", "event": "今年开始坚持健身", "person_relation": "", "emotion": "", "tags": ["日常"]},
        "standard_decision": "add",
        "standard_reason": "两件事完全不相关（聚餐 vs 健身），应作为新记忆入库",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_007",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "2023年8月", "location": "餐厅", "event": "朋友生日聚餐", "person_relation": "朋友", "emotion": "开心", "tags": ["聚会", "生日"]},
        "new_memory": {"time_info": "2023年8月", "location": "餐厅", "event": "朋友的生日聚会吃饭", "person_relation": "朋友", "emotion": "开心", "tags": ["聚会", "吃饭"]},
        "standard_decision": "merge",
        "standard_reason": "时间地点完全一致、标签重叠、事件重合，结构强匹配应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_008",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "今年六月", "location": "学校", "event": "毕业典礼与全班同学拍大合照", "person_relation": "同学", "emotion": "感动", "tags": ["毕业"]},
        "new_memory": {"time_info": "今年六月", "location": "学校", "event": "毕业典礼与全班同学拍大合照", "person_relation": "同学", "emotion": "感动", "tags": ["毕业", "合影"]},
        "standard_decision": "skip",
        "standard_reason": "事件文本完全一致（仅标签略不同），完全重复应丢弃新记忆",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_009",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "上个月", "location": "", "event": "参加表姐的婚礼", "person_relation": "亲戚", "emotion": "感动", "tags": ["婚礼"]},
        "new_memory": {"time_info": "上个月", "location": "酒店", "event": "表姐的婚礼上我帮忙拍了很多照片", "person_relation": "亲戚", "emotion": "感动", "tags": ["婚礼", "家人"]},
        "standard_decision": "merge",
        "standard_reason": "同一场婚礼，新记忆补充了地点和细节，应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_010",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "今年", "location": "健身房", "event": "坚持健身", "person_relation": "", "emotion": "", "tags": ["日常"]},
        "new_memory": {"time_info": "考研那段时间", "location": "图书馆", "event": "每天在图书馆自习", "person_relation": "", "emotion": "", "tags": ["工作"]},
        "standard_decision": "add",
        "standard_reason": "健身与自习是不同事件，应作为新记忆入库",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_011",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "上个月", "location": "餐厅", "event": "和同事聚餐", "person_relation": "同事", "emotion": "", "tags": ["聚会"]},
        "new_memory": {"time_info": "上个月", "location": "餐厅", "event": "更正：那次其实是和朋友聚餐，不是同事", "person_relation": "朋友", "emotion": "", "tags": ["聚会"]},
        "standard_decision": "archive",
        "standard_reason": "人物关系被用户明确更正，旧记忆关系有误应归档替换",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_012",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "前年夏天", "location": "", "event": "看了周杰伦的演唱会", "person_relation": "", "emotion": "开心", "tags": ["日常"]},
        "new_memory": {"time_info": "前年夏天", "location": "体育场", "event": "前年夏天和朋友一起看周杰伦演唱会，现场很嗨", "person_relation": "朋友", "emotion": "开心", "tags": ["日常", "朋友"]},
        "standard_decision": "merge",
        "standard_reason": "同一场演唱会，新记忆补充地点人物细节，应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_013",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "2023年8月", "location": "餐厅", "event": "朋友生日聚餐", "person_relation": "朋友", "emotion": "开心", "tags": ["生日"]},
        "new_memory": {"time_info": "2023年9月", "location": "餐厅", "event": "商务谈判晚宴", "person_relation": "客户", "emotion": "平淡", "tags": ["工作"]},
        "standard_decision": "add",
        "standard_reason": "地点相同但事件、时间、人物完全不同，是两个不同事件，应新增",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_014",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "今年六月", "location": "学校", "event": "毕业典礼合影", "person_relation": "同学", "emotion": "", "tags": ["毕业"]},
        "new_memory": {"time_info": "今年六月", "location": "学校", "event": "毕业典礼和全班合影，很感动", "person_relation": "同学", "emotion": "感动", "tags": ["毕业"]},
        "standard_decision": "merge",
        "standard_reason": "同一事件，新记忆补充了情感，应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_015",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "除夕夜", "location": "家", "event": "除夕全家吃团圆饭", "person_relation": "家人", "emotion": "开心", "tags": ["家庭"]},
        "new_memory": {"time_info": "除夕夜", "location": "家", "event": "除夕全家吃团圆饭", "person_relation": "家人", "emotion": "开心", "tags": ["家庭"]},
        "standard_decision": "skip",
        "standard_reason": "完全一致，重复对话抽取应丢弃",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_016",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "周末", "location": "家", "event": "第一次做可乐鸡翅", "person_relation": "", "emotion": "", "tags": ["日常"]},
        "new_memory": {"time_info": "周末", "location": "家", "event": "周末在家第一次做可乐鸡翅，味道不错", "person_relation": "", "emotion": "开心", "tags": ["日常", "做饭"]},
        "standard_decision": "merge",
        "standard_reason": "同一事件同一时间地点，新记忆补充细节和情感，应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_017",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "去年生日", "location": "", "event": "独自一人过生日", "person_relation": "", "emotion": "遗憾", "tags": ["生日"]},
        "new_memory": {"time_info": "去年生日", "location": "宿舍", "event": "更正：去年生日其实和舍友一起过的", "person_relation": "舍友", "emotion": "开心", "tags": ["生日"]},
        "standard_decision": "archive",
        "standard_reason": "旧记忆内容被用户更正，应归档由新记忆替换",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_018",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "2023年五一", "location": "北京", "event": "去北京旅行", "person_relation": "", "emotion": "", "tags": ["旅行"]},
        "new_memory": {"time_info": "2024年五一", "location": "北京", "event": "去北京旅行", "person_relation": "", "emotion": "", "tags": ["旅行"]},
        "standard_decision": "add",
        "standard_reason": "不同年份的两次旅行，应作为新记忆入库",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_019",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "五一假期", "location": "成都", "event": "去成都玩", "person_relation": "", "emotion": "", "tags": ["旅行"]},
        "new_memory": {"time_info": "五一假期", "location": "成都", "event": "五一去成都吃美食逛景点", "person_relation": "", "emotion": "开心", "tags": ["旅行", "美食"]},
        "standard_decision": "merge",
        "standard_reason": "时间地点一致、事件重合、标签重叠，应合并",
        "key_metric": ["决策准确率"]
    },
    {
        "sample_id": "conflict_020",
        "eval_dimension": "冲突更新",
        "old_memory": {"time_info": "上周末", "location": "岳麓山", "event": "去岳麓山爬山", "person_relation": "", "emotion": "", "tags": ["旅行"]},
        "new_memory": {"time_info": "上周末", "location": "岳麓山", "event": "爬了岳麓山，和同事一起", "person_relation": "同事", "emotion": "", "tags": ["旅行"]},
        "standard_decision": "merge",
        "standard_reason": "同一时间地点同一事件，语义等价应合并",
        "key_metric": ["决策准确率"]
    },
]
