"""
Router de administración: control del scraper y scheduler.
Protegido con API key simple via header X-API-Key.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import ScraperRun, get_session
from app.models import ScrapeResponse, ScraperRunResponse, SchedulerStatusResponse
from app.scheduler import scheduler_status, trigger_now

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/admin", tags=["Administración"])


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def _verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Validación simple de API key. Reemplazar por OAuth2 en producción."""
    if not x_api_key or x_api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="API key inválida o ausente")
    return x_api_key


# ---------------------------------------------------------------------------
# POST /admin/scrape  — dispara scraping inmediato
# ---------------------------------------------------------------------------

_scrape_running = False


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    summary="Disparar scraping inmediato",
    dependencies=[Depends(_verify_api_key)],
)
async def trigger_scrape(background_tasks: BackgroundTasks):
    global _scrape_running
    if _scrape_running:
        return ScrapeResponse(mensaje="Ya hay un scraping en curso, espere a que termine.")

    async def _run():
        global _scrape_running
        _scrape_running = True
        try:
            await trigger_now()
        finally:
            _scrape_running = False

    background_tasks.add_task(_run)
    return ScrapeResponse(mensaje="Scraping iniciado en background. Consulte /admin/runs para ver el estado.")


# ---------------------------------------------------------------------------
# GET /admin/status  — estado del scheduler
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    response_model=SchedulerStatusResponse,
    summary="Estado del scheduler",
    dependencies=[Depends(_verify_api_key)],
)
def get_status():
    return scheduler_status()


# ---------------------------------------------------------------------------
# GET /admin/runs  — historial de ejecuciones
# ---------------------------------------------------------------------------

@router.get(
    "/runs",
    response_model=list[ScraperRunResponse],
    summary="Historial de ejecuciones del scraper",
    dependencies=[Depends(_verify_api_key)],
)
def get_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    runs = (
        db.query(ScraperRun)
        .order_by(ScraperRun.id.desc())
        .limit(limit)
        .all()
    )
    return runs
