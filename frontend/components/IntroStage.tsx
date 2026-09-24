'use client';

import { motion } from 'framer-motion';

interface Props {
  photoCount: number;
  onOpenAlbum: () => void;
  onOpenGlobalChat: () => void;
}

const FEATURES = [
  {
    icon: '🧠',
    title: '结构化记忆抽取',
    desc: '从照片画面与对话中自动抽取时间、地点、人物、事件、情感与标签，沉淀成可检索的事实记忆。',
  },
  {
    icon: '🔗',
    title: '跨照片智能推理',
    desc: '向量语义 + 实体条件双引擎检索，模糊提问也能跨越多张照片，回溯事件与人物关系。',
  },
  {
    icon: '👤',
    title: '人脸聚类识人',
    desc: '自动识别并聚类同一人物，为亲友建立人物档案；支持手动重命名，随时修正聚类误差。',
  },
  {
    icon: '⚖️',
    title: '记忆冲突消解',
    desc: '新旧信息冲突时自动合并、覆盖或归档，旧记忆标记失效而非删除，完整保留溯源。',
  },
  {
    icon: '🎂',
    title: '主动记忆运营',
    desc: '纪念日提醒、相似照片推荐、关键信息补全提问——不等你问，主动唤醒那些重要瞬间。',
  },
  {
    icon: '📅',
    title: '年度回忆生成',
    desc: '按年份汇总全部照片与记忆，自动生成时间线式的年度故事，回顾这一年的高光时刻。',
  },
];

const STEPS = [
  { no: 'STEP 01', title: '上传照片', desc: '支持 JPG / PNG / WebP，照片保存在你自己的设备上。' },
  { no: 'STEP 02', title: 'AI 自动解析', desc: '理解画面内容、提取拍摄信息、识别并聚类人脸。' },
  { no: 'STEP 03', title: '聊出故事', desc: '和照片对话补充细节，记忆会被自动抽取并沉淀。' },
  { no: 'STEP 04', title: '随时唤醒', desc: '全局提问、相似推荐、纪念日提醒，跨照片找回过去。' },
];

export default function IntroStage({
  photoCount,
  onOpenAlbum,
  onOpenGlobalChat,
}: Props) {
  return (
    <div className="intro wrap">
      {/* 开场 */}
      <section className="hero">
        <motion.div
          className="hero-pill"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <span className="dot-live" />
          Personal Memory Agent
        </motion.div>

        <motion.h1
          className="hero-title"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.05 }}
        >
          你的专属记忆智能体
        </motion.h1>

        <motion.p
          className="hero-sub"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.12 }}
        >
          照片会记得，我也会。把照片交给我，我会读懂画面里的人和故事；
          你随口讲过的细节，都会被沉淀成可以被随时唤醒的记忆。
        </motion.p>
      </section>

      {/* 纪念日提醒已统一到顶部「主动提醒」通知位（后端调度器触发），这里不再重复展示 */}

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

      {/* 使用流程 */}
      <div className="section-label">怎么用</div>
      <div className="steps">
        {STEPS.map((s, i) => (
          <motion.div
            key={s.no}
            className="step"
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.45, delay: i * 0.07 }}
          >
            <div className="step-no">{s.no}</div>
            <h4>{s.title}</h4>
            <p>{s.desc}</p>
          </motion.div>
        ))}
      </div>

      {/* 结尾：大按钮 */}
      <motion.div
        className="cta"
        initial={{ opacity: 0, y: 26 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.4 }}
        transition={{ duration: 0.5 }}
      >
        <button className="cta-btn" onClick={onOpenAlbum}>
          <span style={{ fontSize: 22 }}>📁</span>
          创建我的个人回忆相册
        </button>
        <div className="cta-note">
          {photoCount > 0
            ? `相册里已经有 ${photoCount} 张照片，随时可以继续补充`
            : '所有照片与记忆都保存在本地，不上传云端'}
        </div>
        <button className="cta-secondary" onClick={onOpenGlobalChat}>
          🧠 直接开始全局记忆问答
        </button>
      </motion.div>
    </div>
  );
}
