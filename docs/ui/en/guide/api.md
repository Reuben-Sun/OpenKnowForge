# API Guide

This guide follows: create -> search -> update -> delete -> push.
Default service endpoint: `http://127.0.0.1:8000`.

## `GET /health`

Check whether the API is reachable.

```bash
curl http://127.0.0.1:8000/health
```

## 1) Create note `POST /note`

```bash
curl -X POST http://127.0.0.1:8000/note \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "KL Divergence",
    "content": "KL divergence measures the difference between distributions.",
    "tags": ["math", "information-theory"],
    "images": [],
    "type": "concept",
    "status": "mature",
    "is_draft": false,
    "related": [],
    "submitted_at": "2026-03-26T10:00:00+00:00"
  }'
```

`status` supports: `mature` (default) and `draft`.  
You can also use `is_draft` (`true/false`) directly.

Constraints:

- Use either `status` or `is_draft`.
- If both are provided, they must be consistent, otherwise API returns `400` (`status conflicts with is_draft`).

Key fields in response:

- `slug`: unique note id used for read/update/delete
- `created_at`: creation time
- `updated_at`: last edited time
- `submitted_at`: submission time for this request
- `git.hash`: auto-commit hash
- `git.committed_at`: git commit time

## 2) Search notes `GET /notes/search`

### Search by keyword

Matches title, excerpt, and tags. Results are sorted by `updated_at` (descending).

```bash
curl "http://127.0.0.1:8000/notes/search?q=KL&limit=20"
```

### Filter by tag

```bash
curl "http://127.0.0.1:8000/notes/search?tag=math&limit=20"
```

### Keyword + tag

```bash
curl "http://127.0.0.1:8000/notes/search?q=divergence&tag=information-theory&limit=20"
```

## 3) Update note `PUT /note/{slug}`

Updates the note referenced by `slug`.
`updated_at` is refreshed from `submitted_at` (or server current time when omitted).

```bash
curl -X PUT http://127.0.0.1:8000/note/<slug> \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Formula Example",
    "content": "Updated content",
    "tags": ["math", "formula"],
    "status": "mature",
    "submitted_at": "2026-03-26T12:30:00+00:00"
  }'
```

`PUT /note/{slug}` also supports `is_draft` if you want to switch status while editing content.

## 4) Update status only `PATCH /note/{slug}/status`

Switches draft/mature status without changing note content.

```bash
curl -X PATCH http://127.0.0.1:8000/note/<slug>/status \
  -H 'Content-Type: application/json' \
  -d '{
    "is_draft": true,
    "submitted_at": "2026-03-26T13:10:00+00:00"
  }'
```

Or:

```bash
curl -X PATCH http://127.0.0.1:8000/note/<slug>/status \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "mature",
    "submitted_at": "2026-03-26T13:20:00+00:00"
  }'
```

## 5) Delete note `DELETE /note/{slug}`

Deletes the note file and removes local image assets referenced in its body (`/project/images/...`).
The system then rebuilds indexes and writes a git commit record.

```bash
curl -X DELETE http://127.0.0.1:8000/note/<slug>
```

Key fields in response:

- `slug`
- `title`
- `deleted_at`
- `note_path`
- `deleted_images`
- `git.hash`

## 6) Push to remote `POST /git/push`

Pushes the current branch to remote repository. By default it behaves like:

```bash
git push origin <current-branch>
```

Most common usage:

```bash
curl -X POST http://127.0.0.1:8000/git/push \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Specify remote and branch:

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

Key fields in response:

- `remote`
- `branch`
- `hash`
- `committed_at`

## Extra: read and list

Read one note:

```bash
curl http://127.0.0.1:8000/note/<slug>
```

List all notes ordered by last edited time:

```bash
curl http://127.0.0.1:8000/notes
```

List drafts only:

```bash
curl http://127.0.0.1:8000/notes/drafts
```
