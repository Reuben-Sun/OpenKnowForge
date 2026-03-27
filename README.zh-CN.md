# OpenKnowForge

[English](README.md)

OpenKnowForge 是一套以 API 为核心、以 Git 为底座的知识工程系统。
它将内容生成、结构化治理、静态发布与版本审计整合为统一流程，用于构建可持续演进的知识库。

## OpenClaw First：无需人工撰写笔记

本项目默认采用 OpenClaw 作为内容生产引擎。
在常规工作流中，笔记创建与维护并不依赖人工逐篇撰写，而是由 OpenClaw 通过 API 自动完成。

请先在 OpenClaw 中安装以下 Skill：

- OpenKnowForge-Skill：`https://github.com/Reuben-Sun/OpenKnowForge-Skill.git`

推荐流程如下：

1. 在 OpenClaw 中安装 `OpenKnowForge-Skill`。
2. 由 OpenClaw 调用 OpenKnowForge API 完成新建、编辑、分类与维护。
3. 人类仅承担复核、校正与知识治理工作。

![Home](assets/Home.png)

## 设计哲学

- 自动化优先：将“写笔记”升级为“知识工程流水线”，核心操作通过 API 可编排执行。
- 可追溯优先：所有内容修改均进入 Git 历史，便于审计、对比与回滚。
- 发布优先：动态写入、静态发布，兼顾内容更新效率与线上稳定性。
- 结构化优先：以统一元数据驱动索引、检索、排序与展示。
- 协作优先：本地环境轻量、CI 自动部署，适配个人与团队共建。

## 核心能力（已实现）

### 1) 完整笔记生命周期 API

- 新建笔记：`POST /note`
- 读取笔记：`GET /note/{slug}`
- 编辑笔记：`PUT /note/{slug}`
- 仅改状态：`PATCH /note/{slug}/status`
- 删除笔记：`DELETE /note/{slug}`
- 全量列表：`GET /notes`
- 草稿列表：`GET /notes/drafts`
- 条件搜索：`GET /notes/search`
- 推送远端：`POST /git/push`

### 2) 结构化元数据模型

每条笔记维护以下关键字段：

- 状态：`status`（`mature` / `draft`）
- 时间：`created_at`、`updated_at`、`submitted_at`
- 语义：`tags`、`related`、`type`
- 统计：`word_count`、`image_count`

该模型保证排序、筛选、渲染与接口返回的一致性。

### 3) 统计自动计算与回填

系统在创建和编辑笔记时自动计算字数与图片数。
对于历史笔记，启动阶段会在需要时自动补齐统计字段，以维持数据一致。

### 4) 图片接入与规范化存储

API 支持以下图片输入形式：

- Data URL
- HTTP(S) URL
- Base64 字符串

图片统一保存至 `docs/project/images/`，并自动写入笔记正文。

### 5) 索引自动重建与站点同步

每次笔记变更后，系统会自动重建：

- Notes 索引页
- 英文笔记别名文件
- `docs/public/search-index.json`

因此，本地预览与静态构建结果可与最新内容保持同步。

### 6) 内建 Git 追踪

新增、编辑、删除操作会自动执行暂存与提交。
当实际产生提交时，API 返回中包含 commit hash 与提交时间。

## 架构链路

```text
作者 / 脚本 / Agent
        |
        v
 FastAPI（笔记 API）
        |
        v
Markdown + Frontmatter + 图片资产（Git）
        |
        v
VitePress 静态构建
        |
        v
GitHub Pages
```

## 技术栈

- 后端 API：FastAPI
- 内容格式：Markdown + YAML frontmatter
- 文档引擎：VitePress
- 检索索引：`docs/public/search-index.json`
- 发布链路：GitHub Actions + GitHub Pages

## 快速开始

### 1) 安装依赖

```bash
pip install -r requirements.txt
npm install
```

### 2) 启动 API 服务

```bash
python -m uvicorn api.main:app --reload
```

- API 地址：`http://127.0.0.1:8000`
- 健康检查：`GET /health`

### 3) 本地预览文档

```bash
npm run docs:dev
```

- 预览地址：`http://127.0.0.1:5173`
- 中文 Notes：`http://127.0.0.1:5173/notes/`
- 英文 Notes：`http://127.0.0.1:5173/en/notes/`

## GitHub Pages 部署

仓库已包含工作流配置：`.github/workflows/pages.yml`。

部署步骤：

1. 在 GitHub 仓库设置中启用 Pages，Source 选择 `GitHub Actions`。
2. 推送提交到 `main` 分支。
3. 工作流自动构建并发布文档站点。

## 项目结构（高层）

- API 代码：`api/`
- UI 与指南：`docs/ui/`
- 用户笔记：`docs/project/entries/`
- 用户图片：`docs/project/images/`
- 搜索索引：`docs/public/search-index.json`

## 文档入口

- 中文指南：`docs/ui/zh/guide/`
- 英文指南：`docs/ui/en/guide/`

## 开源协议

Apache License 2.0，见 `LICENSE`。
