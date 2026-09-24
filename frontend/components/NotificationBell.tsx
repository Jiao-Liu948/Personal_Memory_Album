'use client';

import { motion } from 'framer-motion';

interface Props {
  unread: number;
  onClick: () => void;
}

/**
 * 主动提醒入口：只做展示。
 * 红点表示后端调度器已经判定出「有值得提醒你的事」，点击查看详情。
 * 这里不提供任何「生成/触发」能力——纪念日和年度回忆都由后端事件驱动。
 */
export default function NotificationBell({ unread, onClick }: Props) {
  return (
    <button className="bell" onClick={onClick} aria-label="主动提醒" title="主动提醒">
      <svg
        width="17"
        height="17"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.7 21a2 2 0 0 1-3.4 0" />
      </svg>
      <span>提醒</span>
      {unread > 0 && (
        <motion.span
          className="bell-dot"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 520, damping: 18 }}
        >
          {unread > 99 ? '99+' : unread}
        </motion.span>
      )}
    </button>
  );
}
