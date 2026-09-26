# 多模态影像知识管理 Agent

把零散的影像资料转化为**可检索、可推理、可追溯的结构化知识资产**。

影像入库即自动完成元数据解析、视觉理解与人脸聚类；对话中口述的事实被抽取为长期结构化记忆；并以**实体匹配 + 语义向量双引擎**支撑跨影像的自然语言问答。主动能力（纪念日提醒、年度回忆）由后端调度器按事件驱动，前端只做被动展示。

---

## 目录

- [核心能力](#核心能力)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [核心流程](#核心流程)
- [前端界面](#前端界面)
- [API 概览](#api-概览)
- [数据模型](#数据模型)
- [指标度量](#指标度量)
- [评测体系](#评测体系)
- [数据备份与迁移](#数据备份与迁移)
- [常见问题](#常见问题)

---

## 核心能力

| 模块 | 能力 |
|---|---|
| 影像解析 | EXIF 元数据（exifread）+ 多模态视觉理解 + InsightFace 人脸检测聚类，聚类后自动合并重复人物 |
| 影像命名 | 用户自定义名称（`photo.display_name`），原始文件名保留用于溯源；支持随时清空回退 |
| 结构化记忆 | 从视觉结果与对话中抽取「时间 / 地点 / 事件 / 人物关系 / 情感 / 标签」六维事实记忆 |
| 冲突消解 | 三层策略：向量粗筛直接合并 → LLM 裁决（skip/add/merge/archive）→ 记忆精炼防冗长 |
| 双引擎检索 | 实体匹配度打分 + 向量分数归一化，按查询意图加权融合排序 |
| 时序意图重排 | 「第一次 / 最早 / 最近 / 上次」类查询，在相关度同档位内按时序重排 |
| 单影像问答 | 带记忆上下文的多轮对话，历史超 20 条自动摘要压缩，对话中持续抽取新记忆 |
| 跨影像问答 | 意图解析 → 融合检索 → LLM 综合回答，标注引用照片 |
| 主动提醒 | 纪念日提醒 + 年度回忆，后台调度、幂等去重，前端红点 + 弹窗 |
| 人物管理 | 自动聚类、自动合并、重命名（异步同步关联记忆并重建向量） |
| 运行控制台 | 影像资产 / 知识沉淀 / 处理管线 / 模型端点，全部实时计算 |
| 评测与度量 | 四维 80 条评测体系 + 三项关键指标的可复现度量工具 |

---

## 系统架构

```
前端交互层   Next.js 16 + React 19 + framer-motion
             运行控制台 / 影像资产库 / 影像问答 / 跨影像问答 / 主动提醒
─────────────────────────────────────────────────────────────
接口层       FastAPI：CORS、参数校验、启动自检、增量迁移、25 个业务端点
─────────────────────────────────────────────────────────────
能力层       vision_service     EXIF + 多模态视觉分析
             face_service       人脸检测聚类 / 自动合并 / 改名传播
             memory_service     记忆抽取 + 三层冲突消解 + 精炼
             chat_service       单影像对话 + 开场白 + 上下文压缩
             search_service     双引擎融合检索 + 时序重排
             global_chat_service 跨影像意图解析与问答
             proactive_service  信息补全 / 相似影像 / 纪念日 / 年度回忆
             notification_service / scheduler  主动提醒与调度
─────────────────────────────────────────────────────────────
存储层       MySQL 8（结构化） + Chroma（语义向量） + 本地文件（原图 / 通知 / 对话）
─────────────────────────────────────────────────────────────
可观测层     统一日志（控制台 + 按天落盘） + Langfuse 调用链埋点
```

**关于多用户**：当前为单用户实现（`user_id` 默认 `default_user`），但数据层所有查询均按 `user_id` 过滤，接入团队协作时只需透传该维度，无需改动业务逻辑。

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端框架 | FastAPI + uvicorn |
| ORM / 数据库 | SQLAlchemy + PyMySQL / MySQL 8.0 |
| 向量库 | Chroma（本地持久化，cosine 距离） |
| 人脸识别 | InsightFace (buffalo_l, CPU) + OpenCV |
| 图像处理 | Pillow + exifread |
| LLM / 视觉 / Embedding | OpenAI 兼容接口（LangChain ChatOpenAI），可指向私有化部署端点 |
| 前端 | Next.js 16 + React 19 + TypeScript + axios + framer-motion |
| 可观测 | Langfuse（兼容 3.x / 4.x API） |
| 日志 | 控制台 + 按天文件（backend/logs/app_YYYYMMDD.log） |

---

## 项目结构

```
personal_memory_agent/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── db/                # ORM、数据库迁移、初始化
│   ├── services/          # 业务服务层
│   ├── evaluation/       # 评测套件
│   └── utils/             # 工具模块
└── frontend/
    ├── app/
    └── components/
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

```bash
# Windows
copy backend\.env.example backend\.env

# Linux / macOS
cp backend/.env.example backend/.env
```

`backend/.env.example` 已标注每个字段用途。需要特别注意的是 **`MODEL_BASE_URL`**：如果使用千问 / 豆包等第三方 OpenAI 兼容接口，必须显式配置，否则会静默回退到 `https://api.openai.com/v1` 导致调用失败。后端启动时会打印端点自检日志。

### 4. 初始化数据库

**首次使用**（会清空所有表）：

```bash
cd backend
python -m db.init_db
```

**已有数据的环境**无需重跑该命令：后端启动时会自动执行 `db/migrate.py` 的幂等增量迁移，只为已有表补齐新增字段（如 `photo.display_name`），不会影响既有数据。

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

启动后访问 http://localhost:3000 。后端启动时会打印模型端点自检日志并启动主动提醒调度器。

### 6. 停止服务

后端 / 前端分别 Ctrl+C 终止。按端口清理残留进程：

```bash
# Windows
netstat -ano | findstr ":8000"
taskkill /F /PID <pid>
```

---

## 核心流程

### 影像入库与记忆流水线

上传 → 原图落盘 + 写 `photo` 表 → `parse_exif()` 读拍摄时间 / GPS / 设备 → `analyze_photo_content()` 多模态分析场景 / 物体 / 人数 / 标签 → `detect_and_cluster_faces()` 人脸检测 + 余弦聚类 + **聚类后自动合并** → `extract_memory_from_vision()` 抽取初始事实记忆 → 三层冲突消解 → 写入 Chroma → 创建 `EpisodeMemory` 并生成 AI 主动开场白。

### 双引擎融合检索

两路召回后按意图加权统一排序，而不是简单合并：

1. **实体侧**：按「命中条件数 / 条件总数」给出 0~1 匹配度（人物 / 地点 / 时间 / 标签各自独立召回后统计命中），而非 AND 硬过滤
2. **向量侧**：Chroma 的 cosine 距离换算为 0~1 相似度（`clamp(1 - distance, 0, 1)`）
3. **融合**：`final = w_entity × entity_score + w_vector × vector_score`，同分时实体命中更多的优先

| 查询意图 | 实体权重 | 向量权重 | 说明 |
|---|---|---|---|
| statistic / relation | 0.75 | 0.25 | 依赖人物、地点、时间等实体精确匹配 |
| recall | 0.40 | 0.60 | 模糊回忆，语义相似更重要 |
| 未指定（直接调 API） | 0.60 | 0.40 | 默认权重 |
| general | — | — | 普通寒暄，跳过召回（省一次 embedding，避免无关记忆污染上下文） |

### 时序意图重排

当查询含「第一次 / 最早」或「最近 / 上次」时，用户要的是时间维度的答案，而默认排序只看相关度。

实现上**按相关度分档（档宽 0.05），档内按时序排、档间保持相关度顺序** —— 时间只在相关度相近的候选之间起决定作用，绝不覆盖相关度本身。

时间从 `time_info` 自由文本解析（复用纪念日检测的解析器），并额外支持「2019年国庆」这类只含年份的表述。

### 记忆冲突消解（三层策略）

| 层级 | 条件 | 动作 |
|---|---|---|
| 粗筛 | Chroma 语义距离 < 0.15 | 极度相似，直接合并 |
| LLM 裁决 | 距离 0.15 ~ 0.45 | 调用 LLM 输出 skip / add / merge / archive |
| 新增 | 距离 ≥ 0.45 | 视为新事件，独立入库 |

- **merge**：字段互补合并，`merge_count + 1`
- **archive**：旧记忆置为无效（保留溯源），新记忆替换
- **记忆精炼**：单条合并次数 > 3 或 event 长度 > 100 字时，异步调用 LLM 凝练为一句话并重置计数
- **数量治理**：单张影像最多保留 5 条有效记忆，超出合并到最旧一条

### 跨影像问答

用户提问 → `_parse_intent()` 解析意图（recall / statistic / compare / relation / general）并提取实体条件与时序要求 → 人名模糊匹配 → `hybrid_search()` 融合检索 → 构建记忆上下文（最多 15 条）→ LLM 综合回答，末尾以 `[照片:photo_id]` 标注引用 → 历史存入 `storage/global_chat.json`。

> `general` 意图走独立的闲聊 prompt：跳过召回后素材必然为空，若沿用「必须说没有相关记忆」的规则，会把「你好」答成「我的记忆中没有相关记录」。

### 主动提醒调度

- 启动时 `start_scheduler()` 拉起守护线程，每 6 小时执行一轮
- **纪念日**：解析记忆中日期，匹配未来 7 天内周年日，幂等 key 为 `anniversary:{fact_id}:{anniversary_date}`
- **年度回忆**：为上一年度预生成故事（LLM），同一年度只推一次；生成失败不推送，留待下轮重试
- **单实例锁**：`storage/.scheduler.lock` 原子创建 + mtime 心跳 + `atexit` 释放，生产模式 2 worker 下只有一个进程真正运行
- 通知写入 `storage/notifications.json`，前端通过 `/api/proactive/notifications` 拉取红点与弹窗

---

## 前端界面

| 视图 | 说明 |
|---|---|
| **运行控制台**（首页） | 影像资产 / 人物实体 / 记忆条目 / 知识维度指标；自动化处理管线（各阶段挂真实计数）+ 近 7 天入库量；知识标签分布与记忆来源构成；模型端点绑定状态与能力开关 |
| **影像资产库** | 文件夹开合动画展开；卡片支持 3D 跟随光标倾斜；悬停可快捷命名 |
| **影像问答** | 单张影像的知识问答 + 结构化记忆 / 识别人物 / 相似影像侧栏；标题处可内联命名 |
| **跨影像问答** | 独立弹层，跨全部影像检索作答，展示引用照片 |
| **主动提醒** | 顶栏铃铛未读红点 + 通知面板（纪念日展示相关照片，年度回忆展示预生成故事与统计） |

## 数据备份与迁移

需手动备份：

- MySQL：`mysqldump` 导出 `personal_agent` 库全量 SQL
- Chroma 向量库：复制 `backend/storage/chroma/`
- 影像原图：复制 `backend/storage/photos/`
- 对话与通知：复制 `backend/storage/global_chat.json`、`storage/notifications.json`

```bash
mysqldump -h127.0.0.1 -P3306 -uroot -p personal_agent > backups/mysql_personal_agent.sql
```

迁移到新机器：旧机备份 → 复制项目 → 导入 MySQL SQL → 还原 chroma / photos → 配置 `.env` → 启动（启动时自动补齐表结构）。

---

## 常见问题

**Q：影像上传后一直显示「解析中」？**
检查后端日志，多为视觉模型额度或 `VISION_MODEL_*` 配置问题。启动时的模型端点自检日志会打印实际生效的 `base_url`。

**Q：AI 对话报错或无回复？**
重点检查 `MODEL_BASE_URL`。未配置时会静默回退到 `https://api.openai.com/v1`，用第三方模型 key 调用会 401 或长时间超时（前端表现为 500）。后端启动时会对该情况打印明确告警。

**Q：请求长时间挂起最后超时？**
模型客户端已配置超时与重试（`LLM_TIMEOUT` / `LLM_MAX_RETRIES` / `VISION_TIMEOUT`，可在 `.env` 覆盖，默认 60s / 1 次）。若仍频繁超时，先确认 `base_url` 可达。

**Q：向量检索不可用？**
检查 `EMBEDDING_*` 配置。未配置时自动回退为纯实体条件检索，问答仍可工作但语义召回能力下降。

**Q：纪念日提醒没有出现？**
调度器每 6 小时才跑一轮，且需记忆中存有可解析日期。可用 `GET /api/proactive/anniversaries` 即时查询。

**Q：升级后表结构对不上（如缺 `display_name`）？**
无需手动处理。后端启动时会自动执行幂等增量迁移补列；仅当确实需要重建库时才运行 `python -m db.init_db`（**会清空所有数据**）。
