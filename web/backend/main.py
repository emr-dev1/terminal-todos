"""FastAPI backend for Terminal Todos web interface."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from web.backend.routers import chat, todos, notes, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from terminal_todos.db.migrations import run_migrations
    run_migrations()
    yield


app = FastAPI(
    title="Terminal Todos API",
    description="Web API for Terminal Todos — AI-powered notes and todo management",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(todos.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(chat.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# Static files MUST be mounted last — it acts as a catch-all and would shadow
# any route registered after it.
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
