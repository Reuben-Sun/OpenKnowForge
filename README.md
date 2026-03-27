# OpenKnowForge

[中文](README.zh-CN.md)

OpenKnowForge is an API-native, Git-backed knowledge base system.
It connects note authoring, metadata governance, static publishing, and version traceability into one workflow.

## OpenClaw-First Workflow (No Manual Note Writing)

This project is designed to run with OpenClaw as the primary authoring engine.
Human users do not need to manually write notes in markdown files.

Install this skill in OpenClaw first:

- OpenKnowForge Skill: `https://github.com/Reuben-Sun/OpenKnowForge-Skill.git`

Recommended operating model:

1. Install `OpenKnowForge-Skill` in OpenClaw from the repository above.
2. Let OpenClaw create, edit, classify, and maintain notes through OpenKnowForge APIs.
3. Keep human input focused on review and curation instead of raw note drafting.

![Home](assets/Home.png)

## Why This Project Matters

OpenKnowForge is not just another markdown notebook.
Its core value is turning knowledge management into an engineering system:

- OpenClaw-native workflow: note creation can be fully delegated to OpenClaw with `OpenKnowForge-Skill`.
- Programmable knowledge operations: notes are managed via HTTP APIs, so scripts/agents can create and maintain content reliably.
- Git-level governance: every note change is committed, auditable, and easy to roll back.
- Publish-ready architecture: data is edited dynamically but published as static pages for speed and low ops cost.
- Structured knowledge schema: each note carries metadata (status, timestamps, tags, stats), enabling deterministic indexing and filtering.
- Team-friendly delivery: local development is lightweight, deployment is CI-driven, and output is accessible through GitHub Pages.

## Core Capabilities (Implemented)

### 1) Full note lifecycle APIs

- Create note: `POST /note`
- Read note: `GET /note/{slug}`
- Update note: `PUT /note/{slug}`
- Update status only: `PATCH /note/{slug}/status`
- Delete note: `DELETE /note/{slug}`
- List all notes: `GET /notes`
- List drafts: `GET /notes/drafts`
- Search notes: `GET /notes/search`
- Push repository: `POST /git/push`

### 2) Strong metadata model

Each note maintains:

- `status`: `mature` or `draft`
- `created_at`, `updated_at`, `submitted_at`
- `tags`, `related`, `type`
- `word_count`, `image_count`

This supports reliable sorting, filtering, and UI rendering.

### 3) Reliable content stats

Word/image statistics are calculated when creating and editing notes.
Existing notes are also backfilled automatically on startup when needed.

### 4) Image ingestion and normalization

The API accepts image inputs as:

- Data URL
- HTTP(S) URL
- Base64 string

Images are stored under `docs/project/images/` and linked into the note body.

### 5) Auto index and site sync

After note changes, the system automatically rebuilds:

- Notes index pages
- English note alias files
- `docs/public/search-index.json`

So local docs preview and static site outputs stay in sync with the latest content.

### 6) Built-in Git traceability

Note create/update/delete operations auto-stage and auto-commit content updates.
The API response includes commit hash/time when a commit is generated.

## Architecture

```text
Author / Script / Agent
          |
          v
  FastAPI (note APIs)
          |
          v
Markdown + Frontmatter + Assets (Git)
          |
          v
VitePress static build
          |
          v
GitHub Pages
```

## Tech Stack

- Backend API: FastAPI
- Content format: Markdown + YAML frontmatter
- Site generator: VitePress
- Index/search source: `docs/public/search-index.json`
- CI/CD: GitHub Actions + GitHub Pages

## Quick Start

### 1) Install dependencies

```bash
pip install -r requirements.txt
npm install
```

### 2) Start API service

```bash
python -m uvicorn api.main:app --reload
```

- API base URL: `http://127.0.0.1:8000`
- Health check: `GET /health`

### 3) Start local docs preview

```bash
npm run docs:dev
```

- Docs preview: `http://127.0.0.1:5173`
- Notes (zh): `http://127.0.0.1:5173/notes/`
- Notes (en): `http://127.0.0.1:5173/en/notes/`

## GitHub Pages Deployment

This repository already contains workflow config at:

- `.github/workflows/pages.yml`

Deploy steps:

1. In GitHub repo settings, enable Pages and choose `GitHub Actions` as source.
2. Push commits to `main`.
3. The Pages workflow builds and publishes docs automatically.

## Project Layout (High-level)

- API code: `api/`
- UI/guide docs: `docs/ui/`
- User notes: `docs/project/entries/`
- User images: `docs/project/images/`
- Search index: `docs/public/search-index.json`

## Documentation

- Chinese guide: `docs/ui/zh/guide/`
- English guide: `docs/ui/en/guide/`

## License

Apache License 2.0. See `LICENSE`.
