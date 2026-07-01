import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import security
from routers import (chat, shell, search, memory as memory_router,
                     models as models_router, config_router, schedule, update, rag,
                     health as health_router)
from services.scheduler import scheduler_loop
from services.health_monitor import health_loop
from services.config_map import config_map_loop
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Démarrage : prépare les fichiers de mémoire et lance les boucles de fond
    (planificateur, bilan santé, carte de config, profil machine). Remplace
    `@app.on_event(\"startup\")`, déprécié dans les FastAPI récents."""
    from services import userctx, machine_profile
    userctx.ensure_files()   # crée context.md/profile.md vides si absents
    if getattr(settings, "MACHINE_PROFILE", True):
        asyncio.create_task(asyncio.to_thread(machine_profile.ensure_collected))
    asyncio.create_task(scheduler_loop())
    asyncio.create_task(health_loop())
    asyncio.create_task(config_map_loop())
    yield
    # (rien à nettoyer : les tâches de fond meurent avec le process)


app = FastAPI(title="mi-saina API", version="1.1.2", lifespan=lifespan)


# Réexport (compat tests/imports existants) — source unique : security.py
_origin_allowed = security.origin_allowed
_host_allowed = security.host_allowed


@app.middleware("http")
async def _local_guard(request: Request, call_next):
    """Anti-CSRF/DNS-rebinding : un site web malveillant ne doit pas pouvoir
    déclencher d'endpoints (le backend exécute des commandes shell).
    - Host non local → refusé (DNS rebinding).
    - Origine distante de navigateur → refusée (CSRF) ; l'absence d'Origin
      (app native, curl local) est tolérée une fois le Host validé."""
    if not _host_allowed(request.headers.get("host")):
        return JSONResponse({"detail": "hôte non autorisé"}, status_code=403)
    if not _origin_allowed(request.headers.get("origin")):
        return JSONResponse({"detail": "origine non autorisée"}, status_code=403)
    return await call_next(request)


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
app.include_router(health_router.router, prefix="/health-monitor")


@app.get("/health")
async def health():
    return {"status": "ok"}
