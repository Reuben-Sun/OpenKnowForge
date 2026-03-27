from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
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
UI_DIR = DOCS_DIR / "ui"
UI_ZH_DIR = UI_DIR / "zh"
UI_EN_DIR = UI_DIR / "en"
UI_NOTES_ZH_DIR = UI_ZH_DIR / "notes"
UI_NOTES_EN_DIR = UI_EN_DIR / "notes"
EN_NOTE_ENTRIES_DIR = UI_NOTES_EN_DIR / "entries"
PROJECT_DIR = DOCS_DIR / "project"
USER_NOTES_DIR = PROJECT_DIR / "entries"
IMAGES_DIR = PROJECT_DIR / "images"
LEGACY_NOTES_DIR = DOCS_DIR / "notes"
LEGACY_USER_NOTES_DIR = LEGACY_NOTES_DIR / "entries"
LEGACY_IMAGES_DIR = DOCS_DIR / "assets" / "images"
PUBLIC_DIR = DOCS_DIR / "public"
ZH_NOTES_INDEX_PATH = UI_NOTES_ZH_DIR / "index.md"
EN_NOTES_INDEX_PATH = UI_NOTES_EN_DIR / "index.md"
SEARCH_INDEX_PATH = PUBLIC_DIR / "search-index.json"

DATA_URL_PATTERN = re.compile(r"^data:(?P<mime>[-\w.]+/[-\w.+]+);base64,(?P<data>.+)$")
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")
IMG_SRC_PATTERN = re.compile(r'<img\s+[^>]*src="([^"]+)"', re.IGNORECASE)
HTML_IMG_TAG_PATTERN = re.compile(r"<img\s+[^>]*>", re.IGNORECASE)
MARKDOWN_IMG_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
CODE_BLOCK_PATTERN = re.compile(r"```[^\n]*\n([\s\S]*?)```")
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]*)`")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
MATH_BLOCK_PATTERN = re.compile(r"\$\$[\s\S]*?\$\$")
INLINE_MATH_PATTERN = re.compile(r"\$(?!\s)([^$\n]+?)\$")
CJK_CHAR_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
LATIN_WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[._'/-][A-Za-z0-9]+)*")
RESERVED_NOTE_FILES = {"index.md", "explorer.md"}
STATS_BACKFILLED_ROOTS: set[str] = set()
VALID_NOTE_STATUS = {"mature", "draft"}
NOTE_STATUS_ALIASES = {"published": "mature"}


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
        status = self._normalize_status(data.get("status"), default="mature")

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
        word_count, image_count, image_paths = self._read_note_stats(note_path)

        self._rebuild_notes_index()
        self._rebuild_en_note_aliases()
        self._rebuild_search_index()

        commit = self._git_commit(slug, action="add")

        return {
            "slug": slug,
            "note_path": str(note_path.relative_to(ROOT_DIR)),
            "status": status,
            "uploaded_image_count": len(saved_images),
            "image_count": image_count,
            "image_paths": image_paths,
            "word_count": word_count,
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
        status = self._normalize_status(data.get("status", current["status"]), default="mature")

        submitted_at = self._normalize_timestamp(data.get("submitted_at"), default_now=True)
        created_at = self._normalize_timestamp(current.get("created_at"), default_now=False) or submitted_at
        updated_at = submitted_at
        previous_image_paths = [str(item).strip() for item in current.get("image_paths") or []]

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
        latest_markdown = note_path.read_text(encoding="utf-8")
        latest_image_paths = set(self._extract_image_paths_from_markdown(latest_markdown))
        removed_images = self._cleanup_images(previous_image_paths, keep_paths=latest_image_paths)
        word_count, image_count, image_paths = self._read_note_stats(note_path)

        self._rebuild_notes_index()
        self._rebuild_en_note_aliases()
        self._rebuild_search_index()

        commit = self._git_commit(slug, action="update")

        return {
            "slug": slug,
            "note_path": str(note_path.relative_to(ROOT_DIR)),
            "status": status,
            "uploaded_image_count": len(saved_images),
            "image_count": image_count,
            "image_paths": image_paths,
            "word_count": word_count,
            "removed_images": removed_images,
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
        status = self._normalize_status(frontmatter.get("status"), default="mature", strict=False)

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
        image_paths = self._extract_image_paths_from_markdown(markdown_body)
        computed_word_count, computed_image_count = self._compute_note_stats(markdown_body)
        word_count = self._normalize_count(frontmatter.get("word_count"), fallback=computed_word_count)
        image_count = self._normalize_count(frontmatter.get("image_count"), fallback=computed_image_count)

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
            "word_count": word_count,
            "image_count": image_count,
            "image_paths": image_paths,
        }

    def list_notes(self) -> list[dict[str, Any]]:
        self._ensure_dirs()
        return self._collect_notes(include_excerpt=False)

    def list_drafts(self) -> list[dict[str, Any]]:
        self._ensure_dirs()
        notes = self._collect_notes(include_excerpt=False)
        return [item for item in notes if str(item.get("status", "")).strip().lower() == "draft"]

    async def update_status(self, slug: str, status: str, submitted_at: Any = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"status": status}
        if submitted_at is not None:
            payload["submitted_at"] = submitted_at
        return await self.update(slug, payload)

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
        deleted_images = self._cleanup_images(current.get("image_paths") or [], keep_paths=None)

        note_path.unlink()
        deleted_at = self._normalize_timestamp(None, default_now=True)

        self._rebuild_notes_index()
        self._rebuild_en_note_aliases()
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

    def _cleanup_images(self, image_paths: list[Any], keep_paths: set[str] | None) -> list[str]:
        deleted: list[str] = []
        keep = keep_paths or set()
        for src in image_paths:
            image_src = str(src).strip()
            if not image_src or image_src in keep:
                continue

            if image_src.startswith("/project/images/"):
                image_path = IMAGES_DIR / Path(image_src).name
            elif image_src.startswith("/assets/images/"):
                image_path = LEGACY_IMAGES_DIR / Path(image_src).name
            else:
                continue

            if image_path.exists():
                image_path.unlink()
                deleted.append(str(image_path.relative_to(ROOT_DIR)))
        return deleted

    def _ensure_dirs(self) -> None:
        UI_NOTES_ZH_DIR.mkdir(parents=True, exist_ok=True)
        UI_NOTES_EN_DIR.mkdir(parents=True, exist_ok=True)
        EN_NOTE_ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
        USER_NOTES_DIR.mkdir(parents=True, exist_ok=True)
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        self._backfill_note_stats_once()

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

    def _normalize_status(self, value: Any, *, default: str, strict: bool = True) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            raw = default
        raw = NOTE_STATUS_ALIASES.get(raw, raw)
        if raw not in VALID_NOTE_STATUS:
            if not strict:
                return default
            valid = ", ".join(sorted(VALID_NOTE_STATUS))
            raise ValueError(f"status must be one of: {valid}")
        return raw

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
        while self._slug_exists(candidate):
            candidate = f"{slug}-{counter}"
            counter += 1
        return candidate

    def _slug_exists(self, slug: str) -> bool:
        entries_targets = [
            USER_NOTES_DIR / f"{slug}.md",
            LEGACY_USER_NOTES_DIR / f"{slug}.md",
        ]
        if any(path.exists() for path in entries_targets):
            return True

        legacy_target = LEGACY_NOTES_DIR / f"{slug}.md"
        return legacy_target.exists() and legacy_target.name not in RESERVED_NOTE_FILES

    def _resolve_note_path(self, slug: str) -> Path:
        normalized = slug.strip().lower()
        if not normalized or not SLUG_PATTERN.match(normalized):
            raise ValueError("invalid slug")

        target = USER_NOTES_DIR / f"{normalized}.md"
        if target.exists():
            return target

        legacy_entries_target = LEGACY_USER_NOTES_DIR / f"{normalized}.md"
        if legacy_entries_target.exists():
            return legacy_entries_target

        legacy_target = LEGACY_NOTES_DIR / f"{normalized}.md"
        if legacy_target.exists() and legacy_target.name not in RESERVED_NOTE_FILES:
            return legacy_target

        raise FileNotFoundError(f"note '{normalized}' not found")

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
                    markdown_path=f"/project/images/{filename}",
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
        normalized_status = self._normalize_status(status, default="mature")

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

        body_markdown = "\n".join(body_lines).rstrip()
        word_count, image_count = self._compute_note_stats(body_markdown)

        frontmatter = {
            "title": title,
            "tags": tags,
            "created_at": created_at,
            "updated_at": updated_at,
            "submitted_at": submitted_at,
            "date": (updated_at or created_at)[:10],
            "word_count": word_count,
            "image_count": image_count,
            "type": note_type,
            "status": normalized_status,
            "related": related,
        }

        frontmatter_block = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False).strip() + "\n---"
        markdown = frontmatter_block + "\n\n" + body_markdown + "\n"

        note_path = USER_NOTES_DIR / f"{slug}.md"
        note_path.write_text(markdown, encoding="utf-8")
        return note_path

    def _extract_content_from_markdown(self, markdown_body: str) -> str:
        lines = markdown_body.splitlines()
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
            if lines and not lines[0].strip():
                lines = lines[1:]
        return "\n".join(lines).strip()

    def _extract_image_paths_from_markdown(self, markdown: str) -> list[str]:
        html_paths = IMG_SRC_PATTERN.findall(markdown)
        markdown_paths = MARKDOWN_IMG_PATTERN.findall(markdown)

        paths: list[str] = []
        for path in [*html_paths, *markdown_paths]:
            item = str(path).strip()
            if item:
                paths.append(item)
        return paths

    def _to_plain_text(self, markdown_body: str) -> str:
        base = self._extract_content_from_markdown(markdown_body)
        if not base:
            return ""

        text = CODE_BLOCK_PATTERN.sub(lambda match: f" {match.group(1)} ", base)
        text = MATH_BLOCK_PATTERN.sub(" ", text)
        text = INLINE_MATH_PATTERN.sub(" ", text)
        text = INLINE_CODE_PATTERN.sub(lambda match: f" {match.group(1)} ", text)
        text = MARKDOWN_IMG_PATTERN.sub(" ", text)
        text = HTML_IMG_TAG_PATTERN.sub(" ", text)
        text = LINK_PATTERN.sub(lambda match: f" {match.group(1)} ", text)
        text = HTML_TAG_PATTERN.sub(" ", text)
        text = re.sub(r"(?mi)^\s*#{1,6}\s*images\s*$", " ", text)
        text = re.sub(r"[#>*~]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _count_words(self, markdown_body: str) -> int:
        text = self._to_plain_text(markdown_body)
        if not text:
            return 0

        cjk_count = len(CJK_CHAR_PATTERN.findall(text))
        latin_count = len(LATIN_WORD_PATTERN.findall(text))
        return cjk_count + latin_count

    def _compute_note_stats(self, markdown_body: str) -> tuple[int, int]:
        normalized = str(markdown_body or "").strip()
        if not normalized:
            return 0, 0
        word_count = self._count_words(normalized)
        image_count = len(self._extract_image_paths_from_markdown(normalized))
        return word_count, image_count

    def _normalize_count(self, value: Any, *, fallback: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback
        if parsed < 0:
            return fallback
        return parsed

    def _read_note_stats(self, note_path: Path) -> tuple[int, int, list[str]]:
        markdown = note_path.read_text(encoding="utf-8")
        body = FRONTMATTER_PATTERN.sub("", markdown).strip()
        word_count, image_count = self._compute_note_stats(body)
        image_paths = self._extract_image_paths_from_markdown(body)
        return word_count, image_count, image_paths

    def _backfill_note_stats_once(self) -> None:
        root_key = str(ROOT_DIR.resolve())
        if root_key in STATS_BACKFILLED_ROOTS:
            return
        self._rebuild_note_stats()
        STATS_BACKFILLED_ROOTS.add(root_key)

    def _rebuild_note_stats(self) -> None:
        paths_by_slug: dict[str, Path] = {}
        for path in sorted(USER_NOTES_DIR.glob("*.md")):
            paths_by_slug[path.stem] = path
        for path in sorted(LEGACY_USER_NOTES_DIR.glob("*.md")):
            paths_by_slug.setdefault(path.stem, path)
        for path in sorted(LEGACY_NOTES_DIR.glob("*.md")):
            if path.name in RESERVED_NOTE_FILES:
                continue
            paths_by_slug.setdefault(path.stem, path)

        for path in paths_by_slug.values():
            text = path.read_text(encoding="utf-8")
            match = FRONTMATTER_PATTERN.match(text)
            if not match:
                continue

            frontmatter = self._extract_frontmatter(text)
            if not frontmatter:
                continue

            body = FRONTMATTER_PATTERN.sub("", text).strip()
            word_count, image_count = self._compute_note_stats(body)

            current_word_count = self._normalize_count(frontmatter.get("word_count"), fallback=-1)
            current_image_count = self._normalize_count(frontmatter.get("image_count"), fallback=-1)
            if current_word_count == word_count and current_image_count == image_count:
                continue

            frontmatter["word_count"] = word_count
            frontmatter["image_count"] = image_count
            frontmatter_block = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False).strip() + "\n---"
            body_with_spacing = text[match.end() :].lstrip("\n")
            rewritten = f"{frontmatter_block}\n\n{body_with_spacing}"
            if not rewritten.endswith("\n"):
                rewritten += "\n"
            path.write_text(rewritten, encoding="utf-8")

    def _rebuild_notes_index(self) -> None:
        zh_lines: list[str] = [
            "---",
            "title: Notes",
            "sidebar: false",
            "aside: false",
            "prev: false",
            "next: false",
            "---",
            "",
            "# Notes",
            "",
            "<NotesCards />",
        ]
        en_lines: list[str] = [
            "---",
            "title: Notes",
            "sidebar: false",
            "aside: false",
            "prev: false",
            "next: false",
            "---",
            "",
            "# Notes",
            "",
            "<NotesCards />",
        ]

        ZH_NOTES_INDEX_PATH.write_text("\n".join(zh_lines).rstrip() + "\n", encoding="utf-8")
        EN_NOTES_INDEX_PATH.write_text("\n".join(en_lines).rstrip() + "\n", encoding="utf-8")

    def _rebuild_en_note_aliases(self) -> None:
        EN_NOTE_ENTRIES_DIR.mkdir(parents=True, exist_ok=True)

        source_by_slug: dict[str, Path] = {}
        for path in sorted(USER_NOTES_DIR.glob("*.md")):
            source_by_slug[path.stem] = path
        for path in sorted(LEGACY_USER_NOTES_DIR.glob("*.md")):
            source_by_slug.setdefault(path.stem, path)

        for slug, source in source_by_slug.items():
            target = EN_NOTE_ENTRIES_DIR / f"{slug}.md"
            include_rel = Path(os.path.relpath(source, start=target.parent)).as_posix()
            content = "\n".join([f"<!--@include: {include_rel} -->", ""])
            if not target.exists() or target.read_text(encoding="utf-8") != content:
                target.write_text(content, encoding="utf-8")

        existing = {path.stem: path for path in EN_NOTE_ENTRIES_DIR.glob("*.md")}
        for slug, path in existing.items():
            if slug not in source_by_slug:
                path.unlink()

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
        paths_by_slug: dict[str, Path] = {}
        for path in sorted(USER_NOTES_DIR.glob("*.md")):
            paths_by_slug[path.stem] = path

        # Backward compatibility for repositories that still keep notes in docs/notes/entries/*.md.
        for path in sorted(LEGACY_USER_NOTES_DIR.glob("*.md")):
            paths_by_slug.setdefault(path.stem, path)

        # Backward compatibility for repositories that still keep notes in docs/notes/*.md.
        for path in sorted(LEGACY_NOTES_DIR.glob("*.md")):
            if path.name in RESERVED_NOTE_FILES:
                continue
            paths_by_slug.setdefault(path.stem, path)

        for slug, path in sorted(paths_by_slug.items(), key=lambda item: item[0]):

            text = path.read_text(encoding="utf-8")
            frontmatter = self._extract_frontmatter(text)
            title = str(frontmatter.get("title") or path.stem)
            body = FRONTMATTER_PATTERN.sub("", text).strip()

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
            status = self._normalize_status(frontmatter.get("status"), default="mature", strict=False)

            computed_word_count, computed_image_count = self._compute_note_stats(body)
            word_count = self._normalize_count(frontmatter.get("word_count"), fallback=computed_word_count)
            image_count = self._normalize_count(frontmatter.get("image_count"), fallback=computed_image_count)

            entry: dict[str, Any] = {
                "slug": slug,
                "title": title,
                "created_at": created_at,
                "updated_at": updated_at,
                "submitted_at": submitted_at,
                "date": (updated_at or created_at)[:10],
                "word_count": word_count,
                "image_count": image_count,
                "status": status,
                "tags": [str(tag) for tag in tags],
                "link": f"/notes/entries/{slug}"
                if path.parent in (USER_NOTES_DIR, LEGACY_USER_NOTES_DIR)
                else f"/notes/{slug}",
            }

            if include_excerpt:
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
        stage_candidates = [
            "docs/ui",
            "docs/project",
            "docs/public/search-index.json",
            "docs/notes",
            "docs/assets/images",
        ]
        stage_paths: list[str] = []
        for rel in stage_candidates:
            if rel.endswith(".json") or (ROOT_DIR / rel).exists():
                stage_paths.append(rel)

        add = subprocess.run(
            ["git", "add", "--", *stage_paths],
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

    def git_push(
        self,
        *,
        remote: str = "origin",
        branch: str | None = None,
        set_upstream: bool = False,
        force_with_lease: bool = False,
    ) -> dict[str, Any]:
        remote_name = str(remote or "").strip() or "origin"
        branch_name = str(branch or "").strip()

        if not branch_name:
            branch_cmd = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
            if branch_cmd.returncode != 0:
                raise ValueError(branch_cmd.stderr.strip() or "failed to resolve current branch")
            branch_name = branch_cmd.stdout.strip()
            if not branch_name:
                raise ValueError("current branch is detached; please provide branch explicitly")

        push_cmd = ["git", "push"]
        if set_upstream:
            push_cmd.append("-u")
        if force_with_lease:
            push_cmd.append("--force-with-lease")
        push_cmd.extend([remote_name, branch_name])

        push = subprocess.run(
            push_cmd,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if push.returncode != 0:
            raise ValueError(push.stderr.strip() or push.stdout.strip() or "git push failed")

        hash_cmd = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        head_hash = hash_cmd.stdout.strip() if hash_cmd.returncode == 0 else ""

        committed_at_cmd = subprocess.run(
            ["git", "log", "-1", "--format=%cI"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        committed_at = committed_at_cmd.stdout.strip() if committed_at_cmd.returncode == 0 else ""

        remote_url_cmd = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        remote_url = remote_url_cmd.stdout.strip() if remote_url_cmd.returncode == 0 else ""

        return {
            "pushed": True,
            "remote": remote_name,
            "remote_url": remote_url,
            "branch": branch_name,
            "set_upstream": set_upstream,
            "force_with_lease": force_with_lease,
            "hash": head_hash,
            "committed_at": committed_at,
            "stdout": push.stdout.strip(),
            "stderr": push.stderr.strip(),
        }
