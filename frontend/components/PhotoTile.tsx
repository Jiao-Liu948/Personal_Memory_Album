'use client';

/* eslint-disable @next/next/no-img-element */

import { useRef } from 'react';
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from 'framer-motion';
import type { PhotoItem } from '@/app/types';
import { imgUrl, formatDate, photoName } from '@/app/api';

interface Props {
  photo: PhotoItem;
  index: number;
  onOpen: (photoId: string) => void;
  onRename: (photoId: string) => void;
}

/** 最大倾斜角度（度）。想更强/更弱改这里就行 */
const MAX_TILT = 11;
/** 回弹/跟随的弹簧参数，越小越"跟手" */
const TILT_SPRING = { stiffness: 260, damping: 22, mass: 0.6 };

export default function PhotoTile({ photo, index, onOpen, onRename }: Props) {
  const ok = photo.parse_status === 'success';
  const name = photoName(photo);
  const custom = (photo.display_name || '').trim();
  const reduceMotion = useReducedMotion();

  const ref = useRef<HTMLDivElement>(null);

  // 光标在卡片内的归一化位置：0 = 左/上边缘，0.5 = 中心，1 = 右/下边缘
  const pointerX = useMotionValue(0.5);
  const pointerY = useMotionValue(0.5);

  // 鼠标所在的那一侧翘起（与 vanilla-tilt 的方向约定一致）
  const rotateX = useSpring(useTransform(pointerY, [0, 1], [-MAX_TILT, MAX_TILT]), TILT_SPRING);
  const rotateY = useSpring(useTransform(pointerX, [0, 1], [-MAX_TILT, MAX_TILT]), TILT_SPRING);

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    // 只响应鼠标：触屏拖动如果跟着倾斜，会和页面滚动打架
    if (reduceMotion || e.pointerType !== 'mouse') return;
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    pointerX.set((e.clientX - rect.left) / rect.width);
    pointerY.set((e.clientY - rect.top) / rect.height);
  };

  const resetTilt = () => {
    pointerX.set(0.5);
    pointerY.set(0.5);
  };

  return (
    // 外层：负责入场动画与 hover 上浮
    <motion.div
      className="photo-slot"
      initial={{ opacity: 0, y: 54, scale: 0.86 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      whileHover={{ y: -6, transition: { type: 'spring', stiffness: 320, damping: 24 } }}
      transition={{
        delay: 0.42 + Math.min(index * 0.06, 0.7),
        type: 'spring',
        stiffness: 210,
        damping: 21,
      }}
    >
      {/* 内层：负责 3D 跟随倾斜。与入场动画分层，避免 transform 互相覆盖 */}
      <motion.div
        ref={ref}
        className="photo"
        style={{ rotateX, rotateY, transformPerspective: 900 }}
        onPointerMove={handlePointerMove}
        onPointerLeave={resetTilt}
        onClick={() => onOpen(photo.photo_id)}
      >
        <div className="photo-img">
          <span className={`photo-badge ${ok ? 'photo-badge--ok' : 'photo-badge--wait'}`}>
            {ok ? '✓ 已解析' : '◷ 解析中'}
          </span>
          <img src={imgUrl(photo.image_url)} alt={name} loading="lazy" />
          <div className="photo-veil">
            <span>💬 打开记忆对话</span>
            <button
              className="photo-rename-btn"
              title="为这张照片命名"
              aria-label="为这张照片命名"
              onClick={(e) => {
                e.stopPropagation();
                onRename(photo.photo_id);
              }}
            >
              ✏️
            </button>
          </div>
        </div>
        <div className="photo-meta">
          <div className={`photo-name ${custom ? 'photo-name--custom' : ''}`} title={name}>
            {name}
          </div>
          <div className="photo-date">📅 {photo.upload_time ? formatDate(photo.upload_time) : '暂无日期'}</div>
        </div>
      </motion.div>
    </motion.div>
  );
}
