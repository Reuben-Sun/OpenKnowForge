# OpenKnowForge

[中文](README.zh-CN.md)

OpenKnowForge is an API-first knowledge base project built with FastAPI + Markdown + VitePress + GitHub Pages.

## Design Philosophy

- Keep knowledge as plain Markdown files so content stays portable.
- Use HTTP APIs for programmable note creation, update, search, and publishing workflows.
- Keep UI static and deployment simple via GitHub Pages.
- Make every content change traceable through Git history.

## Quick Start

### 1) Install dependencies

```bash
pip install -r requirements.txt
npm install
```

### 2) Start API

```bash
python -m uvicorn api.main:app --reload
```

API base URL: `http://127.0.0.1:8000`

### 3) Start local docs preview

```bash
npm run docs:dev
```

Preview URL: `http://127.0.0.1:5173`

## GitHub Pages

This repo already includes a Pages workflow at `.github/workflows/pages.yml`.

To deploy:

1. Enable GitHub Pages in repository settings (Build and deployment -> Source: GitHub Actions).
2. Push commits to `main`.
3. GitHub Actions will build and publish docs automatically.

## Documentation

- Guide (CN): `docs/ui/zh/guide/`
- Guide (EN): `docs/ui/en/guide/`

## License

Apache License 2.0. See `LICENSE`.
