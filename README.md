# Personal Memory Agent · 个人记忆智能体

基于照片的个人记忆管理智能体。上传照片后自动解析画面、识别人物、抽取结构化记忆，支持单照片对话、全局跨照片检索问答、纪念日与年度回忆主动提醒。

---

## 目录

- [核心功能](#核心功能)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [核心流程](#核心流程)
- [API 概览](#api-概览)
- [数据模型](#数据模型)
- [评测体系](#评测体系)
- [数据备份与迁移](#数据备份与迁移)
- [常见问题](#常见问题)

---

## 核心功能

| 模块 | 能力 |
|---|---|
| 照片解析 | EXIF 元数据（exifread）+ 多模态视觉模型分析画面 + InsightFace 人脸检测聚类 |
| 记忆抽取 | 从视觉解析与对话中抽取「时间/地点/事件/人物关系/情感/标签」六字段事实记忆 |
| 冲突消解 | 三层策略：向量粗筛直接合并 → LLM 裁决（skip/add/merge/archive）→ 记忆精炼防冗长 |
| 单照片对话 | 带记忆上下文问答，历史超 20 条自动压缩为摘要，对话中持续抽取新记忆 |
| 全局问答 | 意图解析 → 双引擎检索（向量语义 + 实体过滤）→ LLM 综合回答，标注引用照片 |
| 主动交互 | 信息补全提示、相似照片推荐、纪念日提醒、年度回忆生成 |
| 提醒调度 | 后台守护线程每 6 小时判定，单实例锁防多 worker 重复，通知中心幂等去重 |
| 人物管理 | 自动聚类、改名（后台同步关联记忆并重建向量）、合并相似人物 |
| 评测体系 | 四维 80 条合成数据集评测，Judge 评分 + 基线对比 + 20% 人工抽检 |

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端框架 | FastAPI + uvicorn |
| ORM / 数据库 | SQLAlchemy + PyMySQL / MySQL 8.0 |
| 向量库 | Chroma（本地持久化，cosine 距离） |
| 人脸识别 | InsightFace (buffalo_l, CPU) + OpenCV |
| 图像处理 | Pillow + exifread |
| LLM / 视觉 / Embedding | OpenAI 兼容接口（LangChain ChatOpenAI） |
| 前端 | Next.js 16 + React 19 + TypeScript + axios + framer-motion |
| 可观测 | Langfuse（可选，旁路埋点） |
| 日志 | 控制台 + 按天文件（backend/logs/app_YYYYMMDD.log） |

---

## 项目结构

```
personal_memory_agent/
├── backend/
│   ├── main.py               # FastAPI 入口：API 端点 + 启动自检 + 调度器
│   ├── config.py             # 配置加载（.env）
│   ├── requirements.txt
│   ├── .env.example          # 环境变量模板
│   ├── db/
│   │   ├── database.py       # SQLAlchemy 引擎 / Session
│   │   ├── models.py         # 数据模型
│   │   └── init_db.py        # 建表脚本
│   ├── services/
│   │   ├── vision_service.py       # EXIF 解析 + 多模态视觉分析
│   │   ├── face_service.py         # 人脸检测聚类 / 改名 / 合并
│   │   ├── memory_service.py       # 记忆抽取 + 冲突消解 + 精炼
│   │   ├── chat_service.py         # 单照片对话 + 开场白 + 历史压缩
│   │   ├── global_chat_service.py  # 全局跨照片问答
│   │   ├── search_service.py       # 双引擎混合搜索
│   │   ├── vector_service.py       # Chroma 向量增删查
│   │   ├── photo_service.py        # 照片详情查询
│   │   ├── proactive_service.py    # 主动交互
│   │   ├── notification_service.py # 通知中心
│   │   └── scheduler.py            # 主动提醒调度器
│   ├── evaluation/           # 四维评测体系
│   ├── utils/
│   │   ├── embedding_client.py     # Embedding 客户端
│   │   ├── langfuse_client.py      # Langfuse 埋点
│   │   └── logger.py               # 统一日志
│   ├── storage/              # 运行时数据（不提交 git）
│   └── logs/                 # 运行日志（不提交 git）
└── frontend/
    ├── app/                  # Next.js App Router
    ├── components/           # UI 组件
    └── package.json
```

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0（端口 3306）
- 可用的 OpenAI 兼容 LLM / 视觉模型 / Embedding 接口

### 2. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
```

### 3. 配置环境变量

复制模板并填写真实值：

```bash
# Windows
copy backend\.env.example backend\.env

# Linux / macOS
cp backend/.env.example backend/.env
```

backend/.env.example 已标注每个字段的用途，包含 MySQL、对话模型、视觉模型、Embedding、评测裁判模型、Langfuse、存储路径等。字段完整说明见 backend/config.py。


### 4. 初始化数据库

```bash
cd backend
python -m db.init_db
```

> 该命令执行 drop_all + create_all，仅首次使用时运行，已有数据时会清空所有表。

### 5. 启动服务

后端（端口 8000）：

```bash
cd backend
# 生产模式（2 worker）
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
# 开发模式（热重载）
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

前端（端口 3000）：

```bash
cd frontend
npm run dev
# 或
npm run build && npm run start
```

后端启动时会打印模型端点自检日志并自动启动主动提醒调度器。访问 http://localhost:3000。

### 6. 停止服务

后端 / 前端分别 Ctrl+C 终止。如需按端口清理残留进程：

```bash
# Windows
netstat -ano | findstr ":8000"
taskkill /F /PID <pid>
```

---

## 核心流程

### 照片上传与记忆流水线

上传照片 → 存原图到 storage/photos，写 MySQL photo 表 → parse_exif() 读取拍摄时间/GPS/相机型号 → analyze_photo_content() 多模态模型分析场景/物体/人数/标签 → detect_and_cluster_faces() InsightFace 人脸检测 + 余弦相似度聚类 + 自动合并 → extract_memory_from_vision() 从视觉结果抽取初始事实记忆 → 三层冲突消解 → 写入 Chroma 向量库 → 创建 EpisodeMemory，generate_opening_message() 生成 AI 主动开场白

### 记忆冲突消解（三层策略）

| 层级 | 条件 | 动作 |
|---|---|---|
| 粗筛 | Chroma 语义距离 < 0.15 | 极度相似，直接合并 |
| LLM 裁决 | 距离 0.15 ~ 0.45 | 调用 LLM 输出 skip / add / merge / archive |
| 新增 | 距离 ≥ 0.45 | 视为新事件，独立入库 |

- merge：字段互补合并，merge_count + 1
- archive：旧记忆置为无效（保留溯源），新记忆替换
- 记忆精炼：单条记忆合并次数 > 3 或 event 长度 > 100 字时，异步调用 LLM 凝练为一句话，重置合并计数
- 数量治理：单张照片最多保留 5 条有效记忆，超出合并到最旧一条

### 全局跨照片问答

用户提问 → _parse_intent() 意图解析（recall/statistic/compare/relation/general）→ 人名模糊匹配 → hybrid_search() 双引擎检索（向量语义 + 人物/地点/时间/标签过滤）→ 构建记忆上下文（最多 15 条）→ LLM 综合回答，末尾用 [照片:photo_id] 标注引用 → 对话历史存入 storage/global_chat.json（最多保留 100 条）

### 主动提醒调度

- 后端启动时 start_scheduler() 启动守护线程，每 6 小时执行一轮
- 纪念日提醒：正则解析记忆中的日期，匹配未来 7 天内周年日，幂等 key 为 anniversary:{fact_id}:{anniversary_date}
- 年度回忆：为上一年度预生成故事（LLM），同一年度只推一次，生成失败不推送留待下轮重试
- 单实例锁：storage/.scheduler.lock 原子创建 + mtime 心跳，生产模式 2 worker 下只有一个进程真正运行
- 通知写入 storage/notifications.json，前端通过 /api/proactive/notifications 拉取红点与弹窗

---

## API 概览

### 照片与人物

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/photo/upload | 上传照片并触发完整解析流水线 |
| GET | /api/photo/list | 照片列表（按上传时间倒序） |
| GET | /api/photo/detail | 照片详情（EXIF + 视觉 + 人物 + 记忆） |
| GET | /api/photo/image/{photo_id} | 照片原图文件 |
| GET | /api/photo/persons | 照片识别到的人物 |
| GET | /api/person/photos | 某人物出现的所有照片 |
| PUT | /api/person/rename | 人物改名（后台同步关联记忆） |
| POST | /api/person/merge-similar | 合并相似人物 |

### 对话与记忆

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/chat/send | 单照片对话 |
| GET | /api/chat/history | 单照片对话历史 |
| GET | /api/memory/photo | 单照片的记忆事实列表 |
| POST | /api/search/hybrid | 双引擎混合搜索 |
| POST | /api/global/chat | 全局跨照片问答 |
| GET | /api/global/history | 全局对话历史 |
| DELETE | /api/global/history | 清空全局对话历史 |

### 主动交互

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/proactive/missing-info | 信息补全检测 |
| GET | /api/proactive/similar-photos | 相似照片推荐 |
| GET | /api/proactive/anniversaries | 纪念日提醒 |
| POST | /api/proactive/yearly-recap | 年度回忆生成（即时，调试用） |
| GET | /api/proactive/notifications | 主动提醒通知列表 |
| POST | /api/proactive/notifications/read | 标记通知已读 |

### 系统与评测

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/health | 健康检查 |
| POST | /api/eval/run | 触发评测（后台运行，可选 dimension） |
| GET | /api/eval/status | 查询评测状态与结果摘要 |

---

## 数据模型

| 表 | 核心字段 | 说明 |
|---|---|---|
| photo | photo_id, file_path, exif_info(JSON), vision_analysis(JSON), parse_status, face_parse_status | 照片元数据与解析结果 |
| episode_memory | episode_id, photo_id, full_chat_history(JSON), user_story, summary | 单照片情景记忆 |
| person | person_id, name, face_feature(JSON), photo_count | 人物聚类实体 |
| memory_fact | fact_id, time_info, location, event, person_relation, emotion, tags(JSON), source, related_photo_ids, related_person_ids, merge_count | 结构化事实记忆 |
| photo_person | photo_id, person_id | 照片-人物多对多关联表 |

---

## 评测体系

通过 POST /api/eval/run 触发，后台线程运行，结果写入 backend/evaluation/reports/（md + json）。

合成数据集共 80 条（记忆抽取 20 / 冲突更新 20 / 跨照片推理 30 / 主动交互 10），非真实用户数据。

| 维度 | 评测内容 | 核心指标 | 基线 |
|---|---|---|---|
| 记忆抽取 | 六字段抽取正确率 | 字段覆盖率 / 硬一致率 / Judge 分 | 覆盖 ≥ 90%, Judge ≥ 3.5 |
| 冲突更新 | skip/add/merge/archive 决策 | 决策准确率 | ≥ 95% |
| 跨照片推理 | 多记忆综合回答 | Judge 分（准确/完整/可溯源） | ≥ 4.0 |
| 主动交互 | 信息补全 / 纪念日 / 年度回忆 | 三类子准确率 / 年度覆盖率 | 补全 ≥ 95%, 纪念日 ≥ 90%, 年度 ≥ 90% |

- Judge 使用独立配置的 JUDGE_MODEL_*（未配置时回退主模型），保证评分一致性
- 报告包含基线达标对比表 + 20% 人工抽检清单（固定种子 42，可复现）

---

## 数据备份与迁移

需手动备份以下数据：

- MySQL：mysqldump 导出 personal_agent 库全量 SQL
- Chroma 向量库：复制 backend/storage/chroma/
- 照片原图：复制 backend/storage/photos/
- 全局对话记录：复制 backend/storage/global_chat.json

```bash
# MySQL 导出示例
mysqldump -h127.0.0.1 -P3306 -uroot -p personal_agent > backups/mysql_personal_agent.sql
```

迁移到新机器：旧机备份 → 复制项目到新机 → MySQL 导入 SQL → 还原 chroma / photos 目录 → 配置 .env → 启动。

---

## 常见问题

**Q：照片上传后一直显示"解析中"？**
检查后端窗口日志，多为视觉模型额度或 VISION_MODEL_* 配置错误。启动时后端会打印模型端点自检日志，确认 base_url 与 key 已正确配置。

**Q：AI 对话报错或无回复？**
检查 MODEL_BASE_URL 是否指向正确的 OpenAI 兼容地址（未配置时会静默回退到 https://api.openai.com/v1），以及模型额度是否充足。

**Q：向量检索不可用？**
检查 EMBEDDING_* 配置。未配置时系统自动回退为纯实体条件检索，全局问答仍可工作但语义召回能力下降。

**Q：纪念日提醒没有出现？**
调度器每 6 小时才跑一轮，且需记忆中存在可解析的日期字段。可通过 GET /api/proactive/anniversaries 手动查询当前命中的纪念日。
