from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from api.ingestors.note_ingestor import NoteIngestor


class NotePayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    type: str = Field(default="note")
    status: Optional[str] = Field(default=None)
    is_draft: Optional[bool] = Field(default=None)
    related: list[str] = Field(default_factory=list)
    submitted_at: Optional[str] = Field(default=None)


class NoteEditPayload(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None)
    images: Optional[list[str]] = Field(default=None)
    type: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_draft: Optional[bool] = Field(default=None)
    related: Optional[list[str]] = Field(default=None)
    submitted_at: Optional[str] = Field(default=None)


class NoteStatusPayload(BaseModel):
    status: Optional[str] = Field(default=None)
    is_draft: Optional[bool] = Field(default=None)
    submitted_at: Optional[str] = Field(default=None)


def _canonical_status_name(value: str) -> str:
    raw = str(value).strip().lower()
    if raw == "published":
        return "mature"
    return raw


def _resolve_status_value(
    *,
    status: Optional[str],
    is_draft: Optional[bool],
    default: Optional[str],
) -> Optional[str]:
    resolved = _canonical_status_name(status) if status is not None else None

    if is_draft is not None:
        from_is_draft = "draft" if is_draft else "mature"
        if resolved is not None and resolved != from_is_draft:
            raise ValueError("status conflicts with is_draft")
        resolved = from_is_draft

    if resolved is None:
        return default
    return resolved


app = FastAPI(title="OpenKnowForge API", version="0.2.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/note")
async def create_note(payload: NotePayload) -> dict[str, object]:
    ingestor = NoteIngestor()
    payload_data = payload.model_dump(exclude_none=True)
    is_draft = payload_data.pop("is_draft", None)
    try:
        payload_data["status"] = _resolve_status_value(
            status=payload_data.get("status"),
            is_draft=is_draft,
            default="mature",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload_data["note_type"] = payload_data.pop("type")
    try:
        result = await ingestor.ingest(payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    return {"ok": True, "result": result}


@app.get("/notes")
async def list_notes() -> dict[str, object]:
    ingestor = NoteIngestor()
    try:
        notes = ingestor.list_notes()
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    return {"ok": True, "result": notes}


@app.get("/notes/drafts")
async def list_draft_notes() -> dict[str, object]:
    ingestor = NoteIngestor()
    try:
        notes = ingestor.list_drafts()
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    return {"ok": True, "result": notes, "count": len(notes)}


@app.get("/notes/search")
async def search_notes(
    q: str = Query(default="", description="keyword search in title/content/tags"),
    tag: Optional[str] = Query(default=None, description="exact tag filter"),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    ingestor = NoteIngestor()
    try:
        notes = ingestor.search(query=q, tag=tag, limit=limit)
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    return {
        "ok": True,
        "result": notes,
        "query": {
            "q": q,
            "tag": tag,
            "limit": limit,
            "count": len(notes),
        },
    }


@app.get("/note/{slug}")
async def read_note(slug: str) -> dict[str, object]:
    ingestor = NoteIngestor()
    try:
        result = ingestor.read(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    return {"ok": True, "result": result}


@app.delete("/note/{slug}")
async def delete_note(slug: str) -> dict[str, object]:
    ingestor = NoteIngestor()
    try:
        result = ingestor.delete(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    return {"ok": True, "result": result}


@app.put("/note/{slug}")
async def edit_note(slug: str, payload: NoteEditPayload) -> dict[str, object]:
    ingestor = NoteIngestor()
    payload_data = payload.model_dump(exclude_none=True)
    if not payload_data:
        raise HTTPException(status_code=400, detail="at least one field must be provided")
    is_draft = payload_data.pop("is_draft", None)
    try:
        resolved_status = _resolve_status_value(
            status=payload_data.get("status"),
            is_draft=is_draft,
            default=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if resolved_status is not None:
        payload_data["status"] = resolved_status
    elif "status" in payload_data:
        payload_data.pop("status", None)
    if "type" in payload_data:
        payload_data["note_type"] = payload_data.pop("type")

    try:
        result = await ingestor.update(slug, payload_data)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    return {"ok": True, "result": result}


@app.patch("/note/{slug}/status")
async def update_note_status(slug: str, payload: NoteStatusPayload) -> dict[str, object]:
    ingestor = NoteIngestor()
    try:
        resolved_status = _resolve_status_value(
            status=payload.status,
            is_draft=payload.is_draft,
            default=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if resolved_status is None:
        raise HTTPException(status_code=400, detail="status or is_draft must be provided")

    try:
        result = await ingestor.update_status(
            slug=slug,
            status=resolved_status,
            submitted_at=payload.submitted_at,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    return {"ok": True, "result": result}
