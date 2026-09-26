import axios from 'axios';

// 动态推导后端地址：朋友通过局域网 IP 访问前端时，自动请求同一主机名的 8000 端口
export const API_BASE =
  typeof window !== 'undefined'
    ? `http://${window.location.hostname}:8000`
    : 'http://localhost:8000';

// 统一超时：后端模型接口异常时（如 base_url 配错导致长时间挂起），
// 让前端在可控时间内失败并给出提示，而不是无限转圈。
axios.defaults.timeout = 90000;

// 把后端返回的相对图片路径转成可直接加载的完整 URL
export const imgUrl = (url: string) => `${API_BASE}${url}`;

// 照片展示名：优先用户自定义名称，没有则回退到原始文件名
export const photoName = (p: { display_name?: string; file_name?: string }) =>
  (p.display_name || '').trim() || p.file_name || '照片';

// 把请求异常翻译成可读提示（把后端的 500 detail 原样带出来，便于定位模型配置问题）
export function describeApiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    if (err.code === 'ECONNABORTED') {
      return '请求超时：后端长时间没有响应。请检查 backend/.env 中的模型地址/密钥，以及后端窗口日志。';
    }
    if (!err.response) {
      return '无法连接后端服务，请确认后端已在 8000 端口启动。';
    }
    const detail = (err.response.data as { detail?: unknown } | undefined)?.detail;
    return `后端返回 ${err.response.status}${typeof detail === 'string' ? `：${detail}` : '，请查看后端日志'}`;
  }
  return '请求失败，请稍后重试。';
}


// 格式化上传时间，显示为简洁的日期
export function formatDate(iso: string): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}.${m}.${day}`;
  } catch {
    return iso;
  }
}

// 根据字符串取一个稳定的颜色 class（用于记忆标签着色）
const TAG_PALETTE = ['tag--0', 'tag--1', 'tag--2', 'tag--3', 'tag--4'];
export function tagClass(str: string): string {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return TAG_PALETTE[h % TAG_PALETTE.length];
}
