# -*- coding: utf-8 -*-
"""
单照片记忆抽取评测样本（20条）
字段：
- sample_id: 唯一ID
- eval_dimension: "记忆抽取"
- photo_resource: 照片视觉描述（文本）
- user_dialogue: 用户对话历史（列表 [{role, content}]）
- standard_answer: 期望抽取的结构化记忆 {time_info, location, event, person_relation, emotion, tags}
- key_metric: ["字段抽取准确率"]
"""
EXTRACT_SAMPLES = [
    {
        "sample_id": "extract_001",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：餐厅室内。多人在圆桌边围坐聚餐，桌上摆着鸳鸯火锅和生日蛋糕，气氛热闹。",
        "user_dialogue": [
            {"role": "user", "content": "这是上个月我们宿舍的期末聚会，庆祝考试全部结束。"}
        ],
        "standard_answer": {
            "time_info": "上个月",
            "location": "餐厅",
            "event": "宿舍同学期末聚会庆祝考试结束",
            "person_relation": "宿舍同学聚会",
            "emotion": "开心",
            "tags": ["聚会", "日常"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_002",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：海边沙滩，阳光明媚，几个人在沙滩上笑着拍照，背后是蓝色大海。",
        "user_dialogue": [
            {"role": "user", "content": "去年暑假和爸妈去了三亚，这是第二天在海边拍的。"}
        ],
        "standard_answer": {
            "time_info": "去年暑假",
            "location": "三亚海边",
            "event": "和爸妈去三亚旅行，在海边拍照",
            "person_relation": "家人出游",
            "emotion": "开心",
            "tags": ["旅行"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_003",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：室内居家。桌上一个插着蜡烛的生日蛋糕，周围几个人鼓掌，灯光偏暗。",
        "user_dialogue": [
            {"role": "user", "content": "这是我20岁生日，朋友们给我准备的惊喜派对。"}
        ],
        "standard_answer": {
            "time_info": "20岁生日当天",
            "location": "",
            "event": "朋友为庆祝20岁生日准备惊喜派对",
            "person_relation": "朋友",
            "emotion": "开心",
            "tags": ["生日"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_004",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：办公室。深夜的办公桌前，电脑屏幕亮着代码，桌上有咖啡杯和外卖盒。",
        "user_dialogue": [
            {"role": "user", "content": "上个月项目上线前的加班夜，我们团队熬到凌晨三点。"}
        ],
        "standard_answer": {
            "time_info": "上个月",
            "location": "办公室",
            "event": "项目上线前团队加班到凌晨",
            "person_relation": "同事",
            "emotion": "平淡",
            "tags": ["工作"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_005",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：客厅地板，一只柯基犬趴着，吐着舌头看镜头。",
        "user_dialogue": [
            {"role": "user", "content": "这是我家的狗叫旺财，去年在宠物店领养的。"}
        ],
        "standard_answer": {
            "time_info": "去年",
            "location": "",
            "event": "领养柯基犬旺财",
            "person_relation": "宠物",
            "emotion": "",
            "tags": ["日常", "宠物"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_006",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：校园广场。一群穿着学士服的学生在阶梯前合影，有人举着学士帽。",
        "user_dialogue": [
            {"role": "user", "content": "今年六月毕业典礼，和全班同学拍的大合照。"}
        ],
        "standard_answer": {
            "time_info": "今年六月",
            "location": "学校",
            "event": "毕业典礼与全班同学拍大合照",
            "person_relation": "同学",
            "emotion": "感动",
            "tags": ["毕业"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_007",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：居家餐厅。一家老小围坐大圆桌，桌上摆满菜，电视里放着春节联欢晚会。",
        "user_dialogue": [
            {"role": "user", "content": "除夕夜在家吃的团圆饭，一家人都在。"}
        ],
        "standard_answer": {
            "time_info": "除夕夜",
            "location": "家",
            "event": "除夕全家吃团圆饭",
            "person_relation": "家人",
            "emotion": "开心",
            "tags": ["家庭", "聚会"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_008",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：婚礼现场。台上新人正在交换戒指，台下宾客鼓掌，有鲜花拱门。",
        "user_dialogue": [
            {"role": "user", "content": "上个月参加了表姐的婚礼，场面很温馨。"}
        ],
        "standard_answer": {
            "time_info": "上个月",
            "location": "",
            "event": "参加表姐的婚礼",
            "person_relation": "亲戚",
            "emotion": "感动",
            "tags": ["婚礼"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_009",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：山顶观景台，几人在台阶上休息喝水，远处是城市全貌。",
        "user_dialogue": [
            {"role": "user", "content": "上周末和同事一起去爬了岳麓山，累但很值。"}
        ],
        "standard_answer": {
            "time_info": "上周末",
            "location": "岳麓山",
            "event": "和同事一起爬岳麓山",
            "person_relation": "同事",
            "emotion": "开心",
            "tags": ["旅行", "日常"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_010",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：咖啡店窗边，桌上一杯拿铁和一台打开笔记本的电脑。",
        "user_dialogue": [
            {"role": "user", "content": "这张就是随手拍的，下午在这家店赶报告。"}
        ],
        "standard_answer": {
            "time_info": "下午",
            "location": "咖啡店",
            "event": "下午在咖啡店赶报告",
            "person_relation": "",
            "emotion": "",
            "tags": ["工作", "日常"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_011",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：西餐厅。烛光晚餐，桌上摆着玫瑰花束和红酒，环境浪漫。",
        "user_dialogue": [
            {"role": "user", "content": "情人节那天和女朋友在这家西餐厅约会。"}
        ],
        "standard_answer": {
            "time_info": "情人节",
            "location": "西餐厅",
            "event": "和女朋友在西餐厅情人节约会",
            "person_relation": "情侣",
            "emotion": "开心",
            "tags": ["纪念日"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_012",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：健身房。落地镜前一个穿运动服的人举着手机自拍，背景是器械区。",
        "user_dialogue": [
            {"role": "user", "content": "今年开始坚持健身，这是第三个月的打卡记录。"}
        ],
        "standard_answer": {
            "time_info": "今年",
            "location": "健身房",
            "event": "坚持健身三个月打卡",
            "person_relation": "",
            "emotion": "平淡",
            "tags": ["日常"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_013",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：图书馆自习区。书桌上堆满考研资料和笔记本，有人在埋头写题。",
        "user_dialogue": [
            {"role": "user", "content": "考研那段时间我每天都泡在图书馆，这张是某天晚上拍的。"}
        ],
        "standard_answer": {
            "time_info": "考研那段时间",
            "location": "图书馆",
            "event": "考研期间每天在图书馆自习",
            "person_relation": "",
            "emotion": "",
            "tags": ["工作", "日常"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_014",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：傍晚公园小径，落叶满地，一位中年妇女和一个年轻人并肩散步。",
        "user_dialogue": [
            {"role": "user", "content": "秋天傍晚和妈妈在楼下公园散步，聊了很多。"}
        ],
        "standard_answer": {
            "time_info": "秋天傍晚",
            "location": "公园",
            "event": "和妈妈在公园散步",
            "person_relation": "家人",
            "emotion": "平淡",
            "tags": ["日常"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_015",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：火车车窗，窗外的田园风光飞速掠过，车厢里人不多。",
        "user_dialogue": [
            {"role": "user", "content": "五一假期坐高铁去了成都玩，沿途风景不错。"}
        ],
        "standard_answer": {
            "time_info": "五一假期",
            "location": "成都",
            "event": "坐高铁去成都旅行",
            "person_relation": "",
            "emotion": "开心",
            "tags": ["旅行"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_016",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：桌面上一块小蛋糕和一张手写信封，光线柔和。",
        "user_dialogue": [
            {"role": "user", "content": "去年生日是自己一个人过的，但朋友从外地寄来了一封信，很感动。"}
        ],
        "standard_answer": {
            "time_info": "去年生日",
            "location": "",
            "event": "独自过生日，收到朋友寄来的信",
            "person_relation": "朋友",
            "emotion": "感动",
            "tags": ["生日"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_017",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：演唱会现场，舞台灯光耀眼，台下人山人海举着荧光棒。",
        "user_dialogue": [
            {"role": "user", "content": "前年夏天和朋友一起去看了周杰伦的演唱会，超嗨！"}
        ],
        "standard_answer": {
            "time_info": "前年夏天",
            "location": "",
            "event": "和朋友一起看周杰伦演唱会",
            "person_relation": "朋友",
            "emotion": "开心",
            "tags": ["日常", "聚会"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_018",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：厨房灶台，锅里在炒菜，旁边放着可乐和鸡翅的原料。",
        "user_dialogue": [
            {"role": "user", "content": "周末在家研究新菜，第一次尝试做可乐鸡翅。"}
        ],
        "standard_answer": {
            "time_info": "周末",
            "location": "家",
            "event": "第一次做可乐鸡翅",
            "person_relation": "",
            "emotion": "平淡",
            "tags": ["日常"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_019",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：机场航站楼，落地窗前一个拖着行李箱的背影，远处是停机坪。",
        "user_dialogue": [
            {"role": "user", "content": "上个月送闺蜜出国留学，在机场有点舍不得。"}
        ],
        "standard_answer": {
            "time_info": "上个月",
            "location": "机场",
            "event": "送闺蜜出国留学",
            "person_relation": "朋友",
            "emotion": "遗憾",
            "tags": ["日常"]
        },
        "key_metric": ["字段抽取准确率"]
    },
    {
        "sample_id": "extract_020",
        "eval_dimension": "记忆抽取",
        "photo_resource": "场景：深夜便利店，一个穿着工作服的人在关东煮柜台前买夜宵。",
        "user_dialogue": [
            {"role": "user", "content": "昨天加班到十点，在楼下便利店随便买了点关东煮当夜宵。"}
        ],
        "standard_answer": {
            "time_info": "昨天",
            "location": "便利店",
            "event": "加班后在便利店买关东煮当夜宵",
            "person_relation": "",
            "emotion": "平淡",
            "tags": ["工作"]
        },
        "key_metric": ["字段抽取准确率"]
    },
]
