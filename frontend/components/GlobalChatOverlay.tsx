'use client';

/* eslint-disable @next/next/no-img-element */

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import type { ChatMessage, PhotoItem } from '@/app/types';
import { imgUrl, photoName } from '@/app/api';
import MessageBubble from './MessageBubble';
import Typing from './Typing';

interface Props {
  history: ChatMessage[];
  relatedPhotos: PhotoItem[];
  loading: boolean;
  inputText: string;
  onInputChange: (v: string) => void;
  onSend: () => void;
  onClear: () => void;
  onOpenPhoto: (photoId: string) => void;
  onClose: () => void;
}

export default function GlobalChatOverlay({
  history,
  relatedPhotos,
  loading,
  inputText,
  onInputChange,
  onSend,
  onClear,
  onOpenPhoto,
  onClose,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [history.length, relatedPhotos.length, loading]);

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <motion.div
      className="overlay overlay--top"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.26 }}
      onClick={onClose}
    >
      <button className="overlay-close" onClick={onClose} aria-label="关闭全局问答">
        ✕
      </button>

      <motion.div
        className="global-chat"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 28, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 22, scale: 0.97 }}
        transition={{ duration: 0.34, ease: 'easeOut' }}
      >
        <section className="panel chat-panel">
          <div className="panel-head" style={{ justifyContent: 'space-between' }}>
            <span>🧠 跨影像知识问答</span>
            <button className="btn btn-ghost btn-sm" onClick={onClear}>
              🗑️ 清空
            </button>
          </div>

          <div className="chat-scroll" ref={scrollRef}>
            {history.length === 0 && !loading ? (
              <div className="center-empty">
                <div className="em">🔮</div>
                <div style={{ fontWeight: 700 }}>跨影像检索，直接提问即可</div>
                <p className="side-empty" style={{ marginTop: 8 }}>
                  例如「去年去过哪些地方」「和谁一起拍的合照」——
                  系统会用实体条件匹配叠加语义向量检索，把分散在各张影像上的信息聚合起来。
                </p>
              </div>
            ) : (
              history.map((m, i) => <MessageBubble key={i} message={m} />)
            )}

            {loading && <Typing text="正在检索知识库..." />}

            {relatedPhotos.length > 0 && (
              <motion.div
                className="refs"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="refs-title">📎 本次回答引用的照片</div>
                <div className="refs-strip">
                  {relatedPhotos.map((p) => (
                    <div
                      key={p.photo_id}
                      className="mini-thumb"
                      onClick={() => onOpenPhoto(p.photo_id)}
                      title={photoName(p)}
                    >
                      <img src={imgUrl(p.image_url)} alt={photoName(p)} loading="lazy" />
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>

          <div className="chat-foot">
            <div className="chat-input-row">
              <input
                className="field"
                value={inputText}
                onChange={(e) => onInputChange(e.target.value)}
                onKeyDown={handleKey}
                placeholder="问我任何关于你过去的问题…"
              />
              <button className="btn btn-primary" onClick={onSend} disabled={loading || !inputText.trim()}>
                发送
              </button>
            </div>
          </div>
        </section>
      </motion.div>
    </motion.div>
  );
}
