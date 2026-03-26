# API

## `GET /health`

Returns service health.

```bash
curl http://127.0.0.1:8000/health
```

## `POST /note`

Create a note and trigger markdown/index rebuild.

### Request JSON

```json
{
  "title": "Delaunay Triangulation",
  "content": "Markdown content here...",
  "tags": ["geometry", "algorithm"],
  "images": ["https://example.com/image.png"],
  "type": "concept",
  "status": "draft",
  "related": ["voronoi-diagram"],
  "submitted_at": "2026-03-26T10:00:00+00:00"
}
```

### Response highlights

- `slug`
- `created_at`
- `updated_at`
- `submitted_at`
- `git.hash`
- `git.committed_at`

## `GET /notes`

List notes sorted by `updated_at` (desc).

```bash
curl http://127.0.0.1:8000/notes
```

## `GET /note/{slug}`

Read one note by slug.

```bash
curl http://127.0.0.1:8000/note/openknowforge
```

## `PUT /note/{slug}`

Edit an existing note. `updated_at` is refreshed from this request's `submitted_at` (or current server time if omitted).

```bash
curl -X PUT http://127.0.0.1:8000/note/openknowforge \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "Updated markdown content",
    "status": "published",
    "submitted_at": "2026-03-26T12:30:00+00:00"
  }'
```
