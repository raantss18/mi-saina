from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, shell, search, memory as memory_router, models as models_router, config_router

app = FastAPI(title="LocalMind API", version="1.0.0")

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


@app.get("/health")
async def health():
    return {"status": "ok"}
