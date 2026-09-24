'use client';

/* eslint-disable @next/next/no-img-element */

import { motion } from 'framer-motion';
import type { PhotoItem } from '@/app/types';
import { imgUrl, formatDate } from '@/app/api';

interface Props {
  photo: PhotoItem;
  index: number;
  onOpen: (photoId: string) => void;
}

export default function PhotoTile({ photo, index, onOpen }: Props) {
  const ok = photo.parse_status === 'success';

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
        <img src={imgUrl(photo.image_url)} alt={photo.file_name} loading="lazy" />
        <div className="photo-veil">
          <span>💬 打开记忆对话</span>
        </div>
      </div>
      <div className="photo-meta">
        <div className="photo-name" title={photo.file_name}>
          {photo.file_name}
        </div>
        <div className="photo-date">📅 {photo.upload_time ? formatDate(photo.upload_time) : '暂无日期'}</div>
      </div>
    </motion.div>
  );
}
