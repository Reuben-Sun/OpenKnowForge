# API 教程

本文按“添加 -> 搜索 -> 修改 -> 删除”的顺序演示。  
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
    "status": "published",
    "related": [],
    "submitted_at": "2026-03-26T10:00:00+00:00"
  }'
```

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
    "status": "published",
    "submitted_at": "2026-03-26T12:30:00+00:00"
  }'
```

## 4) 删除笔记 `DELETE /note/{slug}`

删除笔记文件，并清理该笔记在正文中引用的本地图片资源（`/assets/images/...`）。  
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

## 补充：读取与列表

读取单条：

```bash
curl http://127.0.0.1:8000/note/openknowforge
```

按最后编辑时间倒序列出全部：

```bash
curl http://127.0.0.1:8000/notes
```
