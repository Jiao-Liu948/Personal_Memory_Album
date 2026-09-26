'use client';

/* eslint-disable @next/next/no-img-element */

import { motion } from 'framer-motion';
import type { AppNotification, Anniversary, YearlyRecap } from '@/app/types';
import { imgUrl, photoName } from '@/app/api';

interface PanelProps {
  notifications: AppNotification[];
  onMarkAllRead: () => void;
  onOpenPhoto: (photoId: string) => void;
  onClose: () => void;
}

const TYPE_META: Record<string, { icon: string; label: string }> = {
  anniversary: { icon: '🎂', label: '纪念日' },
  yearly_recap: { icon: '📅', label: '年度回忆' },
};

/** 纪念日提醒：事件 + 周年 + 相关照片 */
function AnniversaryBody({ payload, onOpenPhoto }: { payload: Anniversary; onOpenPhoto: (id: string) => void }) {
  const photos = payload.related_photo_ids ?? [];
  return (
    <>
      <p className="notif-text">{payload.days_text}（{payload.anniversary_date}，原日期 {payload.original_date}）</p>
      {photos.length > 0 && (
        <div className="refs-strip" style={{ marginTop: 10 }}>
          {photos.slice(0, 6).map((id) => (
            <div key={id} className="mini-thumb" onClick={() => onOpenPhoto(id)} title="查看这张照片">
              <img src={imgUrl(`/api/photo/image/${id}`)} alt="回忆照片" loading="lazy" />
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/** 年度回忆：调度器预生成好的故事 + 统计 + 照片（前端只读取成品） */
function YearlyRecapBody({ payload, onOpenPhoto }: { payload: YearlyRecap; onOpenPhoto: (id: string) => void }) {
  const stats = [
    { label: '照片', value: payload.total_photos ?? 0 },
    { label: '记忆', value: payload.total_memories ?? 0 },
  ];
  return (
    <>
      <p className="notif-text" style={{ whiteSpace: 'pre-wrap' }}>{payload.yearly_story}</p>
      <div className="notif-stats">
        {stats.map((s) => (
          <span key={s.label} className="notif-stat">
            <b>{s.value}</b>
            {s.label}
          </span>
        ))}
        {(payload.top_tags ?? []).slice(0, 4).map((t) => (
          <span key={t.tag} className="tag tag--0">{t.tag} × {t.count}</span>
        ))}
      </div>
      {(payload.photos ?? []).length > 0 && (
        <div className="refs-strip" style={{ marginTop: 12 }}>
          {payload.photos.slice(0, 8).map((p) => (
            <div key={p.photo_id} className="mini-thumb" onClick={() => onOpenPhoto(p.photo_id)} title={photoName(p)}>
              <img src={imgUrl(p.image_url)} alt={photoName(p)} loading="lazy" />
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default function NotificationPanel({
  notifications,
  onMarkAllRead,
  onOpenPhoto,
  onClose,
}: PanelProps) {
  const hasUnread = notifications.some((n) => !n.read);

  return (
    <motion.div
      className="overlay overlay--top"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      onClick={onClose}
    >
      <button className="overlay-close" onClick={onClose} aria-label="关闭提醒">
        ✕
      </button>

      <motion.div
        className="notif-panel"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 26, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.98 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
      >
        <div className="notif-head">
          <span>🔔 主动提醒</span>
          {hasUnread && (
            <button className="btn btn-ghost btn-sm" onClick={onMarkAllRead}>
              全部已读
            </button>
          )}
        </div>

        <div className="notif-list">
          {notifications.length === 0 ? (
            <div className="center-empty">
              <div className="em">🌙</div>
              <div style={{ fontWeight: 700 }}>暂时没有提醒</div>
              <p className="side-empty" style={{ marginTop: 8 }}>
                当纪念日临近，或新的一年来临时，我会主动在这里提醒你。
              </p>
            </div>
          ) : (
            notifications.map((n) => {
              const meta = TYPE_META[n.type] ?? { icon: '🔔', label: '提醒' };
              return (
                <div key={n.id} className={`notif-item ${n.read ? '' : 'notif-item--unread'}`}>
                  <div className="notif-item-head">
                    <span className="notif-icon">{meta.icon}</span>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div className="notif-title">{n.title}</div>
                      <div className="notif-meta">
                        {meta.label} · {n.created_at}
                      </div>
                    </div>
                    {!n.read && <span className="notif-new" />}
                  </div>

                  {n.type === 'anniversary' ? (
                    <AnniversaryBody payload={n.payload as unknown as Anniversary} onOpenPhoto={onOpenPhoto} />
                  ) : n.type === 'yearly_recap' ? (
                    <YearlyRecapBody payload={n.payload as unknown as YearlyRecap} onOpenPhoto={onOpenPhoto} />
                  ) : (
                    <p className="notif-text">{n.body}</p>
                  )}
                </div>
              );
            })
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
