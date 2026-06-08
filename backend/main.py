import asyncio
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from routers import (chat, shell, search, memory as memory_router,
                     models as models_router, config_router, schedule, update, rag)
from services.scheduler import scheduler_loop

app = FastAPI(title="mi-saina API", version="1.0.10")


def _origin_allowed(origin: str | None) -> bool:
    """N'autorise que les origines locales (web dev) et l'appli desktop (tauri)."""
    if not origin:
        return True  # clients natifs/CLI locaux (pas d'origine de navigateur)
    if origin.startswith("tauri://"):
        return True
    host = (urlparse(origin).hostname or "").lower()
    return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".localhost")


@app.middleware("http")
async def _origin_guard(request: Request, call_next):
    """Anti-CSRF/DNS-rebinding : un site web malveillant ouvert localement ne doit
    pas pouvoir déclencher d'endpoints (le backend exécute des commandes shell).
    Les requêtes sans Origin (app native, curl) passent ; les origines distantes
    de navigateur sont refusées."""
    if not _origin_allowed(request.headers.get("origin")):
        return JSONResponse({"detail": "origine non autorisée"}, status_code=403)
    return await call_next(request)


@app.on_event("startup")
async def _start_scheduler():
    from services import userctx
    userctx.ensure_files()   # crée context.md/profile.md vides si absents
    asyncio.create_task(scheduler_loop())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat")
app.include_router(shell.router, prefix="/shell")
app.include_router(search.router, prefix="/search")
app.include_router(memory_router.router, prefix="/memory")
app.include_router(models_router.router, prefix="/models")
app.include_router(config_router.router, prefix="/config")
app.include_router(schedule.router, prefix="/schedule")
app.include_router(update.router, prefix="/update")
app.include_router(rag.router, prefix="/rag")


@app.get("/health")
async def health():
    return {"status": "ok"}
