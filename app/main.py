"""
Punto de entrada de la API FastAPI — CompraÁgil Mercado Público Chile.
"""
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import CompraAgil, ScraperRun, get_session, init_db
from app.models import HealthResponse
from app.routers import admin, compras
from app.scheduler import start_scheduler, stop_scheduler

settings = get_settings()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"{settings.logs_dir}/api.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=== Iniciando CompraÁgil API ===")
    settings.ensure_dirs()
    init_db()
    start_scheduler()
    logger.info("API lista en http://%s:%d", settings.api_host, settings.api_port)
    yield
    # Shutdown
    stop_scheduler()
    logger.info("=== API detenida ===")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CompraÁgil API",
    description=(
        "API REST para consultar datos de Compras Ágiles de Mercado Público Chile. "
        "Los datos se actualizan automáticamente cada 2 horas desde "
        "https://datos-abiertos.chilecompra.cl/descargas/compra-agil"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restringir en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(compras.router)
app.include_router(admin.router)

# Archivos estáticos (dashboard)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ---------------------------------------------------------------------------
# Endpoints raíz
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    """Sirve el dashboard visual."""
    return FileResponse("app/static/index.html")


@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
def health():
    db_ok = False
    total = 0
    try:
        db = get_session()
        total = db.query(CompraAgil).count()
        db.close()
        db_ok = True
    except Exception:
        pass

    from app.scheduler import scheduler_status
    sched = scheduler_status()

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_ok=db_ok,
        scheduler_running=sched.get("running", False),
        total_records=total,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Error no manejado: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )
