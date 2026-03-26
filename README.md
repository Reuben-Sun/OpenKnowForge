# OpenKnowForge

OpenKnowForge 是一个可编程知识库框架：通过本地 API 写入知识内容（Markdown + 图片 + 元数据），自动保存到 Git，并通过 VitePress 构建成可部署到 GitHub Pages 的静态站点。

## 功能概览

- `POST /note` 写入知识笔记
- `GET /note/{slug}` 读取单条知识
- `PUT /note/{slug}` 编辑知识
- `GET /notes` 按最后编辑时间倒序列出知识
- 自动保存图片到 `docs/assets/images/`
- 自动生成 Markdown 笔记到 `docs/notes/`
- 自动更新笔记目录和静态搜索索引
- Notes 页面为圆角卡片布局
- Explore 页面为按最后编辑时间排序的标题列表
- 自动执行 Git add/commit（失败不会阻塞写入）

## 项目结构

```txt
OpenKnowForge/
├── api/
│   ├── main.py
│   └── ingestors/
├── docs/
│   ├── notes/
│   ├── assets/images/
│   └── .vitepress/
├── scripts/
├── .github/workflows/pages.yml
├── requirements.txt
└── package.json
```

## 1) 使用 micromamba 启动本地 API

```bash
micromamba create -y -n openknowforge python=3.11
micromamba run -n openknowforge pip install -r requirements.txt -r requirements-dev.txt
micromamba run -n openknowforge python -m uvicorn api.main:app --reload
```

服务地址：`http://127.0.0.1:8000`

如果你更习惯先激活环境：

```bash
eval "$(micromamba shell hook --shell zsh)"
micromamba activate openknowforge
python -m uvicorn api.main:app --reload
```

也可以直接（在已激活环境中）：

```bash
./scripts/run_api.sh
```

## 2) 写入一条笔记（带提交时间）

```bash
curl -X POST http://127.0.0.1:8000/note \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "OpenKnowForge Quick Start",
    "content": "Markdown content...",
    "tags": ["guide", "quickstart"],
    "images": [],
    "type": "guide",
    "status": "published",
    "related": [],
    "submitted_at": "2026-03-26T10:00:00+00:00"
  }'
```

响应会包含：

- `slug` 和笔记路径
- `created_at`、`updated_at`、`submitted_at`
- git 提交结果（`git.hash`、`git.committed_at`）

## 3) 读取与编辑知识

读取单条：

```bash
curl http://127.0.0.1:8000/note/openknowforge
```

按最后编辑时间列出：

```bash
curl http://127.0.0.1:8000/notes
```

编辑：

```bash
curl -X PUT http://127.0.0.1:8000/note/openknowforge \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "Updated content",
    "status": "published",
    "submitted_at": "2026-03-26T12:30:00+00:00"
  }'
```

说明：

- `created_at` 在首次创建时写入
- `updated_at` 每次编辑时刷新
- 排序统一按 `updated_at` 倒序

## 4) 启动文档站点

```bash
npm install
npm run docs:dev
```

说明：`docs:dev` 默认开启文件轮询（polling），用于保证 API 写入新笔记后 Web 预览可热更新，无需重启 Web 服务。

访问：

- `http://127.0.0.1:5173/notes/`
- `http://127.0.0.1:5173/notes/explorer`

构建：

```bash
npm run docs:build
```

## 5) 运行自动化测试

```bash
micromamba run -n openknowforge python -m pytest -q
```

## 6) GitHub Pages 自动部署

已提供 `.github/workflows/pages.yml`：

- 触发条件：push 到 `main`
- 流程：安装依赖 -> 构建 VitePress -> 发布到 Pages

首次启用时请在仓库设置中确认：

- `Settings -> Pages -> Source` 使用 `GitHub Actions`

## 可扩展点

- 在 `api/ingestors/` 添加新 ingestor，实现自定义来源/处理流程
- 增加图片压缩、OCR、AI 摘要、语义检索等能力
