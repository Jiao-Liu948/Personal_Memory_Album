'use client';

import { useRef } from 'react';
import { motion } from 'framer-motion';
import type { PhotoItem } from '@/app/types';
import PhotoTile from './PhotoTile';

interface Props {
  photos: PhotoItem[];
  loading: boolean;
  uploading: boolean;
  onClose: () => void;
  onOpenPhoto: (photoId: string) => void;
  onUpload: (file: File) => void;
  onRenamePhoto: (photoId: string) => void;
}

export default function AlbumFolder({
  photos,
  loading,
  uploading,
  onClose,
  onOpenPhoto,
  onUpload,
  onRenamePhoto,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  const pick = () => fileRef.current?.click();

  return (
    <motion.div
      className="overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.28 }}
      onClick={onClose}
    >
      <button className="overlay-close" onClick={onClose} aria-label="关闭相册">
        ✕
      </button>

      <motion.div
        className="folder-stage"
        onClick={(e) => e.stopPropagation()}
        initial={{ scale: 0.5, y: 190, opacity: 0 }}
        animate={{ scale: 1, y: 0, opacity: 1 }}
        exit={{ scale: 0.55, y: 170, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 150, damping: 19 }}
      >
        {/* 文件选择框必须放在 .folder-stage 内部：
            input.click() 会产生一个「会冒泡」的 click 事件，
            若它挂在 overlay 之下，事件会冒泡到 overlay 的 onClose，
            导致弹层在用户选图之前就被卸载，选中的文件永远提交不出去。 */}
        <input
          ref={fileRef}
          type="file"
          accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
          className="sr-only"
          tabIndex={-1}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = '';
          }}
        />

        <div className="folder">
          <div className="folder-tab" />

          <div className="folder-back">
            <div className="folder-title">
              <h2>🗂️ 影像资产库</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span className="folder-count">{photos.length} 项资产</span>
                <button className="btn btn-glass btn-sm" onClick={pick} disabled={uploading}>
                  {uploading ? '解析中…' : '＋ 导入影像'}
                </button>
              </div>
            </div>

            {uploading && (
              <div className="uploading">
                <span className="spinner" />
                正在执行解析管线：视觉理解 → 人脸聚类 → 记忆抽取，请稍候…
              </div>
            )}

            {loading && photos.length === 0 ? (
              <div className="folder-grid">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="skel" />
                ))}
              </div>
            ) : photos.length === 0 ? (
              <div className="empty-folder">
                <div className="empty-art">🗂️</div>
                <h3>资产库还是空的</h3>
                <p>
                  导入第一批影像，系统会自动完成元数据解析、画面理解与人脸聚类，
                  并把可复用的信息沉淀为结构化记忆，供后续检索与问答使用。
                </p>
                <button className="btn btn-primary" onClick={pick} disabled={uploading}>
                  📤 导入第一批影像
                </button>
                <p className="hint" style={{ marginTop: 12 }}>
                  支持 JPG / PNG / WebP
                </p>
              </div>
            ) : (
              <div className="folder-grid">
                {photos.map((p, i) => (
                  <PhotoTile
                    key={p.photo_id}
                    photo={p}
                    index={i}
                    onOpen={onOpenPhoto}
                    onRename={onRenamePhoto}
                  />
                ))}
              </div>
            )}
          </div>

          {/* 文件夹前盖：开局盖住内容，随后向下翻开并淡出 */}
          <motion.div
            className="folder-lid"
            initial={{ rotateX: 0, opacity: 1 }}
            animate={{ rotateX: -112, opacity: 0 }}
            transition={{
              rotateX: { duration: 1, delay: 0.3, ease: [0.22, 1, 0.36, 1] },
              opacity: { duration: 0.42, delay: 0.78, ease: 'easeIn' },
            }}
          >
            <span className="folder-lid-sheen" />
            <span className="folder-hint">
              <span className="big">🗂️</span>
              正在打开影像资产库…
            </span>
          </motion.div>
        </div>
      </motion.div>
    </motion.div>
  );
}
