"""REST endpoints for todo management."""

from typing import Annotated, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from terminal_todos.core.todo_service import TodoService

router = APIRouter(tags=["todos"])


# ---- Dependency: creates a TodoService and always closes it after the response ----

async def _svc():
    service = TodoService()
    try:
        yield service
    finally:
        try:
            service.close()
        except Exception:
            pass


SvcDep = Annotated[TodoService, Depends(_svc)]


def _todo_to_dict(todo) -> dict:
    return {
        "id": todo.id,
        "content": todo.content,
        "completed": todo.completed,
        "priority": todo.priority,
        "created_at": todo.created_at.isoformat() if todo.created_at else None,
        "completed_at": todo.completed_at.isoformat() if todo.completed_at else None,
        "due_date": todo.due_date.isoformat() if todo.due_date else None,
        "note_id": todo.note_id,
        "focus_order": todo.focus_order,
        "labels": todo.get_labels() if hasattr(todo, "get_labels") else [],
    }


class CreateTodoRequest(BaseModel):
    content: str
    priority: int = 0
    due_date: Optional[str] = None


class UpdateTodoRequest(BaseModel):
    content: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[str] = None
    labels: Optional[list] = None


# ============================================================
# IMPORTANT: Static-path routes MUST come before parameterized
# routes like /{todo_id} to avoid 405 from Starlette's router.
# ============================================================

@router.get("/todos")
async def list_todos(service: SvcDep, status: str = "active") -> list:
    if status == "active":
        todos = service.list_active(limit=200)
    elif status == "completed":
        todos = service.list_completed(limit=200)
    else:
        todos = service.list_all(limit=200)
    return [_todo_to_dict(t) for t in todos]


@router.post("/todos", status_code=201)
async def create_todo(service: SvcDep, body: CreateTodoRequest) -> dict:
    due = None
    if body.due_date:
        try:
            due = date.fromisoformat(body.due_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="due_date must be ISO format (YYYY-MM-DD)")
    todo = service.create_todo(content=body.content, priority=body.priority, due_date=due)
    return _todo_to_dict(todo)


@router.get("/todos/labels")
async def get_all_labels(service: SvcDep) -> list:
    """Return all label strings used across todos (for autocomplete suggestions)."""
    return service.get_all_used_labels()


@router.get("/todos/stats")
async def get_stats(service: SvcDep) -> dict:
    return service.get_todo_count()


@router.get("/todos/focus")
async def list_focused(service: SvcDep) -> list:
    todos = service.list_focused()
    return [_todo_to_dict(t) for t in todos]


# ---- Parameterized routes (must come after static ones above) ----

@router.patch("/todos/{todo_id}")
async def update_todo(todo_id: int, service: SvcDep, body: UpdateTodoRequest) -> dict:
    from terminal_todos.db.models import Todo as TodoModel

    todo = service.get_todo(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    # All simple field mutations go through the service session so that
    # SQLAlchemy's identity map stays coherent when update_labels runs later.
    simple_dirty = False
    if body.content is not None:
        todo.content = body.content
        simple_dirty = True

    if body.priority is not None:
        todo.priority = body.priority
        simple_dirty = True

    if simple_dirty:
        service.session.commit()
        service.session.refresh(todo)

    if body.due_date is not None:
        due = date.fromisoformat(body.due_date) if body.due_date else None
        service.update_due_date(todo_id, due)

    if body.labels is not None:
        service.update_labels(todo_id, body.labels)

    updated = service.get_todo(todo_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Todo not found after update")
    return _todo_to_dict(updated)


@router.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: int, service: SvcDep) -> None:
    ok = service.delete_todo(todo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Todo not found")


@router.post("/todos/{todo_id}/complete")
async def complete_todo(todo_id: int, service: SvcDep) -> dict:
    todo = service.complete_todo(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return _todo_to_dict(todo)


@router.post("/todos/{todo_id}/uncomplete")
async def uncomplete_todo(todo_id: int, service: SvcDep) -> dict:
    todo = service.uncomplete_todo(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return _todo_to_dict(todo)


@router.post("/todos/{todo_id}/focus", status_code=201)
async def add_to_focus(todo_id: int, service: SvcDep) -> dict:
    ok = service.add_to_focus(todo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo = service.get_todo(todo_id)
    return _todo_to_dict(todo)


@router.delete("/todos/{todo_id}/focus", status_code=204)
async def remove_from_focus(todo_id: int, service: SvcDep) -> None:
    service.remove_from_focus(todo_id)
