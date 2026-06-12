"""
Router de administración: control del pipeline, usuarios activos y guardado de oportunidades.
Protegido con API key simple via header X-API-Key.
Usado por el workflow de n8n multi-tenant.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import (
    MpItem, ScraperRun, User, UserConfig, UserOpportunity,
    get_db, get_session
)
from app.models import ScrapeResponse, ScraperRunResponse, SchedulerStatusResponse
from app.scheduler import scheduler_status, trigger_now

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/admin", tags=["Administración"])


def _verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="API key inválida o ausente")
    return x_api_key


# ---------------------------------------------------------------------------
# POST /admin/scrape — dispara pipeline completo en background
# ---------------------------------------------------------------------------

_pipeline_running = False


@router.post(
    "/sync-mp",
    summary="Sincronizar items de MP API → mp_items (sin scoring). Usado por n8n.",
    dependencies=[Depends(_verify_api_key)],
)
async def sync_mp(background_tasks: BackgroundTasks):
    """
    Descarga las compras ágiles de la API de Mercado Público y las guarda
    en mp_items. No realiza scoring por usuario. Los usuarios obtienen sus
    oportunidades llamando a POST /users/me/refresh.
    """
    async def _run():
        from app.mp_api import sync_mp_only
        try:
            result = await sync_mp_only()
            logger.info("Sync MP completado: %s", result)
        except Exception as e:
            logger.exception("Error en sync MP: %s", e)

    background_tasks.add_task(_run)
    return {"message": "Sincronización MP iniciada en background"}


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    summary="Disparar pipeline completo (fetch + scoring de todos los usuarios)",
    dependencies=[Depends(_verify_api_key)],
)
async def trigger_scrape(background_tasks: BackgroundTasks):
    global _pipeline_running
    if _pipeline_running:
        return ScrapeResponse(mensaje="Ya hay un pipeline en curso, espere a que termine.")

    async def _run():
        global _pipeline_running
        _pipeline_running = True
        try:
            await trigger_now()
        finally:
            _pipeline_running = False

    background_tasks.add_task(_run)
    return ScrapeResponse(mensaje="Pipeline SaaS iniciado en background.")


# ---------------------------------------------------------------------------
# GET /admin/status
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
# GET /admin/runs — historial (legacy)
# ---------------------------------------------------------------------------

@router.get(
    "/runs",
    response_model=list[ScraperRunResponse],
    summary="Historial de ejecuciones",
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


# ---------------------------------------------------------------------------
# GET /admin/users/active — lista de usuarios activos con su config
# Usado por el workflow n8n multi-tenant
# ---------------------------------------------------------------------------

class UserConfigPublic(BaseModel):
    user_id: str
    email: str
    name: Optional[str]
    company_name: Optional[str]
    system_prompt: str
    regions: list[str]
    min_amount_clp: int
    max_amount_clp: Optional[int]
    min_score: int
    telegram_chat_id: Optional[str]
    telegram_enabled: bool
    email_notifications: bool


@router.get(
    "/users/active",
    response_model=list[UserConfigPublic],
    summary="Usuarios activos con su configuración (para n8n)",
    dependencies=[Depends(_verify_api_key)],
)
def get_active_users(db: Session = Depends(get_db)):
    rows = (
        db.query(User, UserConfig)
        .join(UserConfig, User.id == UserConfig.user_id)
        .filter(
            User.is_active == True,
            UserConfig.is_active == True,
            UserConfig.system_prompt != "",
        )
        .all()
    )
    return [
        UserConfigPublic(
            user_id=str(u.id),
            email=u.email,
            name=u.name,
            company_name=u.company_name,
            system_prompt=cfg.system_prompt,
            regions=cfg.regions or ["10", "11", "9"],
            min_amount_clp=cfg.min_amount_clp or 0,
            max_amount_clp=cfg.max_amount_clp,
            min_score=cfg.min_score or 60,
            telegram_chat_id=cfg.telegram_chat_id,
            telegram_enabled=cfg.telegram_enabled or False,
            email_notifications=cfg.email_notifications or True,
        )
        for u, cfg in rows
    ]


# ---------------------------------------------------------------------------
# POST /admin/save-opportunity — guarda oportunidad desde n8n
# ---------------------------------------------------------------------------

class SaveOpportunityRequest(BaseModel):
    user_id: str
    codigo: str
    nombre: Optional[str] = None
    organismo: Optional[str] = None
    region: Optional[str] = None
    monto_clp: Optional[int] = None
    fecha_cierre: Optional[str] = None
    url_mp: Optional[str] = None
    score: int
    viabilidad: str
    accion: str
    resumen: Optional[str] = None
    justificacion: Optional[str] = None
    riesgo: Optional[str] = None
    precio_sugerido_clp: Optional[int] = None


class SaveOpportunityResponse(BaseModel):
    opportunity_id: str
    created: bool
    message: str


@router.post(
    "/save-opportunity",
    response_model=SaveOpportunityResponse,
    summary="Guardar oportunidad desde n8n",
    dependencies=[Depends(_verify_api_key)],
)
def save_opportunity(body: SaveOpportunityRequest, db: Session = Depends(get_db)):
    # Upsert del item de MP
    item = db.query(MpItem).filter_by(codigo=body.codigo).first()
    if not item:
        item = MpItem(
            codigo=body.codigo,
            nombre=body.nombre,
            organismo=body.organismo,
            region=body.region,
            monto_clp=body.monto_clp,
            fecha_cierre=body.fecha_cierre,
            url_mp=body.url_mp,
        )
        db.add(item)
        db.flush()

    # Verificar si ya existe la oportunidad para este usuario
    existing = (
        db.query(UserOpportunity)
        .filter_by(user_id=body.user_id, mp_codigo=body.codigo)
        .first()
    )
    if existing:
        db.commit()
        return SaveOpportunityResponse(
            opportunity_id=str(existing.id),
            created=False,
            message=f"Ya existe oportunidad para {body.codigo}",
        )

    opp = UserOpportunity(
        user_id=body.user_id,
        mp_codigo=body.codigo,
        score=body.score,
        viabilidad=body.viabilidad,
        accion=body.accion,
        resumen=(body.resumen or "")[:2000],
        justificacion=(body.justificacion or "")[:2000],
        riesgo=(body.riesgo or "")[:500],
        precio_sugerido_clp=body.precio_sugerido_clp,
    )
    db.add(opp)
    db.commit()
    db.refresh(opp)

    return SaveOpportunityResponse(
        opportunity_id=str(opp.id),
        created=True,
        message=f"Oportunidad {body.codigo} guardada con score {body.score}",
    )


# ---------------------------------------------------------------------------
# PATCH /admin/opportunity/{id}/notified — marcar como notificado
# ---------------------------------------------------------------------------

@router.patch(
    "/opportunity/{opportunity_id}/notified",
    status_code=204,
    summary="Marcar oportunidad como notificada por Telegram",
    dependencies=[Depends(_verify_api_key)],
)
def mark_notified(opportunity_id: UUID, db: Session = Depends(get_db)):
    opp = db.query(UserOpportunity).filter_by(id=opportunity_id).first()
    if opp:
        opp.notificado_telegram = True
        db.commit()
