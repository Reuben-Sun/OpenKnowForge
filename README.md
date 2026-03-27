# OpenKnowForge

[中文](README.zh-CN.md)

OpenKnowForge is an API-native, Git-backed knowledge engineering system.
It unifies content generation, metadata governance, static publishing, and version traceability into a single workflow.

## OpenClaw-First Workflow (No Manual Note Writing)

The project is designed around OpenClaw as the primary authoring engine.
In normal operation, notes are not manually drafted one by one; OpenClaw handles creation and maintenance through APIs.

Install this skill in OpenClaw first:

- OpenKnowForge-Skill: `https://github.com/Reuben-Sun/OpenKnowForge-Skill.git`

Recommended workflow:

1. Install `OpenKnowForge-Skill` in OpenClaw.
2. Let OpenClaw call OpenKnowForge APIs for note creation, editing, classification, and maintenance.
3. Keep human effort focused on review, correction, and knowledge governance.

![Home](assets/Home.png)

## Design Philosophy

- Automation first: treat note-taking as an orchestrated knowledge pipeline driven by APIs.
- Traceability first: keep every content change in Git history for auditability and rollback.
- Publishing first: combine dynamic ingestion with static delivery for both velocity and reliability.
- Structure first: use a consistent metadata model to support indexing, search, sorting, and rendering.
- Collaboration first: keep local setup lightweight and deployment CI-driven for team adoption.

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

### 2) Structured metadata model

Each note maintains:

- Status: `status` (`mature` / `draft`)
- Time fields: `created_at`, `updated_at`, `submitted_at`
- Semantic fields: `tags`, `related`, `type`
- Statistics: `word_count`, `image_count`

This model keeps sorting, filtering, rendering, and API responses consistent.

### 3) Automatic statistics and backfill

Word and image counts are computed on create and update.
Legacy notes are backfilled when needed during startup to keep metadata consistent.

### 4) Image ingestion and normalized storage

The API accepts image input as:

- Data URL
- HTTP(S) URL
- Base64 string

Images are stored under `docs/project/images/` and injected into note content automatically.

### 5) Auto index rebuild and site sync

After note mutations, the system rebuilds:

- Notes index pages
- English note alias files
- `docs/public/search-index.json`

This keeps local preview and static output aligned with current content.

### 6) Built-in Git traceability

Create, update, and delete operations perform automatic staging and committing.
When a commit is created, the API response includes the commit hash and timestamp.

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
- Docs engine: VitePress
- Search index source: `docs/public/search-index.json`
- Delivery pipeline: GitHub Actions + GitHub Pages

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

The repository already includes workflow configuration at `.github/workflows/pages.yml`.

Deployment steps:

1. Enable GitHub Pages in repository settings and select `GitHub Actions` as the source.
2. Push commits to `main`.
3. The workflow builds and publishes the site automatically.

## Project Layout (High-level)

- API code: `api/`
- UI and guides: `docs/ui/`
- User notes: `docs/project/entries/`
- User images: `docs/project/images/`
- Search index: `docs/public/search-index.json`

## Documentation

- Chinese guide: `docs/ui/zh/guide/`
- English guide: `docs/ui/en/guide/`

## License

Apache License 2.0. See `LICENSE`.
