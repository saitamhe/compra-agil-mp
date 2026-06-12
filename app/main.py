"""
CompraÁgil SaaS — API FastAPI multi-tenant.
"""
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import RunLog, User, get_db, get_session, init_db
from app.models import HealthResponse
from app.routers import admin
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.opportunities import router as opportunities_router
from app.scheduler import start_scheduler, stop_scheduler

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"{settings.logs_dir}/api.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Iniciando CompraÁgil SaaS API ===")
    settings.ensure_dirs()
    init_db()
    start_scheduler()
    logger.info("API lista en http://%s:%d", settings.api_host, settings.api_port)
    yield
    stop_scheduler()
    logger.info("=== API detenida ===")


app = FastAPI(
    title="CompraÁgil SaaS",
    description=(
        "Plataforma SaaS para monitoreo automatizado de Compras Ágiles "
        "de Mercado Público Chile. Cada usuario configura su propio perfil "
        "y recibe recomendaciones personalizadas con IA."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(opportunities_router)
app.include_router(admin.router)

# Archivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("app/static/index.html")


@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
def health():
    db_ok = False
    total_users = 0
    total_opportunities = 0
    try:
        db = get_session()
        total_users = db.query(User).count()
        from app.database import UserOpportunity
        total_opportunities = db.query(UserOpportunity).count()
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
        total_records=total_opportunities,
        version="2.0.0",
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Error no manejado: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )
