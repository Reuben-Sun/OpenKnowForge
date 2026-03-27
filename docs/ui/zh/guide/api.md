# API 教程

本文按“添加 -> 搜索 -> 修改 -> 删除 -> 推送”的顺序演示。  
服务地址默认是 `http://127.0.0.1:8000`。

## `GET /health`

检查服务是否可用。

```bash
curl http://127.0.0.1:8000/health
```

## 1) 添加笔记 `POST /note`

```bash
curl -X POST http://127.0.0.1:8000/note \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "KL散度",
    "content": "KL 散度用于衡量两个概率分布之间的差异。",
    "tags": ["math", "information-theory"],
    "images": [],
    "type": "concept",
    "status": "mature",
    "is_draft": false,
    "related": [],
    "submitted_at": "2026-03-26T10:00:00+00:00"
  }'
```

`status` 可选值：`mature`（默认，成熟知识）或 `draft`（草稿）。  
也可以直接使用 `is_draft`（`true/false`）设置是否为草稿。

约束：

- `status` 与 `is_draft` 可以二选一。
- 两者同时传时必须语义一致，否则返回 `400`（`status conflicts with is_draft`）。

返回重点字段：

- `slug`: 笔记唯一标识，用于后续读取/修改/删除
- `created_at`: 创建时间
- `updated_at`: 最后编辑时间
- `submitted_at`: 本次提交时间
- `git.hash`: 自动提交哈希
- `git.committed_at`: git 提交时间

## 2) 搜索笔记 `GET /notes/search`

### 按关键字搜索

会在标题、内容摘要、标签中匹配关键字，按 `updated_at` 倒序返回。

```bash
curl "http://127.0.0.1:8000/notes/search?q=KL&limit=20"
```

### 按标签过滤

```bash
curl "http://127.0.0.1:8000/notes/search?tag=math&limit=20"
```

### 关键字 + 标签组合

```bash
curl "http://127.0.0.1:8000/notes/search?q=divergence&tag=information-theory&limit=20"
```

## 3) 修改笔记 `PUT /note/{slug}`

将 `slug` 对应的笔记更新为新内容。  
`updated_at` 会刷新为本次 `submitted_at`（若不传则使用服务端当前时间）。

```bash
curl -X PUT http://127.0.0.1:8000/note/<slug> \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "数学公式示例",
    "content": "这里是更新后的内容",
    "tags": ["math", "formula"],
    "status": "mature",
    "submitted_at": "2026-03-26T12:30:00+00:00"
  }'
```

`PUT /note/{slug}` 同样支持 `is_draft`，用于在编辑正文时顺便切换状态。

## 4) 仅修改状态 `PATCH /note/{slug}/status`

只切换草稿/成熟状态，不改正文内容。

```bash
curl -X PATCH http://127.0.0.1:8000/note/<slug>/status \
  -H 'Content-Type: application/json' \
  -d '{
    "is_draft": true,
    "submitted_at": "2026-03-26T13:10:00+00:00"
  }'
```

也可写成：

```bash
curl -X PATCH http://127.0.0.1:8000/note/<slug>/status \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "mature",
    "submitted_at": "2026-03-26T13:20:00+00:00"
  }'
```

## 5) 删除笔记 `DELETE /note/{slug}`

删除笔记文件，并清理该笔记在正文中引用的本地图片资源（`/project/images/...`）。  
删除后会自动重建索引并提交 git 记录。

```bash
curl -X DELETE http://127.0.0.1:8000/note/<slug>
```

返回重点字段：

- `slug`
- `title`
- `deleted_at`
- `note_path`
- `deleted_images`
- `git.hash`

## 6) 推送到远端 `POST /git/push`

将当前分支推送到远端仓库，默认等价于：

```bash
git push origin <当前分支>
```

示例（最常用）：

```bash
curl -X POST http://127.0.0.1:8000/git/push \
  -H 'Content-Type: application/json' \
  -d '{}'
```

指定远端与分支：

```bash
curl -X POST http://127.0.0.1:8000/git/push \
  -H 'Content-Type: application/json' \
  -d '{
    "remote": "origin",
    "branch": "main",
    "set_upstream": false,
    "force_with_lease": false
  }'
```

返回重点字段：

- `remote`
- `branch`
- `hash`
- `committed_at`

## 补充：读取与列表

读取单条：

```bash
curl http://127.0.0.1:8000/note/<slug>
```

按最后编辑时间倒序列出全部：

```bash
curl http://127.0.0.1:8000/notes
```

只列出草稿：

```bash
curl http://127.0.0.1:8000/notes/drafts
```
