'use client';

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { AnimatePresence } from 'framer-motion';
import { API_BASE, describeApiError } from './api';
import type { PhotoItem, MemoryFact, Person, ChatMessage, AppNotification } from './types';
import IntroStage from '@/components/IntroStage';
import FolderFab from '@/components/FolderFab';
import AlbumFolder from '@/components/AlbumFolder';
import GlobalChatOverlay from '@/components/GlobalChatOverlay';
import PhotoMemory from '@/components/PhotoMemory';
import NotificationBell from '@/components/NotificationBell';
import NotificationPanel from '@/components/NotificationPanel';

export default function Home() {
  // ===== 相册文件夹 =====
  const [albumOpen, setAlbumOpen] = useState(false);
  const [photoList, setPhotoList] = useState<PhotoItem[]>([]);
  const [photoLoading, setPhotoLoading] = useState(true);
  const [uploadLoading, setUploadLoading] = useState(false);

  // ===== 全局记忆问答（独立弹层）=====
  const [globalChatOpen, setGlobalChatOpen] = useState(false);
  const [globalHistory, setGlobalHistory] = useState<ChatMessage[]>([]);
  const [globalInput, setGlobalInput] = useState('');
  const [globalLoading, setGlobalLoading] = useState(false);
  const [globalRelatedPhotos, setGlobalRelatedPhotos] = useState<PhotoItem[]>([]);

  // ===== 单照片记忆对话 =====
  const [activePhotoId, setActivePhotoId] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [memoryFacts, setMemoryFacts] = useState<MemoryFact[]>([]);
  const [persons, setPersons] = useState<Person[]>([]);
  const [similarPhotos, setSimilarPhotos] = useState<PhotoItem[]>([]);

  // ===== 主动提醒（后端调度器触发，前端只读展示）=====
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifyOpen, setNotifyOpen] = useState(false);

  const currentPhoto = photoList.find((p) => p.photo_id === activePhotoId);

  // ---------- 数据加载 ----------
  const loadPhotoList = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/photo/list`);
      setPhotoList(res.data ?? []);
    } catch (err) {
      console.error('加载照片列表失败', err);
    } finally {
      setPhotoLoading(false);
    }
  }, []);

  const loadNotifications = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/proactive/notifications`);
      setNotifications(res.data?.notifications ?? []);
      setUnreadCount(res.data?.unread_count ?? 0);
    } catch (err) {
      console.error('加载主动提醒失败', err);
    }
  }, []);

  const loadGlobalHistory = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/global/history`);
      setGlobalHistory(res.data?.history ?? []);
    } catch (err) {
      console.error('加载全局对话失败', err);
    }
  }, []);

  useEffect(() => {
    // 首次进入时并行拉取相册 / 主动提醒 / 历史问答；
    // 各 loader 内的 setState 都在 await 之后，属于异步加载而非同步级联渲染。
    loadPhotoList();
    loadNotifications();
    loadGlobalHistory();
  }, [loadPhotoList, loadNotifications, loadGlobalHistory]);

  // 提醒由后端调度器异步产出，前端定时轮询即可（红点不要求秒级实时）
  useEffect(() => {
    const timer = setInterval(loadNotifications, 60000);
    return () => clearInterval(timer);
  }, [loadNotifications]);

  // ---------- 相册 ----------
  const handleUpload = async (file: File) => {
    setUploadLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      // 上传接口要串行执行「视觉解析 + 人脸聚类 + 记忆抽取 + 生成开场白」，
      // 耗时明显长于普通对话，这里单独放宽超时，避免解析还没结束就被前端掐断。
      await axios.post(`${API_BASE}/api/photo/upload`, formData, { timeout: 300000 });
      await loadPhotoList();
      await loadNotifications(); // 新照片可能带来新的纪念日提醒
    } catch (err) {
      console.error('上传失败', err);
      alert(describeApiError(err));
    } finally {
      setUploadLoading(false);
    }
  };

  // ---------- 全局记忆问答（独立入口）----------
  const openGlobalChat = () => {
    setGlobalChatOpen(true);
    setGlobalRelatedPhotos([]);
    loadGlobalHistory();
  };

  const sendGlobalMessage = async () => {
    const text = globalInput.trim();
    if (!text || globalLoading) return;
    setGlobalInput('');
    setGlobalHistory((prev) => [...prev, { role: 'user', content: text }]);
    setGlobalLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/global/chat?query=${encodeURIComponent(text)}`);
      setGlobalHistory((prev) => [...prev, { role: 'assistant', content: res.data.reply }]);
      setGlobalRelatedPhotos(res.data?.related_photos ?? []);
    } catch (err) {
      console.error('全局问答失败', err);
      setGlobalHistory((prev) => [...prev, { role: 'assistant', content: describeApiError(err) }]);
    } finally {
      setGlobalLoading(false);
    }
  };

  const clearGlobalHistory = async () => {
    try {
      await axios.delete(`${API_BASE}/api/global/history`);
      setGlobalHistory([]);
      setGlobalRelatedPhotos([]);
    } catch (err) {
      console.error('清空全局对话失败', err);
    }
  };

  // ---------- 主动提醒（只读）----------
  const openNotifications = () => {
    setNotifyOpen(true);
    loadNotifications();
  };

  const markAllNotificationsRead = async () => {
    try {
      await axios.post(`${API_BASE}/api/proactive/notifications/read`);
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('标记已读失败', err);
    }
  };

  // ---------- 单照片记忆对话 ----------
  const openPhoto = async (photoId: string) => {
    setActivePhotoId(photoId);
    setChatHistory([]);
    setMemoryFacts([]);
    setPersons([]);
    setSimilarPhotos([]);
    try {
      const [chatRes, memRes, personRes, similarRes] = await Promise.all([
        axios.get(`${API_BASE}/api/chat/history?photo_id=${photoId}`),
        axios.get(`${API_BASE}/api/memory/photo?photo_id=${photoId}`),
        axios.get(`${API_BASE}/api/photo/persons?photo_id=${photoId}`),
        axios.get(`${API_BASE}/api/proactive/similar-photos?photo_id=${photoId}&top_k=4`),
      ]);
      setChatHistory(chatRes.data?.history ?? []);
      setMemoryFacts(memRes.data?.facts ?? []);
      setPersons(personRes.data?.persons ?? []);
      setSimilarPhotos(similarRes.data?.recommendations ?? []);
    } catch (err) {
      console.error('加载照片记忆失败', err);
    }
  };

  const closePhoto = () => {
    setActivePhotoId('');
    setInputText('');
  };

  const sendPhotoMessage = async () => {
    if (!inputText.trim() || !activePhotoId) return;
    const text = inputText.trim();
    setInputText('');
    setChatHistory((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);
    try {
      const res = await axios.post(
        `${API_BASE}/api/chat/send?photo_id=${activePhotoId}&query=${encodeURIComponent(text)}`,
      );
      setChatHistory((prev) => [...prev, { role: 'assistant', content: res.data.reply }]);
      const memRes = await axios.get(`${API_BASE}/api/memory/photo?photo_id=${activePhotoId}`);
      setMemoryFacts(memRes.data?.facts ?? []);
    } catch (err) {
      console.error('照片对话失败', err);
      setChatHistory((prev) => [...prev, { role: 'assistant', content: describeApiError(err) }]);
    } finally {
      setLoading(false);
    }
  };

  const renamePerson = async (personId: string) => {
    const newName = prompt('请输入新的人物名称');
    if (!newName?.trim()) return;
    try {
      await axios.put(
        `${API_BASE}/api/person/rename?person_id=${personId}&name=${encodeURIComponent(newName.trim())}`,
      );
      const res = await axios.get(`${API_BASE}/api/photo/persons?photo_id=${activePhotoId}`);
      setPersons(res.data?.persons ?? []);
    } catch (err) {
      console.error('重命名失败', err);
      alert('重命名失败');
    }
  };

  return (
    <div className="app">
      <div className="aurora" aria-hidden />
      <div className="stars" aria-hidden />

      <div className="shell">
        <header className="site-header">
          <div className="wrap site-header-inner">
            <div className="brand">
              <div className="brand-mark">✦</div>
              <div>
                <div className="brand-name">记忆相册</div>
                <div className="brand-tag">Personal Memory Agent</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <NotificationBell unread={unreadCount} onClick={openNotifications} />
              <button className="btn btn-glass btn-sm" onClick={openGlobalChat}>
                🧠 全局记忆问答
              </button>
            </div>
          </div>
        </header>

        <main style={{ flex: 1 }}>
          <IntroStage
            photoCount={photoList.length}
            onOpenAlbum={() => setAlbumOpen(true)}
            onOpenGlobalChat={openGlobalChat}
          />
        </main>
      </div>

      {/* 相册文件夹 */}
      <AnimatePresence>
        {albumOpen && (
          <AlbumFolder
            photos={photoList}
            loading={photoLoading}
            uploading={uploadLoading}
            onClose={() => setAlbumOpen(false)}
            onOpenPhoto={openPhoto}
            onUpload={handleUpload}
          />
        )}
      </AnimatePresence>

      {/* 全局记忆问答（独立弹层） */}
      <AnimatePresence>
        {globalChatOpen && (
          <GlobalChatOverlay
            history={globalHistory}
            relatedPhotos={globalRelatedPhotos}
            loading={globalLoading}
            inputText={globalInput}
            onInputChange={setGlobalInput}
            onSend={sendGlobalMessage}
            onClear={clearGlobalHistory}
            onOpenPhoto={openPhoto}
            onClose={() => setGlobalChatOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* 主动提醒（后端触发，前端只读展示） */}
      <AnimatePresence>
        {notifyOpen && (
          <NotificationPanel
            notifications={notifications}
            onMarkAllRead={markAllNotificationsRead}
            onOpenPhoto={openPhoto}
            onClose={() => setNotifyOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* 单照片记忆详情 */}
      <AnimatePresence>
        {activePhotoId && (
          <PhotoMemory
            photoId={activePhotoId}
            photo={currentPhoto}
            chatHistory={chatHistory}
            memoryFacts={memoryFacts}
            persons={persons}
            similarPhotos={similarPhotos}
            loading={loading}
            inputText={inputText}
            onInputChange={setInputText}
            onSend={sendPhotoMessage}
            onRenamePerson={renamePerson}
            onOpenPhoto={openPhoto}
            onClose={closePhoto}
          />
        )}
      </AnimatePresence>

      <FolderFab count={photoList.length} onClick={() => setAlbumOpen(true)} />
    </div>
  );
}
