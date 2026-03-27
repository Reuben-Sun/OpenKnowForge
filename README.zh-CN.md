# OpenKnowForge

[English](README.md)

OpenKnowForge 是一个 API 原生、Git 驱动的知识库系统。
它把笔记生产、元数据治理、静态发布、版本追踪整合成一条可工程化的工作流。

## OpenClaw 全自动工作流（无需人工写笔记）

这个项目的设计前提是以 OpenClaw 作为主要内容生产引擎。
日常使用中不需要人类手动维护 markdown 笔记正文。

请优先在 OpenClaw 中安装这个 Skill：

- OpenKnowForge-Skill：`https://github.com/Reuben-Sun/OpenKnowForge-Skill.git`

推荐使用方式：

1. 在 OpenClaw 中从上述仓库安装 `OpenKnowForge-Skill`。
2. 由 OpenClaw 通过 OpenKnowForge API 完成笔记创建、编辑、分类和维护。
3. 人类主要负责复核与知识治理，而不是手工撰写原始笔记。

![Home](assets/Home.png)

## 项目含金量

OpenKnowForge 不是普通的 Markdown 笔记集合，它的价值在于把“记笔记”变成“可编排的知识工程”：

- OpenClaw 原生工作流：通过 `OpenKnowForge-Skill` 可将笔记创作全程交给 OpenClaw。
- 可编程知识管理：通过 HTTP API 管理笔记，便于脚本与 Agent 自动化接入。
- Git 级别治理：每次变更可追踪、可审计、可回滚，天然适配协作场景。
- 生产可发布架构：写入是动态 API，输出是静态站点，兼顾开发效率与线上稳定性。
- 结构化知识模型：每条笔记具备状态、时间戳、标签、统计信息，支持稳定检索与排序。
- 团队可落地：本地启动轻量，部署通过 CI 自动化，最终站点可直接托管在 GitHub Pages。

## 核心能力（已实现）

### 1) 完整笔记生命周期 API

- 新建笔记：`POST /note`
- 读取笔记：`GET /note/{slug}`
- 编辑笔记：`PUT /note/{slug}`
- 仅改状态：`PATCH /note/{slug}/status`
- 删除笔记：`DELETE /note/{slug}`
- 全量列表：`GET /notes`
- 草稿列表：`GET /notes/drafts`
- 笔记搜索：`GET /notes/search`
- 推送远端：`POST /git/push`

### 2) 强约束元数据模型

每条笔记都维护：

- `status`：`mature`（成熟知识）或 `draft`（草稿）
- `created_at`、`updated_at`、`submitted_at`
- `tags`、`related`、`type`
- `word_count`、`image_count`

这些字段让排序、筛选、展示逻辑更稳定。

### 3) 自动统计机制

在创建和编辑笔记时会自动统计字数与图片数量。
对历史笔记也会在需要时自动补齐统计，保证数据一致性。

### 4) 图片写入能力

API 支持以下图片输入格式：

- Data URL
- HTTP(S) 链接
- Base64 字符串

图片落地到 `docs/project/images/`，并自动写入笔记内容。

### 5) 索引与站点自动同步

每次笔记变更后会自动重建：

- Notes 索引页
- 英文笔记别名文件
- `docs/public/search-index.json`

保证本地预览与静态构建结果始终和内容同步。

### 6) 内建 Git 追踪

新增/编辑/删除笔记会自动执行暂存和提交。
接口返回中会带上 commit hash 与提交时间（当实际产生提交时）。

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
- 文档站点：VitePress
- 搜索索引：`docs/public/search-index.json`
- 持续部署：GitHub Actions + GitHub Pages

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

仓库已包含工作流配置：

- `.github/workflows/pages.yml`

部署步骤：

1. 在 GitHub 仓库设置中启用 Pages，Source 选择 `GitHub Actions`。
2. 推送提交到 `main` 分支。
3. 工作流会自动构建并发布文档站点。

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
