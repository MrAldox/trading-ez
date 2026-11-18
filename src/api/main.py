"""
Trading EZ - Servidor de Producción FastAPI y Ensamblador de Rutas.
Configurado para ejecución local y despliegue directo en Render con puerto dinámico.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# Garantizar que el directorio raíz esté en sys.path tanto en Docker/Render como en local
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.core.config import settings, BASE_DIR
from src.api.routers.opportunities import router as opp_router
from src.api.routers.market import router as market_router
from src.api.routers.backtest import router as backtest_router
from src.api.routers.model import router as model_router
from src.api.routers.paper import router as paper_router
from src.api.routers.screener import router as screener_router
from src.api.routers.news import router as news_router
from src.api.routers.calendar import router as calendar_router
from src.api.routers.journal import router as journal_router
from src.api.routers.alerts import router as alerts_router
from src.scheduler.jobs import scheduler

FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización del planificador de tareas en segundo plano
    scheduler.start()
    yield
    # Limpieza al apagar
    scheduler.shutdown()

app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    description="Market Terminal Pro - Selección Cuantitativa y Calibración Fuera de Muestra",
    lifespan=lifespan,
)

# CORS Middleware para desarrollo y despliegues web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar Routers de la API
app.include_router(opp_router)
app.include_router(market_router)
app.include_router(backtest_router)
app.include_router(model_router)
app.include_router(paper_router)
app.include_router(screener_router)
app.include_router(news_router)
app.include_router(calendar_router)
app.include_router(journal_router)
app.include_router(alerts_router)

@app.get("/api/health")
def healthcheck():
    return {
        "status": "healthy",
        "app": settings.app.name,
        "version": settings.app.version,
        "environment": settings.app.env,
    }

# Servir Frontend SPA (Vanilla JS + Canvas + CSS)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Si la ruta apunta a un archivo estático específico
        target = FRONTEND_DIR / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        # Fallback a index.html para SPA routing
        index_file = FRONTEND_DIR / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return {"app": settings.app.name, "message": "Frontend inicializándose"}

def start():
    """Punto de entrada de ejecución con Uvicorn."""
    import uvicorn
    port = int(os.environ.get("PORT", settings.app.port))
    host = os.environ.get("HOST", settings.app.host)
    uvicorn.run("src.api.main:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    start()
