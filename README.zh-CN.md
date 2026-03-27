# OpenKnowForge

[English](README.md)

OpenKnowForge 是一个 API 优先的知识库项目，技术栈为 FastAPI + Markdown + VitePress + GitHub Pages。

## 设计理念

- 笔记始终保存为纯 Markdown，内容可迁移、可长期维护。
- 通过 HTTP API 实现可编程的笔记新增、修改、检索与发布流程。
- 前端采用静态站点，部署保持简单，直接接入 GitHub Pages。
- 所有内容变更都可通过 Git 历史追踪。

## 快速开始

### 1) 安装依赖

```bash
pip install -r requirements.txt
npm install
```

### 2) 启动 API

```bash
python -m uvicorn api.main:app --reload
```

API 地址：`http://127.0.0.1:8000`

### 3) 本地预览文档

```bash
npm run docs:dev
```

预览地址：`http://127.0.0.1:5173`

## GitHub Pages

仓库已包含工作流：`.github/workflows/pages.yml`。

部署方式：

1. 在仓库设置中启用 GitHub Pages（Build and deployment -> Source 选择 GitHub Actions）。
2. 将提交推送到 `main` 分支。
3. GitHub Actions 会自动构建并发布文档站点。

## 文档位置

- 中文指南：`docs/ui/zh/guide/`
- 英文指南：`docs/ui/en/guide/`

## 开源协议

Apache License 2.0，见 `LICENSE`。
