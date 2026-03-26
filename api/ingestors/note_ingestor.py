from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

from api.ingestors.base import BaseIngestor

ROOT_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT_DIR / "docs"
NOTES_DIR = DOCS_DIR / "notes"
IMAGES_DIR = DOCS_DIR / "assets" / "images"
PUBLIC_DIR = DOCS_DIR / "public"
NOTES_INDEX_PATH = NOTES_DIR / "index.md"
SEARCH_INDEX_PATH = PUBLIC_DIR / "search-index.json"

DATA_URL_PATTERN = re.compile(r"^data:(?P<mime>[-\w.]+/[-\w.+]+);base64,(?P<data>.+)$")
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")
IMG_SRC_PATTERN = re.compile(r'<img\s+[^>]*src="([^"]+)"', re.IGNORECASE)
RESERVED_NOTE_FILES = {"index.md", "explorer.md"}


@dataclass
class SavedImage:
    markdown_path: str
    filesystem_path: Path


class NoteIngestor(BaseIngestor):
    async def ingest(self, data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_dirs()

        title = str(data.get("title", "")).strip()
        if not title:
            raise ValueError("title is required")

        content = str(data.get("content", "")).strip()
        tags = self._normalize_list(data.get("tags"))
        related = self._normalize_list(data.get("related"))
        note_type = str(data.get("note_type", "note")).strip() or "note"
        status = str(data.get("status", "draft")).strip() or "draft"

        submitted_at = self._normalize_timestamp(data.get("submitted_at"), default_now=True)
        created_at = submitted_at
        updated_at = submitted_at

        slug = self._build_note_slug(title)
        saved_images = await self._save_images(data.get("images") or [], slug)
        note_path = self._write_note(
            slug=slug,
            title=title,
            content=content,
            tags=tags,
            related=related,
            note_type=note_type,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            submitted_at=submitted_at,
            images=saved_images,
        )

        self._rebuild_notes_index()
        self._rebuild_search_index()

        commit = self._git_commit(slug, action="add")

        return {
            "slug": slug,
            "note_path": str(note_path.relative_to(ROOT_DIR)),
            "image_count": len(saved_images),
            "image_paths": [img.markdown_path for img in saved_images],
            "created_at": created_at,
            "updated_at": updated_at,
            "submitted_at": submitted_at,
            "git": commit,
        }

    async def update(self, slug: str, data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_dirs()
        current = self.read(slug)

        title = str(data.get("title", current["title"]))
        title = title.strip()
        if not title:
            raise ValueError("title is required")

        content = str(data.get("content", current["content"]))
        content = content.strip()

        tags = (
            self._normalize_list(data.get("tags"))
            if "tags" in data
            else self._normalize_list(current.get("tags"))
        )
        related = (
            self._normalize_list(data.get("related"))
            if "related" in data
            else self._normalize_list(current.get("related"))
        )

        note_type = str(data.get("note_type", current["type"])).strip() or "note"
        status = str(data.get("status", current["status"])).strip() or "draft"

        submitted_at = self._normalize_timestamp(data.get("submitted_at"), default_now=True)
        created_at = self._normalize_timestamp(current.get("created_at"), default_now=False) or submitted_at
        updated_at = submitted_at

        saved_images = await self._save_images(data.get("images") or [], slug)
        if saved_images:
            image_lines = [f'<img src="{img.markdown_path}" alt="{title}" loading="lazy" />' for img in saved_images]
            if content:
                content = content.rstrip() + "\n\n## Images\n\n" + "\n".join(image_lines)
            else:
                content = "## Images\n\n" + "\n".join(image_lines)

        note_path = self._write_note(
            slug=slug,
            title=title,
            content=content,
            tags=tags,
            related=related,
            note_type=note_type,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            submitted_at=submitted_at,
            images=[],
        )

        self._rebuild_notes_index()
        self._rebuild_search_index()

        commit = self._git_commit(slug, action="update")

        return {
            "slug": slug,
            "note_path": str(note_path.relative_to(ROOT_DIR)),
            "image_count": len(saved_images),
            "image_paths": [img.markdown_path for img in saved_images],
            "created_at": created_at,
            "updated_at": updated_at,
            "submitted_at": submitted_at,
            "git": commit,
        }

    def read(self, slug: str) -> dict[str, Any]:
        self._ensure_dirs()
        path = self._resolve_note_path(slug)
        text = path.read_text(encoding="utf-8")

        frontmatter = self._extract_frontmatter(text)
        markdown_body = FRONTMATTER_PATTERN.sub("", text).strip()

        title = str(frontmatter.get("title") or path.stem)
        tags = self._normalize_list(frontmatter.get("tags"))
        related = self._normalize_list(frontmatter.get("related"))
        note_type = str(frontmatter.get("type") or "note")
        status = str(frontmatter.get("status") or "draft")

        created_at = self._normalize_timestamp(
            frontmatter.get("created_at") or frontmatter.get("date"),
            default_now=False,
        )
        updated_at = self._normalize_timestamp(
            frontmatter.get("updated_at") or created_at or frontmatter.get("date"),
            default_now=False,
        )
        submitted_at = self._normalize_timestamp(
            frontmatter.get("submitted_at") or updated_at or created_at,
            default_now=False,
        )

        content = self._extract_content_from_markdown(markdown_body)
        image_paths = IMG_SRC_PATTERN.findall(markdown_body)

        return {
            "slug": path.stem,
            "path": str(path.relative_to(ROOT_DIR)),
            "title": title,
            "content": content,
            "tags": tags,
            "type": note_type,
            "status": status,
            "related": related,
            "created_at": created_at,
            "updated_at": updated_at,
            "submitted_at": submitted_at,
            "image_paths": image_paths,
        }

    def list_notes(self) -> list[dict[str, Any]]:
        self._ensure_dirs()
        return self._collect_notes(include_excerpt=False)

    def search(self, query: str = "", tag: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        self._ensure_dirs()
        query_text = str(query).strip().lower()
        tag_text = str(tag).strip().lower() if tag else ""
        bounded_limit = max(1, min(int(limit), 200))

        all_notes = self._collect_notes(include_excerpt=True)
        matches: list[dict[str, Any]] = []
        for item in all_notes:
            tags = [str(entry).strip() for entry in item.get("tags") or []]
            if tag_text and not any(tag_text == entry.lower() for entry in tags):
                continue

            if query_text:
                haystack_parts = [
                    str(item.get("title", "")),
                    str(item.get("excerpt", "")),
                    " ".join(tags),
                ]
                haystack = " ".join(haystack_parts).lower()
                if query_text not in haystack:
                    continue

            matches.append(item)
            if len(matches) >= bounded_limit:
                break

        return matches

    def delete(self, slug: str) -> dict[str, Any]:
        self._ensure_dirs()
        current = self.read(slug)
        note_path = self._resolve_note_path(slug)

        deleted_images: list[str] = []
        for src in current.get("image_paths") or []:
            image_src = str(src).strip()
            if not image_src.startswith("/assets/images/"):
                continue

            image_path = IMAGES_DIR / Path(image_src).name
            if image_path.exists():
                image_path.unlink()
                deleted_images.append(str(image_path.relative_to(ROOT_DIR)))

        note_path.unlink()
        deleted_at = self._normalize_timestamp(None, default_now=True)

        self._rebuild_notes_index()
        self._rebuild_search_index()

        commit = self._git_commit(slug, action="delete")

        return {
            "slug": slug,
            "title": current.get("title", ""),
            "deleted_at": deleted_at,
            "note_path": str(note_path.relative_to(ROOT_DIR)),
            "deleted_images": deleted_images,
            "git": commit,
        }

    def _ensure_dirs(self) -> None:
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    def _normalize_list(self, value: Any) -> list[str]:
        if not value:
            return []
        if not isinstance(value, list):
            return [str(value).strip()] if str(value).strip() else []
        normalized: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized

    def _build_note_slug(self, title: str) -> str:
        # Keep file naming deterministic and URL-friendly.
        slug = title.lower().strip()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        if not slug:
            slug = "note"

        candidate = slug
        counter = 2
        while (NOTES_DIR / f"{candidate}.md").exists():
            candidate = f"{slug}-{counter}"
            counter += 1
        return candidate

    def _resolve_note_path(self, slug: str) -> Path:
        normalized = slug.strip().lower()
        if not normalized or not SLUG_PATTERN.match(normalized):
            raise ValueError("invalid slug")

        target = NOTES_DIR / f"{normalized}.md"
        if not target.exists() or target.name in RESERVED_NOTE_FILES:
            raise FileNotFoundError(f"note '{normalized}' not found")
        return target

    async def _save_images(self, images: list[str], slug: str) -> list[SavedImage]:
        saved: list[SavedImage] = []
        for index, image_ref in enumerate(images, start=1):
            image_ref = str(image_ref).strip()
            if not image_ref:
                continue

            raw_bytes, suffix = await self._resolve_image_bytes(image_ref)
            digest = hashlib.sha256(raw_bytes).hexdigest()[:12]
            filename = f"{slug}-{index}-{digest}{suffix}"
            target = IMAGES_DIR / filename
            target.write_bytes(raw_bytes)
            saved.append(
                SavedImage(
                    markdown_path=f"/assets/images/{filename}",
                    filesystem_path=target,
                )
            )
        return saved

    async def _resolve_image_bytes(self, image_ref: str) -> tuple[bytes, str]:
        data_url_match = DATA_URL_PATTERN.match(image_ref)
        if data_url_match:
            mime = data_url_match.group("mime")
            raw = base64.b64decode(data_url_match.group("data"))
            return raw, self._suffix_from_mime(mime)

        if image_ref.startswith("http://") or image_ref.startswith("https://"):
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(image_ref)
                response.raise_for_status()
                mime = response.headers.get("content-type", "").split(";")[0].strip()
                suffix = self._suffix_from_mime(mime)
                if suffix == ".bin":
                    parsed = urlparse(image_ref)
                    url_suffix = Path(parsed.path).suffix
                    if url_suffix:
                        suffix = url_suffix
                return response.content, suffix

        try:
            raw = base64.b64decode(image_ref, validate=True)
            return raw, ".png"
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                "images entries must be data URLs, HTTP(S) URLs, or base64 strings"
            ) from exc

    def _suffix_from_mime(self, mime: str) -> str:
        mime_to_suffix = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/svg+xml": ".svg",
            "image/avif": ".avif",
        }
        return mime_to_suffix.get(mime, ".bin")

    def _write_note(
        self,
        slug: str,
        title: str,
        content: str,
        tags: list[str],
        related: list[str],
        note_type: str,
        status: str,
        created_at: str,
        updated_at: str,
        submitted_at: str,
        images: list[SavedImage],
    ) -> Path:
        frontmatter = {
            "title": title,
            "tags": tags,
            "created_at": created_at,
            "updated_at": updated_at,
            "submitted_at": submitted_at,
            "date": (updated_at or created_at)[:10],
            "type": note_type,
            "status": status,
            "related": related,
        }

        image_lines: list[str] = []
        for img in images:
            image_lines.append(f'<img src="{img.markdown_path}" alt="{title}" loading="lazy" />')

        body_lines: list[str] = ["# " + title, ""]
        if content:
            body_lines.append(content.rstrip())
        if image_lines:
            if content:
                body_lines.append("")
            body_lines.extend(["## Images", "", *image_lines])

        frontmatter_block = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False).strip() + "\n---"
        markdown = frontmatter_block + "\n\n" + "\n".join(body_lines).rstrip() + "\n"

        note_path = NOTES_DIR / f"{slug}.md"
        note_path.write_text(markdown, encoding="utf-8")
        return note_path

    def _extract_content_from_markdown(self, markdown_body: str) -> str:
        lines = markdown_body.splitlines()
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
            if lines and not lines[0].strip():
                lines = lines[1:]
        return "\n".join(lines).strip()

    def _rebuild_notes_index(self) -> None:
        lines: list[str] = [
            "---",
            "title: Notes",
            "---",
            "",
            "# Notes",
            "",
            "Live note catalog as rounded cards.",
            "",
            "Use [Explore Notes](/notes/explorer) for a time-sorted title list.",
            "",
            "<NotesCards />",
        ]

        NOTES_INDEX_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def _rebuild_search_index(self) -> None:
        notes = self._collect_notes(include_excerpt=True)
        payload = {
            "generatedAt": self._normalize_timestamp(None, default_now=True),
            "notes": notes,
        }
        SEARCH_INDEX_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _collect_notes(self, include_excerpt: bool = False) -> list[dict[str, Any]]:
        notes: list[dict[str, Any]] = []
        for path in sorted(NOTES_DIR.glob("*.md")):
            if path.name in RESERVED_NOTE_FILES:
                continue

            text = path.read_text(encoding="utf-8")
            frontmatter = self._extract_frontmatter(text)
            title = str(frontmatter.get("title") or path.stem)

            created_at = self._normalize_timestamp(
                frontmatter.get("created_at") or frontmatter.get("date"),
                default_now=False,
            )
            updated_at = self._normalize_timestamp(
                frontmatter.get("updated_at") or created_at or frontmatter.get("date"),
                default_now=False,
            )
            submitted_at = self._normalize_timestamp(
                frontmatter.get("submitted_at") or updated_at or created_at,
                default_now=False,
            )

            tags = frontmatter.get("tags") or []
            if not isinstance(tags, list):
                tags = [str(tags)]

            entry: dict[str, Any] = {
                "slug": path.stem,
                "title": title,
                "created_at": created_at,
                "updated_at": updated_at,
                "submitted_at": submitted_at,
                "date": (updated_at or created_at)[:10],
                "tags": [str(tag) for tag in tags],
                "link": f"/notes/{path.stem}",
            }

            if include_excerpt:
                body = FRONTMATTER_PATTERN.sub("", text).strip()
                excerpt_base = self._extract_content_from_markdown(body)
                excerpt = re.sub(r"\s+", " ", excerpt_base)
                entry["excerpt"] = excerpt[:200]

            notes.append(entry)

        notes.sort(
            key=lambda item: self._timestamp_sort_value(item.get("updated_at") or item.get("date")),
            reverse=True,
        )
        return notes

    def _extract_frontmatter(self, text: str) -> dict[str, Any]:
        match = FRONTMATTER_PATTERN.match(text)
        if not match:
            return {}
        try:
            parsed = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _parse_timestamp(self, value: Any) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None

        normalized = raw
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            normalized = f"{normalized}T00:00:00+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _normalize_timestamp(self, value: Any, *, default_now: bool) -> str:
        parsed = self._parse_timestamp(value)
        if parsed:
            return parsed.replace(microsecond=0).isoformat()

        if default_now:
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return ""

    def _timestamp_sort_value(self, value: Any) -> float:
        parsed = self._parse_timestamp(value)
        if not parsed:
            return 0.0
        return parsed.timestamp()

    def _git_commit(self, slug: str, action: str) -> dict[str, Any]:
        add = subprocess.run(
            ["git", "add", "docs/notes", "docs/assets/images", "docs/public/search-index.json"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if add.returncode != 0:
            return {
                "committed": False,
                "error": add.stderr.strip() or "git add failed",
            }

        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=ROOT_DIR,
            check=False,
        )
        if diff.returncode == 0:
            return {"committed": False, "message": "No staged changes"}

        if action == "update":
            verb = "update"
        elif action == "delete":
            verb = "delete"
        else:
            verb = "add"
        commit = subprocess.run(
            ["git", "commit", "-m", f"docs(kb): {verb} note {slug}"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if commit.returncode != 0:
            return {
                "committed": False,
                "error": commit.stderr.strip() or "git commit failed",
            }

        commit_hash = ""
        commit_hash_cmd = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if commit_hash_cmd.returncode == 0:
            commit_hash = commit_hash_cmd.stdout.strip()

        committed_at = ""
        commit_time_cmd = subprocess.run(
            ["git", "log", "-1", "--format=%cI"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if commit_time_cmd.returncode == 0:
            committed_at = commit_time_cmd.stdout.strip()

        return {
            "committed": True,
            "message": commit.stdout.strip().splitlines()[-1] if commit.stdout.strip() else "ok",
            "hash": commit_hash,
            "committed_at": committed_at,
        }
