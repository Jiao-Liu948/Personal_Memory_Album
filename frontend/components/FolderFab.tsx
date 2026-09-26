'use client';

import { motion } from 'framer-motion';

interface Props {
  count: number;
  onClick: () => void;
}

export default function FolderFab({ count, onClick }: Props) {
  return (
    <motion.button
      className="fab"
      onClick={onClick}
      aria-label="打开影像资产库"
      initial={{ opacity: 0, y: 70, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 70, scale: 0.9 }}
      transition={{ delay: 0.35, type: 'spring', stiffness: 190, damping: 20 }}
    >
      <span className="fab-icon">
        <span className="fab-tab" />
        <svg
          width="21"
          height="21"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#ffffff"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="3" y="4" width="18" height="16" rx="3" />
          <circle cx="8.5" cy="9.5" r="1.5" />
          <path d="M21 15.5l-4.5-4.5L12 15.5l-2.2-2.2L4 19" />
        </svg>
        {count > 0 && <span className="fab-badge">{count}</span>}
      </span>
      <span className="fab-text">
        <span className="fab-label">影像资产库</span>
        <span className="fab-count">
          {count > 0 ? `${count} 项资产 · 点击展开` : '暂无资产 · 点击导入'}
        </span>
      </span>
    </motion.button>
  );
}
