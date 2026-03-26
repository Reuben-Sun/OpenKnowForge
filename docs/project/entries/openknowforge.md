---
title: "OpenKnowForge \u9879\u76EE\u4F7F\u7528\u65B9\u6CD5\uFF08\u672C\u5730\u5F00\
  \u53D1\u4E0E\u9884\u89C8\uFF09"
tags:
- guide
- how-to
- openknowforge
- local-dev
created_at: '2026-03-26T00:00:00+00:00'
updated_at: '2026-03-26T00:00:00+00:00'
submitted_at: '2026-03-26T00:00:00+00:00'
date: '2026-03-26'
type: guide
status: published
related:
- notes-explorer
- search-index
word_count: 153
image_count: 0
---

# OpenKnowForge 项目使用方法（本地开发与预览）

## 1. 准备环境（micromamba）

```bash
micromamba create -y -n openknowforge python=3.11
micromamba run -n openknowforge pip install -r requirements.txt -r requirements-dev.txt
```

## 2. 启动 API

```bash
micromamba run -n openknowforge python -m uvicorn api.main:app --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 3. 通过 POST /note 写入知识

```bash
curl -X POST http://127.0.0.1:8000/note \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "示例标题",
    "content": "Markdown 内容",
    "tags": ["how-to", "openknowforge"],
    "images": [],
    "type": "guide",
    "status": "published",
    "related": []
  }'
```

写入后会自动生成：
- `docs/project/entries/<slug>.md`
- `docs/public/search-index.json`
- 可能的 git 自动提交（失败不阻塞写入）

## 4. 本地预览笔记站点

```bash
npm install
npm run docs:dev
```

访问：
- `http://127.0.0.1:5173/notes/`
- `http://127.0.0.1:5173/notes/explorer`

## 5. 常见问题

### Failed to load search index. Create notes via POST /note first.
含义：前端没有拿到 `search-index.json`。
排查顺序：
1. 先确认至少写入过一条笔记（调用一次 `POST /note`）。
2. 确认文件存在：`docs/public/search-index.json`。
3. 用 `npm run docs:dev` 方式启动预览，不要直接 `file://` 打开静态文件。
4. 打开浏览器网络面板，确认 `search-index.json` 返回 200 且内容是 JSON。

## 6. 测试与构建

```bash
micromamba run -n openknowforge python -m pytest -q
npm run docs:build
```
