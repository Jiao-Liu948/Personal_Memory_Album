# 前端 · 影像知识管理控制台

多模态影像知识管理 Agent 的 Web 界面。技术栈：**Next.js 16（App Router）+ React 19 + TypeScript + framer-motion + axios**。

完整项目说明见仓库根目录的 [README.md](../README.md)。

---

## 快速开始

```bash
npm install

# 开发模式（热更新）
npm run dev

# 生产构建与启动
npm run build
npm run start

# 代码检查
npm run lint
```

访问 http://localhost:3000 。**需要后端已在 8000 端口运行**（启动方式见根 README）。

---

## 与后端的关系

后端地址在 `app/api.ts` 中动态推导：

```ts
// 通过局域网 IP 访问前端时，自动请求同一主机名的 8000 端口
export const API_BASE =
  typeof window !== 'undefined'
    ? `http://${window.location.hostname}:8000`
    : 'http://localhost:8000';
```

因此**无需为局域网访问单独配置** —— 同一 WiFi 下的其他人用 `http://<你的IP>:3000` 打开时，请求会自动指向 `http://<你的IP>:8000`。

`app/api.ts` 另外统一处理了三件事：

- 请求超时（默认 90s；上传因需串行执行「视觉解析 + 人脸聚类 + 记忆抽取 + 开场白生成」而单独放宽到 5 分钟）
- 错误翻译（`describeApiError` 把后端 500 的 `detail` 原样带到界面上，便于定位模型配置问题）
- 展示名回退（`photoName` = `display_name || file_name`）

---

## 目录结构

```
app/
├── page.tsx          视图编排：控制台 / 资产库 / 影像问答 / 跨影像问答 / 主动提醒
├── types.ts          与后端返回值对齐的类型定义
├── api.ts            后端地址推导、超时、错误翻译、展示名工具
├── layout.tsx        根布局与站点元信息
└── globals.css       设计系统（深空极光主题、玻璃卡片、文件夹动画、控制台样式）

components/
├── SystemOverview.tsx      运行控制台首页（指标 / 处理管线 / 知识分布 / 模型端点）
├── AlbumFolder.tsx         影像资产库（文件夹开合动画 + 空态导入引导）
├── PhotoTile.tsx           资产卡片（3D 跟随光标倾斜、命名入口）
├── PhotoMemory.tsx         单影像问答与记忆侧栏（内联命名、人物重命名、相似影像）
├── GlobalChatOverlay.tsx   跨影像知识问答弹层
├── NotificationBell.tsx    主动提醒铃铛（未读红点）
├── NotificationPanel.tsx   提醒面板（纪念日 / 年度回忆）
├── FolderFab.tsx           悬浮入口按钮
├── MessageBubble.tsx       对话气泡
└── Typing.tsx              思考中指示器
```

---

## 设计约定

**前端只做被动展示，不承载任何「生成 / 触发」类主动能力入口。**

纪念日提醒与年度回忆由后端调度器按事件驱动，前端只负责读取通知、显示红点、点击弹窗。原因有两点：

1. 该自动发生的事情不该变成用户的操作负担
2. 年度回忆生成涉及 LLM 调用，做成按钮意味着用户每点一次就消耗一次模型调用

同理，双引擎检索（`/api/search/hybrid`）与信息补全（`/api/proactive/missing-info`）属于会话内部的检索链路，不单独暴露为界面功能。

---

## 交互实现说明

**文件夹开合动画**：资产库弹层的「前盖」以底边为轴做 `rotateX` 翻转并淡出，照片以错峰的 spring 动画从文件夹内升起。

**卡片 3D 倾斜**：鼠标在卡片上的位置经归一化后映射为 `rotateX` / `rotateY`（`useMotionValue` + `useSpring`，不触发 React 重渲染）。为避免与入场动画争抢 transform 属性，卡片分成两层 —— 外层负责入场与悬停上浮，内层负责倾斜。仅响应鼠标指针（触屏拖动若跟随倾斜会与页面滚动冲突），并尊重 `prefers-reduced-motion`。

**命名编辑**：资产库卡片悬停时出现快捷入口，影像详情页标题处可内联编辑（回车保存 / Esc 取消）。
