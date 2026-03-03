"""REST endpoints for note management."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from terminal_todos.core.note_service import NoteService
from terminal_todos.extraction.todo_extractor import TodoExtractor

router = APIRouter(tags=["notes"])


async def _svc():
    service = NoteService()
    try:
        yield service
    finally:
        try:
            service.close()
        except Exception:
            pass


SvcDep = Annotated[NoteService, Depends(_svc)]


def _note_to_dict(note) -> dict:
    return {
        "id": note.id,
        "content": note.content,
        "title": note.title,
        "note_type": note.note_type,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        "category": note.category,
        "summary": note.summary,
        "keywords": note.get_keywords() if hasattr(note, "get_keywords") else [],
        "tags": note.get_tags() if hasattr(note, "get_tags") else [],
    }


class CreateNoteRequest(BaseModel):
    content: str
    title: Optional[str] = None


class ExtractRequest(BaseModel):
    content: str


# ---- Static-path routes first (must come before /{note_id} to avoid 405) ----

@router.get("/notes")
async def list_notes(service: SvcDep, limit: int = 50) -> list:
    notes = service.list_all(limit=limit)
    return [_note_to_dict(n) for n in notes]


@router.post("/notes", status_code=201)
async def create_note(service: SvcDep, body: CreateNoteRequest) -> dict:
    note = service.create_note(content=body.content, title=body.title)
    return _note_to_dict(note)


@router.get("/notes/search")
async def search_notes(service: SvcDep, q: str, limit: int = 10) -> list:
    results = service.search_notes(query=q, k=limit)
    return results


@router.post("/notes/extract")
async def extract_todos_from_text(body: ExtractRequest) -> dict:
    """Run AI extraction on raw text and return candidate todos without saving anything."""
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="content must not be empty")
    try:
        extractor = TodoExtractor()
        result = await extractor.extract_async(body.content)
        return {
            "title": result.title,
            "note_type": result.note_type,
            "todos": [{"content": t.content, "priority": t.priority} for t in result.todos],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


# ---- Parameterized routes last ----

@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: int, service: SvcDep) -> None:
    ok = service.delete_note(note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
