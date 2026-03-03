"""Settings management endpoints — read/write .env and manage labels."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["settings"])


# ---------------------------------------------------------------------------
# .env file helpers
# ---------------------------------------------------------------------------

def _find_env_path() -> Path:
    """Locate the .env file that was loaded at startup."""
    # Prefer the CWD (where `terminal-todos web` is usually run from)
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env
    # Fallback: project root is 4 levels above this file (web/backend/routers/settings.py)
    return Path(__file__).resolve().parent.parent.parent.parent / ".env"


def _mask(value: str, keep: int = 10) -> str:
    """Show only the first `keep` chars of a secret."""
    if not value:
        return ""
    return value[:keep] + "…" if len(value) > keep else value


def _write_env(path: Path, updates: dict) -> None:
    """Merge `updates` into the .env file, preserving comments and order."""
    lines: list[str] = path.read_text().splitlines() if path.exists() else []
    written: set[str] = set()
    out: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip().upper()
            if key in updates:
                val = updates[key]
                written.add(key)
                if val is None:
                    continue  # remove line
                out.append(f"{key}={val}")
                continue
        out.append(line)

    # Append brand-new keys that weren't already in the file
    for key, val in updates.items():
        if key.upper() not in written and val is not None:
            out.append(f"{key.upper()}={val}")

    path.write_text("\n".join(out) + "\n")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class UpdateSettingsRequest(BaseModel):
    # API Keys — blank string means "no change"
    openai_api_key: Optional[str] = None
    # Model
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    # General
    user_name: Optional[str] = None
    max_todos_display: Optional[int] = None
    search_results_limit: Optional[int] = None
    verbose_logging: Optional[bool] = None
    # Observability
    enable_arize_tracing: Optional[bool] = None
    arize_space_id: Optional[str] = None
    arize_api_key: Optional[str] = None
    arize_project_name: Optional[str] = None


class RenameLabelRequest(BaseModel):
    old_label: str
    new_label: str


class CreateLabelRequest(BaseModel):
    label: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/settings")
async def get_settings_endpoint() -> dict:
    from terminal_todos.config import get_settings
    s = get_settings()
    key = s.openai_api_key or ""
    arize_key = s.arize_api_key or ""
    return {
        "openai_api_key_set": bool(key),
        "openai_api_key_preview": _mask(key),
        "data_dir": str(s.data_dir),
        "db_path": str(s.db_path),
        "embedding_model": s.embedding_model,
        "llm_model": s.llm_model,
        "user_name": s.user_name,
        "max_todos_display": s.max_todos_display,
        "search_results_limit": s.search_results_limit,
        "verbose_logging": s.verbose_logging,
        "enable_arize_tracing": s.enable_arize_tracing,
        "arize_space_id": s.arize_space_id,
        "arize_api_key_set": bool(arize_key),
        "arize_api_key_preview": _mask(arize_key),
        "arize_project_name": s.arize_project_name,
        "env_path": str(_find_env_path()),
    }


@router.put("/settings")
async def update_settings_endpoint(body: UpdateSettingsRequest) -> dict:
    env_path = _find_env_path()
    updates: dict = {}

    # Only write non-blank, non-None values
    def _set(env_key: str, val):
        if val is not None:
            updates[env_key] = val

    if body.openai_api_key and body.openai_api_key.strip():
        updates["OPENAI_API_KEY"] = body.openai_api_key.strip()
    _set("LLM_MODEL", body.llm_model)
    _set("EMBEDDING_MODEL", body.embedding_model)
    _set("USER_NAME", body.user_name)
    if body.max_todos_display is not None:
        updates["MAX_TODOS_DISPLAY"] = str(body.max_todos_display)
    if body.search_results_limit is not None:
        updates["SEARCH_RESULTS_LIMIT"] = str(body.search_results_limit)
    if body.verbose_logging is not None:
        updates["VERBOSE_LOGGING"] = "true" if body.verbose_logging else "false"
    if body.enable_arize_tracing is not None:
        updates["ENABLE_ARIZE_TRACING"] = "true" if body.enable_arize_tracing else "false"
    if body.arize_space_id is not None:
        updates["ARIZE_SPACE_ID"] = body.arize_space_id or None
    if body.arize_api_key and body.arize_api_key.strip():
        updates["ARIZE_API_KEY"] = body.arize_api_key.strip()
    _set("ARIZE_PROJECT_NAME", body.arize_project_name)

    _write_env(env_path, updates)

    # Reload singleton so subsequent calls pick up new values
    from terminal_todos.config import reset_settings
    reset_settings()

    return {"ok": True, "env_path": str(env_path)}


# ---------------------------------------------------------------------------
# Label management
# ---------------------------------------------------------------------------

def _svc():
    from terminal_todos.core.todo_service import TodoService
    return TodoService()


@router.get("/settings/labels")
async def list_labels() -> list:
    svc = _svc()
    try:
        return svc.get_all_used_labels()
    finally:
        svc.close()


@router.post("/settings/labels")
async def create_label(body: CreateLabelRequest) -> dict:
    label = body.label.strip()
    if not label:
        raise HTTPException(status_code=422, detail="Label must be non-empty")
    svc = _svc()
    try:
        svc.add_label(label)
        return {"ok": True}
    finally:
        svc.close()


@router.post("/settings/labels/rename")
async def rename_label(body: RenameLabelRequest) -> dict:
    if not body.old_label.strip() or not body.new_label.strip():
        raise HTTPException(status_code=422, detail="Both labels must be non-empty")
    svc = _svc()
    try:
        count = svc.rename_label(body.old_label.strip(), body.new_label.strip())
        return {"updated": count}
    finally:
        svc.close()


@router.delete("/settings/labels/{label}")
async def delete_label(label: str) -> dict:
    svc = _svc()
    try:
        count = svc.delete_label(label)
        return {"updated": count}
    finally:
        svc.close()
