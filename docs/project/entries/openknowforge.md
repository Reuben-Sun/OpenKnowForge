---
title: "OpenKnowForge\u5FEB\u901F\u5F00\u59CB"
tags:
- guide
- how-to
- openknowforge
- local-dev
- github-pages
- deploy
- vitepress
- ci
created_at: '2026-03-26T00:00:00+00:00'
updated_at: '2026-03-26T17:02:20+00:00'
submitted_at: '2026-03-26T17:02:20+00:00'
date: '2026-03-26'
word_count: 511
image_count: 0
type: guide
status: published
related:
- notes-explorer
- search-index
---

# OpenKnowForge快速开始

## 本地开发与预览

### 启动 API

```bash
python -m uvicorn api.main:app --reload
```

### 本地预览

```bash
npm run docs:dev
```

访问：
- `http://127.0.0.1:5173/notes/`
- `http://127.0.0.1:5173/notes/explorer`

## GitHub Pages 部署配置

目标：将本项目的 VitePress Web 站点自动部署到 GitHub Pages。

### 1. 配置 VitePress base（关键）

本项目默认已自动处理 `base`，fork 后一般不需要改代码：

```ts
const repoName = process.env.GITHUB_REPOSITORY?.split('/')[1]?.trim()
const explicitBase = process.env.VITEPRESS_BASE?.trim()
const isGitHubActions = process.env.GITHUB_ACTIONS === 'true'
const isUserOrOrgSiteRepo = Boolean(repoName && repoName.toLowerCase().endsWith('.github.io'))
const base = explicitBase
  ? normalizeBasePath(explicitBase)
  : isGitHubActions && repoName && !isUserOrOrgSiteRepo
    ? normalizeBasePath(repoName)
    : '/'
```

含义：
1. 本地开发时使用 `base: '/'`。
2. 在 GitHub Actions 构建项目页时，自动使用 `/<repo>/`（例如 `/OpenKnowForge/`）。
3. 如果仓库名是 `xxx.github.io`（用户/组织主页），自动使用 `base: '/'`。
4. 需要手动覆盖时，设置环境变量 `VITEPRESS_BASE`（例如 `/docs/` 或 `/`）。
5. GitHub 社交链接默认会自动使用当前仓库；需要覆盖时设置 `VITEPRESS_GITHUB_REPO`（如 `owner/repo` 或完整 GitHub URL）。

### 2. 启用 GitHub Pages

进入仓库：`Settings -> Pages`

- Build and deployment -> Source 选择 `GitHub Actions`

这是必须步骤，否则工作流不会真正发布到 Pages。

### 3. 触发部署

每次 `commit` 并推送到 `main` 后，GitHub Actions 会自动触发 Pages 部署。

## 常见问题

### fork 后需要改什么？

1. 必做：在 `Settings -> Pages` 把 Source 设为 `GitHub Actions`。
2. 必做：将代码推送到 `main`，触发自动部署。
3. 可选：设置 `VITEPRESS_GITHUB_REPO` 指向你自己的仓库（如 `your-name/your-repo`）。
4. 通常不需要手改 `base`；仅在特殊路径部署时才通过 `VITEPRESS_BASE` 覆盖。

### Failed to load search index. Create notes via POST /note first.

含义：前端没有拿到 `search-index.json`。

排查顺序：
1. 先确认至少写入过一条笔记（调用一次 `POST /note`）。
2. 确认文件存在：`docs/public/search-index.json`。
3. 用 `npm run docs:dev` 方式启动预览，不要直接 `file://` 打开静态文件。
4. 打开浏览器网络面板，确认 `search-index.json` 返回 200 且内容是 JSON。

### GitHub Pages 页面样式异常或资源 404

1. 优先检查 `docs/.vitepress/config.ts` 的 `base` 是否与仓库路径一致。
2. 检查 `Settings -> Pages -> Source` 是否是 `GitHub Actions`。
3. 等待 1~3 分钟后强制刷新页面，排除 CDN 缓存影响。
