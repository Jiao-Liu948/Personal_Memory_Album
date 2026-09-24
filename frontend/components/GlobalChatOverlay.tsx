'use client';

/* eslint-disable @next/next/no-img-element */

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import type { ChatMessage, PhotoItem } from '@/app/types';
import { imgUrl } from '@/app/api';
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
            <span>🧠 全局记忆问答</span>
            <button className="btn btn-ghost btn-sm" onClick={onClear}>
              🗑️ 清空
            </button>
          </div>

          <div className="chat-scroll" ref={scrollRef}>
            {history.length === 0 && !loading ? (
              <div className="center-empty">
                <div className="em">🔮</div>
                <div style={{ fontWeight: 700 }}>跨照片，问我任何关于你过去的问题</div>
                <p className="side-empty" style={{ marginTop: 8 }}>
                  比如「我去年去了哪些地方旅行？」「我和家人有哪些合照？」
                  我会检索你所有的照片与记忆，把散落的回忆串起来。
                </p>
              </div>
            ) : (
              history.map((m, i) => <MessageBubble key={i} message={m} />)
            )}

            {loading && <Typing text="正在检索你的记忆..." />}

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
                      title={p.file_name}
                    >
                      <img src={imgUrl(p.image_url)} alt={p.file_name} loading="lazy" />
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
