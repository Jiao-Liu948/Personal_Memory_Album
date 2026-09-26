// 与后端 API 返回值对齐的共享类型定义

export interface PhotoItem {
  photo_id: string;
  file_name: string;
  /** 用户自定义名称；为空时展示 file_name */
  display_name?: string;
  upload_time: string;
  parse_status: string;
  image_url: string;
  vision?: Record<string, unknown>;
}

export interface MemoryFact {
  fact_id: string;
  event: string;
  time_info: string;
  location: string;
  emotion: string;
  tags: string[];
  source: string;
  person_relation: string;
}

export interface Person {
  person_id: string;
  name: string;
  photo_count?: number;
}

export interface ChatMessage {
  role: string;
  content: string;
}

export interface Anniversary {
  fact_id: string;
  event: string;
  original_date: string;
  anniversary_date: string;
  years_passed: number;
  status: 'upcoming' | 'today' | 'just_passed';
  days_text: string;
  related_photo_ids: string[];
}

export interface YearlyRecap {
  year: number;
  total_memories: number;
  total_photos: number;
  top_tags: { tag: string; count: number }[];
  monthly_timeline: Record<string, YearlyTimelineItem[]>;
  photos: PhotoItem[];
  yearly_story: string;
}

export interface YearlyTimelineItem {
  fact_id: string;
  event: string;
  date: string;
  location: string;
  tags: string[];
  related_photo_ids: string[];
}

// 主动提醒通知：由后端调度器触发写入，前端只读展示（红点 + 弹窗）
export interface AppNotification {
  id: string;
  type: 'anniversary' | 'yearly_recap' | string;
  title: string;
  body: string;
  payload: Record<string, unknown>;
  dedup_key?: string;
  created_at: string;
  read: boolean;
}

export interface NotificationFeed {
  notifications: AppNotification[];
  unread_count: number;
  total: number;
}

// ============ 系统概览（控制台指标，后端实时计算） ============
export interface ModelBinding {
  name: string;
  base_url: string;
  configured: boolean;
}

export interface PipelineStage {
  stage: string;
  value: number;
  unit: string;
}

export interface SystemOverview {
  assets: {
    total: number;
    parsed: number;
    pending: number;
    failed: number;
    parse_rate: number;
  };
  knowledge: {
    persons: number;
    facts: number;
    tags: number;
    locations: number;
    linked_photos: number;
  };
  sources: { source: string; count: number }[];
  top_tags: { tag: string; count: number }[];
  top_locations: { location: string; count: number }[];
  timeline: { date: string; count: number }[];
  pipeline: PipelineStage[];
  models: Record<'chat' | 'vision' | 'embedding', ModelBinding>;
  capabilities: {
    vector_search: boolean;
    face_cluster: boolean;
    proactive: boolean;
  };
  generated_at: string;
}
