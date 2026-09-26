'use client';

import { motion } from 'framer-motion';
import type { SystemOverview as Overview } from '@/app/types';
import { tagClass } from '@/app/api';

interface Props {
  overview: Overview | null;
  onOpenAlbum: () => void;
  onOpenGlobalChat: () => void;
}

/** 记忆来源的可读标签 */
const SOURCE_LABEL: Record<string, string> = {
  vision: '视觉解析',
  chat: '对话抽取',
  user_supplement: '用户补充',
  merged: '合并归档',
};

const MODEL_LABEL: Record<'chat' | 'vision' | 'embedding', string> = {
  chat: '语言模型',
  vision: '视觉模型',
  embedding: '向量模型',
};

const CAPABILITIES: { key: 'vector_search' | 'face_cluster' | 'proactive'; label: string }[] = [
  { key: 'vector_search', label: '语义向量检索' },
  { key: 'face_cluster', label: '人脸聚类' },
  { key: 'proactive', label: '主动提醒调度' },
];

const FEATURES = [
  {
    icon: '🧩',
    title: '多模态解析管线',
    desc: 'EXIF 元数据、视觉语义理解、人脸检测聚类多路并行，影像入库即完成结构化，无需人工录入。',
  },
  {
    icon: '🗂️',
    title: '结构化记忆沉淀',
    desc: '按时间 / 地点 / 事件 / 人物 / 情感 / 标签六维 schema 落库，每条记忆绑定影像与原始上下文，可溯源。',
  },
  {
    icon: '🔀',
    title: '双引擎融合检索',
    desc: '实体条件匹配度与向量语义相似度按查询意图加权融合排序，模糊提问也能跨影像回溯。',
  },
  {
    icon: '⚖️',
    title: '记忆冲突消解',
    desc: '新旧记忆语义比对后自动合并 / 覆盖 / 归档，历史版本标记失效而非物理删除，保留完整变更轨迹。',
  },
  {
    icon: '🔔',
    title: '主动知识运营',
    desc: '纪念日提醒、相似影像推荐、年度时间线生成，全部由后端调度器按事件驱动，不依赖用户主动查询。',
  },
  {
    icon: '📉',
    title: '上下文成本控制',
    desc: '长对话自动摘要压缩以控制 Token 占用，配合全链路统一日志与模型调用链追踪。',
  },
];

export default function SystemOverview({ overview, onOpenAlbum, onOpenGlobalChat }: Props) {
  const assets = overview?.assets;
  const knowledge = overview?.knowledge;
  const timeline = overview?.timeline ?? [];
  const pipeline = overview?.pipeline ?? [];
  const topTags = overview?.top_tags ?? [];
  const sources = overview?.sources ?? [];
  const assetCount = assets?.total ?? 0;
  const maxCount = Math.max(1, ...timeline.map((d) => d.count));
  const sourceTotal = sources.reduce((sum, s) => sum + s.count, 0);

  const metrics = [
    { label: '影像资产', value: assetCount, unit: '张', sub: `解析成功率 ${assets?.parse_rate ?? 0}%` },
    { label: '人物实体', value: knowledge?.persons ?? 0, unit: '人', sub: '人脸聚类去重' },
    { label: '记忆条目', value: knowledge?.facts ?? 0, unit: '条', sub: `覆盖 ${knowledge?.linked_photos ?? 0} 张影像` },
    { label: '知识维度', value: knowledge?.tags ?? 0, unit: '类', sub: `${knowledge?.locations ?? 0} 个地点` },
  ];

  return (
    <div className="overview wrap">
      {/* 系统定位 */}
      <section className="hero">
        <motion.div
          className="hero-pill"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <span className="dot-live" />
          Multimodal Image Knowledge Agent
        </motion.div>

        <motion.h1
          className="hero-title"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.05 }}
        >
          多模态影像知识管理智能体
        </motion.h1>

        <motion.p
          className="hero-sub"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.12 }}
        >
          把零散的影像资料转化为可检索、可推理、可追溯的结构化知识资产：
          入库即自动完成元数据解析、视觉理解与人脸聚类；对话中口述的事实被抽取沉淀为长期记忆，
          并以实体条件 + 语义向量双引擎支撑跨影像的自然语言问答。
        </motion.p>
      </section>

      {/* 运行概览 */}
      <div className="section-label">运行概览</div>
      <div className="metrics">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            className="metric"
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.4, delay: i * 0.06 }}
          >
            <div className="metric-label">{m.label}</div>
            <div className="metric-value">
              {m.value}
              <span>{m.unit}</span>
            </div>
            <div className="metric-sub">{m.sub}</div>
          </motion.div>
        ))}
      </div>

      {/* 处理管线 */}
      <div className="section-label">自动化处理管线</div>
      <div className="pipeline-card">
        <div className="pipeline">
          {pipeline.map((s, i) => (
            <div key={s.stage} className="pipe-node">
              <div className="pipe-idx">{String(i + 1).padStart(2, '0')}</div>
              <div className="pipe-stage">{s.stage}</div>
              <div className="pipe-value">
                {s.value}
                <span>{s.unit}</span>
              </div>
              {i < pipeline.length - 1 && <span className="pipe-arrow">›</span>}
            </div>
          ))}
        </div>

        <div className="chart-wrap">
          <div className="chart-title">近 7 天入库量</div>
          <div className="chart">
            {timeline.map((d) => (
              <div key={d.date} className="chart-col" title={`${d.date}：${d.count} 张`}>
                <div
                  className="chart-bar"
                  style={{ height: `${Math.max(5, (d.count / maxCount) * 100)}%` }}
                />
                <span className="chart-label">{d.date.slice(5)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 知识与来源 */}
      <div className="overview-grid">
        <div className="panel">
          <div className="panel-head">知识标签分布</div>
          <div className="panel-body">
            {topTags.length === 0 ? (
              <p className="side-empty">暂无标签数据，导入影像后将自动生成。</p>
            ) : (
              <div className="tag-cloud">
                {topTags.map((t) => (
                  <span key={t.tag} className={`tag ${tagClass(t.tag)}`}>
                    {t.tag} × {t.count}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">记忆来源构成</div>
          <div className="panel-body">
            {sources.length === 0 ? (
              <p className="side-empty">暂无记忆条目。</p>
            ) : (
              <div className="source-list">
                {sources.map((s) => {
                  const pct = sourceTotal ? Math.round((s.count / sourceTotal) * 100) : 0;
                  return (
                    <div key={s.source} className="source-row">
                      <span className="source-name">{SOURCE_LABEL[s.source] ?? s.source}</span>
                      <span className="source-bar">
                        <i style={{ width: `${pct}%` }} />
                      </span>
                      <span className="source-pct">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 运行环境 */}
      <div className="section-label">运行环境</div>
      <div className="runtime">
        {(['chat', 'vision', 'embedding'] as const).map((k) => {
          const m = overview?.models?.[k];
          return (
            <div key={k} className="runtime-item">
              <div className="runtime-head">
                <span className="runtime-name">{MODEL_LABEL[k]}</span>
                <span className={`rt-dot ${m?.configured ? 'rt-dot--on' : ''}`} />
              </div>
              <div className="runtime-model" title={m?.name}>
                {m?.name || '未配置'}
              </div>
              <div className="runtime-url" title={m?.base_url}>
                {m?.base_url || '—'}
              </div>
            </div>
          );
        })}
      </div>

      <div className="caps">
        {CAPABILITIES.map((c) => {
          const on = Boolean(overview?.capabilities?.[c.key]);
          return (
            <span key={c.key} className={`cap ${on ? 'cap--on' : ''}`}>
              {on ? '●' : '○'} {c.label}
            </span>
          );
        })}
      </div>

      {/* 核心能力 */}
      <div className="section-label">核心能力</div>
      <div className="features">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            className="feature"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.45, delay: (i % 3) * 0.08 }}
          >
            <div className="feature-ico">{f.icon}</div>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
          </motion.div>
        ))}
      </div>

      {/* 入口 */}
      <motion.div
        className="cta"
        initial={{ opacity: 0, y: 26 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.4 }}
        transition={{ duration: 0.5 }}
      >
        <button className="cta-btn" onClick={onOpenAlbum}>
          <span style={{ fontSize: 22 }}>🗂️</span>
          进入影像资产库
        </button>
        <div className="cta-note">
          {assetCount > 0
            ? `已纳管 ${assetCount} 张影像，持续沉淀结构化知识`
            : '尚无影像资产，导入第一批影像即可启动解析管线'}
        </div>
        <button className="cta-secondary" onClick={onOpenGlobalChat}>
          🧠 跨影像知识问答
        </button>
        {overview?.generated_at && <div className="overview-stamp">指标更新于 {overview.generated_at}</div>}
      </motion.div>
    </div>
  );
}
