'use client';

/* eslint-disable @next/next/no-img-element */

import { motion } from 'framer-motion';
import type { PhotoItem } from '@/app/types';
import { imgUrl, formatDate, photoName } from '@/app/api';

interface Props {
  photo: PhotoItem;
  index: number;
  onOpen: (photoId: string) => void;
  onRename: (photoId: string) => void;
}

export default function PhotoTile({ photo, index, onOpen, onRename }: Props) {
  const ok = photo.parse_status === 'success';
  const name = photoName(photo);
  const custom = (photo.display_name || '').trim();

  return (
    <motion.div
      className="photo"
      style={{ transformPerspective: 900 }}
      initial={{ opacity: 0, y: 54, scale: 0.86, rotateX: -28 }}
      animate={{ opacity: 1, y: 0, scale: 1, rotateX: 0 }}
      transition={{
        delay: 0.42 + Math.min(index * 0.06, 0.7),
        type: 'spring',
        stiffness: 210,
        damping: 21,
      }}
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
  );
}
