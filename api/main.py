from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from api.ingestors.note_ingestor import NoteIngestor


class NotePayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    type: str = Field(default="note")
    status: str = Field(default="draft")
    related: list[str] = Field(default_factory=list)
    submitted_at: str | None = Field(default=None)


class NoteEditPayload(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    images: list[str] | None = Field(default=None)
    type: str | None = Field(default=None)
    status: str | None = Field(default=None)
    related: list[str] | None = Field(default=None)
    submitted_at: str | None = Field(default=None)


app = FastAPI(title="OpenKnowForge API", version="0.2.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/note")
async def create_note(payload: NotePayload) -> dict[str, object]:
    ingestor = NoteIngestor()
    payload_data = payload.model_dump(exclude_none=True)
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


@app.get("/notes/search")
async def search_notes(
    q: str = Query(default="", description="keyword search in title/content/tags"),
    tag: str | None = Query(default=None, description="exact tag filter"),
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
