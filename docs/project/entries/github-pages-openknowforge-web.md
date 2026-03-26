---
title: "GitHub Pages \u90E8\u7F72\u914D\u7F6E\u6B65\u9AA4 OpenKnowForge Web"
tags:
- github-pages
- deploy
- vitepress
- ci
- how-to
created_at: '2026-03-26T12:29:03+00:00'
updated_at: '2026-03-26T12:29:03+00:00'
submitted_at: '2026-03-26T12:29:03+00:00'
date: '2026-03-26'
type: guide
status: published
related:
- openknowforge
word_count: 355
image_count: 0
---

# GitHub Pages 部署配置步骤 OpenKnowForge Web

目标：将本项目的 VitePress Web 站点自动部署到 GitHub Pages。

## 1. 准备仓库

1. 确保代码已推送到 `main` 分支。
2. 仓库根目录需要有 `package.json`，且可执行 `npm run docs:build`。
3. 本项目已内置工作流文件：`.github/workflows/pages.yml`。

## 2. 配置 VitePress base（关键）

如果你使用的是 **项目页**（地址形如 `https://<user>.github.io/<repo>/`），需要在 `docs/.vitepress/config.ts` 中设置：

```ts
export default defineConfig({
  base: '/OpenKnowForge/',
  // ...
})
```

说明：`/OpenKnowForge/` 需替换为你的仓库名。

如果你使用 **用户主页**（`https://<user>.github.io/`）或绑定了自定义域名根路径，可保持默认 `base: '/'`。

## 3. 启用 GitHub Pages

进入仓库：`Settings -> Pages`

- Build and deployment -> Source 选择 `GitHub Actions`

这是必须步骤，否则工作流不会真正发布到 Pages。

## 4. 核对 CI 工作流

本项目默认工作流要点如下（`.github/workflows/pages.yml`）：

- 触发：`push` 到 `main`（也支持手动 `workflow_dispatch`）
- Node：20
- 构建命令：`npm ci` + `npm run docs:build`
- 上传产物目录：`docs/.vitepress/dist`
- 发布动作：`actions/deploy-pages@v4`

可直接复用现有文件，无需另写脚本。

## 5. 触发部署

```bash
git add .
git commit -m "chore: configure github pages deploy"
git push origin main
```

推送后到 `Actions` 页面查看 `Deploy VitePress to GitHub Pages` 是否成功。

## 6. 验证访问

部署成功后访问：

- 项目页：`https://<user>.github.io/<repo>/`
- 本项目示例：`https://reuben-sun.github.io/OpenKnowForge/`

若出现样式或资源 404，优先检查 `base` 配置是否与仓库名一致。

## 7. 常见问题

### 7.1 页面是空白或资源 404

- 大概率是 `base` 配错
- 确认 `docs/.vitepress/config.ts` 与实际 Pages 路径一致

### 7.2 Actions 成功但 Pages 没更新

- 检查 `Settings -> Pages -> Source` 是否是 `GitHub Actions`
- 等待 1~3 分钟 CDN 缓存刷新

### 7.3 推送后没触发流程

- 确认提交分支是 `main`
- 确认 `.github/workflows/pages.yml` 在默认分支中
