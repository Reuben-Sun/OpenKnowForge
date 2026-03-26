# OpenKnowForge

OpenKnowForge 是一个可编程知识库框架：通过本地 API 写入知识内容（Markdown + 图片 + 元数据），自动保存到 Git，并通过 VitePress 构建成可部署到 GitHub Pages 的静态站点。

## 功能概览

- `POST /note` 接收结构化笔记输入
- 自动保存图片到 `docs/assets/images/`
- 自动生成 Markdown 笔记到 `docs/notes/`
- 自动更新笔记目录和静态搜索索引
- 提供标签筛选 + 即时搜索页面：`/notes/explorer`
- 自动执行 Git add/commit（失败不会阻塞写入）
- VitePress 静态站点 + GitHub Actions Pages 发布

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

## 2) 写入一条笔记

```bash
./scripts/post_note_example.sh
```

或手动调用：

```bash
curl -X POST http://127.0.0.1:8000/note \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Delaunay Triangulation",
    "content": "Markdown content...",
    "tags": ["geometry", "algorithm"],
    "images": [],
    "type": "concept",
    "status": "draft",
    "related": ["voronoi-diagram"]
  }'
```

## 3) 启动文档站点

```bash
npm install
npm run docs:dev
```

访问：

- `http://127.0.0.1:5173/notes/`
- `http://127.0.0.1:5173/notes/explorer`

构建：

```bash
npm run docs:build
```

## 4) 运行自动化测试

```bash
micromamba run -n openknowforge python -m pytest -q
```

## 5) GitHub Pages 自动部署

已提供 `.github/workflows/pages.yml`：

- 触发条件：push 到 `main`
- 流程：安装依赖 -> 构建 VitePress -> 发布到 Pages

首次启用时请在仓库设置中确认：

- `Settings -> Pages -> Source` 使用 `GitHub Actions`

## API 说明

`POST /note` 示例请求：

```json
{
  "title": "Delaunay Triangulation",
  "content": "Markdown content here...",
  "tags": ["geometry", "algorithm"],
  "images": ["<base64 or url>"],
  "type": "concept",
  "status": "draft",
  "related": ["voronoi-diagram"]
}
```

响应会包含：

- 生成的 `slug` 和笔记路径
- 保存的图片路径
- git 提交结果

## 可扩展点

- 在 `api/ingestors/` 添加新 ingestor，实现自定义来源/处理流程
- 增加图片压缩、OCR、AI 摘要、语义检索等能力
