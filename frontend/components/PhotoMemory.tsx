'use client';

/* eslint-disable @next/next/no-img-element */

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import type { PhotoItem, MemoryFact, Person, ChatMessage } from '@/app/types';
import { imgUrl, tagClass, photoName } from '@/app/api';
import MessageBubble from './MessageBubble';
import Typing from './Typing';

interface Props {
  photoId: string;
  photo?: PhotoItem;
  chatHistory: ChatMessage[];
  memoryFacts: MemoryFact[];
  persons: Person[];
  similarPhotos: PhotoItem[];
  loading: boolean;
  inputText: string;
  onInputChange: (v: string) => void;
  onSend: () => void;
  onRenamePerson: (personId: string) => void;
  onRenamePhoto: (photoId: string, name?: string) => void;
  onOpenPhoto: (photoId: string) => void;
  onClose: () => void;
}

const EMOTION_ICON: Record<string, string> = {
  开心: '😄',
  感动: '🥹',
  遗憾: '😢',
  平淡: '😐',
  其他: '🙂',
};

export default function PhotoMemory({
  photoId,
  photo,
  chatHistory,
  memoryFacts,
  persons,
  similarPhotos,
  loading,
  inputText,
  onInputChange,
  onSend,
  onRenamePerson,
  onRenamePhoto,
  onOpenPhoto,
  onClose,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState('');

  const displayName = photoName(photo || { file_name: '照片' });

  const startEditName = () => {
    // 预填当前自定义名；没自定义过就预填原始文件名，方便直接改
    setNameDraft((photo?.display_name || '').trim() || photo?.file_name || '');
    setEditingName(true);
  };

  const submitName = () => {
    onRenamePhoto(photoId, nameDraft.trim());
    setEditingName(false);
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [chatHistory.length, loading]);

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
      transition={{ duration: 0.25 }}
      onClick={onClose}
    >
      <button className="overlay-close" onClick={onClose} aria-label="关闭照片记忆">
        ✕
      </button>

      <motion.div
        className="memory-layout"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 26, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.98 }}
        transition={{ duration: 0.32, ease: 'easeOut' }}
      >
        {/* 左侧：照片 + 记忆 + 人物 + 相似 */}
        <aside style={{ minWidth: 0 }}>
          <div className="memory-photo">
            <img src={imgUrl(`/api/photo/image/${photoId}`)} alt={displayName} />
            <div className="memory-photo-cap" onClick={(e) => e.stopPropagation()}>
              {editingName ? (
                <div className="name-edit">
                  <input
                    className="name-input"
                    value={nameDraft}
                    autoFocus
                    maxLength={60}
                    placeholder="给这张照片起个名字…"
                    onChange={(e) => setNameDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') submitName();
                      if (e.key === 'Escape') setEditingName(false);
                    }}
                  />
                  <button className="name-btn name-btn--ok" onClick={submitName}>
                    保存
                  </button>
                  <button className="name-btn" onClick={() => setEditingName(false)}>
                    取消
                  </button>
                </div>
              ) : (
                <div className="name-row">
                  <span className="name-text" title={displayName}>
                    {displayName}
                  </span>
                  <button
                    className="name-edit-btn"
                    title="为这张照片命名"
                    aria-label="为这张照片命名"
                    onClick={startEditName}
                  >
                    ✏️
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="side-card">
            <div className="side-title">📌 自动抽取的记忆</div>
            {memoryFacts.length === 0 ? (
              <p className="side-empty">对话中补充故事后，这里会自动生成结构化记忆。</p>
            ) : (
              memoryFacts.map((f) => (
                <div key={f.fact_id} className="fact">
                  {f.tags?.length > 0 && (
                    <div className="fact-tags">
                      {f.tags.map((t, i) => (
                        <span key={i} className={`tag ${tagClass(t)}`}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="fact-event">{f.event || '暂无事件描述'}</div>
                  <div className="fact-info">
                    {f.location && <span>📍 {f.location}</span>}
                    {f.time_info && <span>🕐 {f.time_info}</span>}
                    {f.emotion && <span>{EMOTION_ICON[f.emotion] || '🙂'} {f.emotion}</span>}
                    {f.person_relation && <span>👥 {f.person_relation}</span>}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="side-card">
            <div className="side-title">👤 识别人物 · 点击重命名</div>
            {persons.length === 0 ? (
              <p className="side-empty">未识别到人脸</p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {persons.map((p) => (
                  <span key={p.person_id} className="person" onClick={() => onRenamePerson(p.person_id)}>
                    <span className="person-avatar">{p.name?.[0] || '?'}</span>
                    {p.name}
                  </span>
                ))}
              </div>
            )}
          </div>

          {similarPhotos.length > 0 && (
            <div className="side-card">
              <div className="side-title">🔗 相似照片</div>
              <div className="refs-strip">
                {similarPhotos.map((p) => (
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
            </div>
          )}
        </aside>

        {/* 右侧：和这张照片的对话 */}
        <section className="panel chat-panel">
          <div className="panel-head">💬 和这张照片聊聊</div>
          <div className="chat-scroll" ref={scrollRef}>
            {chatHistory.length === 0 ? (
              <div className="center-empty">
                <div className="em">💬</div>
                <div style={{ fontWeight: 700 }}>开始和这张照片对话吧</div>
                <p className="side-empty" style={{ marginTop: 8 }}>
                  问我这张照片里有什么，或者讲讲它背后的故事，我会帮你记住。
                </p>
              </div>
            ) : (
              chatHistory.map((m, i) => <MessageBubble key={i} message={m} />)
            )}
            {loading && <Typing text="正在回忆..." />}
          </div>
          <div className="chat-foot">
            <div className="chat-input-row">
              <input
                className="field"
                value={inputText}
                onChange={(e) => onInputChange(e.target.value)}
                onKeyDown={handleKey}
                placeholder="问我这张照片的问题，或补充背后的故事…"
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
