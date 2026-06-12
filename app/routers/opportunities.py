"""
Router de oportunidades: dashboard personalizado por usuario.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.database import MpItem, UserOpportunity, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/opportunities", tags=["Oportunidades"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OpportunityResponse(BaseModel):
    id: str
    mp_codigo: str
    nombre: Optional[str]
    organismo: Optional[str]
    region: Optional[str]
    monto_clp: Optional[int]
    fecha_cierre: Optional[str]
    url_mp: Optional[str]
    score: Optional[int]
    viabilidad: Optional[str]
    accion: Optional[str]
    resumen: Optional[str]
    justificacion: Optional[str]
    riesgo: Optional[str]
    precio_sugerido_clp: Optional[int]
    estado_seguimiento: str
    notificado_telegram: bool
    user_notes: Optional[str]
    scored_at: str

    model_config = {"from_attributes": True}


class UpdateOpportunityRequest(BaseModel):
    estado_seguimiento: Optional[str] = None
    user_notes: Optional[str] = None


class PaginatedOpportunities(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    data: list[OpportunityResponse]


class DashboardStats(BaseModel):
    total: int
    por_accion: dict
    por_viabilidad: dict
    score_promedio: Optional[float]
    monto_total_potencial: Optional[int]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.delete("", status_code=204)
def clear_opportunities(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Borra todas las oportunidades del usuario para re-evaluar con el prompt actual."""
    db.query(UserOpportunity).filter_by(user_id=user_id).delete()
    db.commit()


@router.get("", response_model=PaginatedOpportunities)
def list_opportunities(
    accion: Optional[str] = Query(None, description="cotizar|investigar|ignorar"),
    viabilidad: Optional[str] = Query(None),
    estado_seguimiento: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
    order_by: str = Query("score", description="score|scored_at|monto_clp"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    query = (
        db.query(UserOpportunity, MpItem)
        .join(MpItem, UserOpportunity.mp_codigo == MpItem.codigo)
        .filter(UserOpportunity.user_id == user_id)
    )

    if accion:
        query = query.filter(UserOpportunity.accion == accion)
    if viabilidad:
        query = query.filter(UserOpportunity.viabilidad == viabilidad)
    if estado_seguimiento:
        query = query.filter(UserOpportunity.estado_seguimiento == estado_seguimiento)
    if min_score is not None:
        query = query.filter(UserOpportunity.score >= min_score)

    # Ordenamiento
    if order_by == "monto_clp":
        query = query.order_by(desc(MpItem.monto_clp))
    elif order_by == "scored_at":
        query = query.order_by(desc(UserOpportunity.scored_at))
    else:
        query = query.order_by(desc(UserOpportunity.score))

    total = query.count()
    pages = max(1, (total + page_size - 1) // page_size)
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    data = [_to_response(opp, item) for opp, item in rows]

    return PaginatedOpportunities(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        data=data,
    )


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func
    opps = db.query(UserOpportunity).filter_by(user_id=user_id).all()

    por_accion: dict = {}
    por_viabilidad: dict = {}
    scores = []
    monto_total = 0

    for o in opps:
        por_accion[o.accion or "?"] = por_accion.get(o.accion or "?", 0) + 1
        por_viabilidad[o.viabilidad or "?"] = por_viabilidad.get(o.viabilidad or "?", 0) + 1
        if o.score:
            scores.append(o.score)
        if o.precio_sugerido_clp:
            monto_total += o.precio_sugerido_clp

    return DashboardStats(
        total=len(opps),
        por_accion=por_accion,
        por_viabilidad=por_viabilidad,
        score_promedio=round(sum(scores) / len(scores), 1) if scores else None,
        monto_total_potencial=monto_total or None,
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(
    opportunity_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    row = (
        db.query(UserOpportunity, MpItem)
        .join(MpItem, UserOpportunity.mp_codigo == MpItem.codigo)
        .filter(UserOpportunity.id == opportunity_id, UserOpportunity.user_id == user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    return _to_response(*row)


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
def update_opportunity(
    opportunity_id: UUID,
    body: UpdateOpportunityRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    opp = (
        db.query(UserOpportunity)
        .filter_by(id=opportunity_id, user_id=user_id)
        .first()
    )
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")

    if body.estado_seguimiento is not None:
        opp.estado_seguimiento = body.estado_seguimiento
    if body.user_notes is not None:
        opp.user_notes = body.user_notes

    db.commit()
    db.refresh(opp)

    item = db.query(MpItem).filter_by(codigo=opp.mp_codigo).first()
    return _to_response(opp, item)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_response(opp: UserOpportunity, item: Optional[MpItem]) -> OpportunityResponse:
    return OpportunityResponse(
        id=str(opp.id),
        mp_codigo=opp.mp_codigo,
        nombre=item.nombre if item else None,
        organismo=item.organismo if item else None,
        region=item.region if item else None,
        monto_clp=item.monto_clp if item else None,
        fecha_cierre=item.fecha_cierre.isoformat() if item and item.fecha_cierre else None,
        url_mp=item.url_mp if item else None,
        score=opp.score,
        viabilidad=opp.viabilidad,
        accion=opp.accion,
        resumen=opp.resumen,
        justificacion=opp.justificacion,
        riesgo=opp.riesgo,
        precio_sugerido_clp=opp.precio_sugerido_clp,
        estado_seguimiento=opp.estado_seguimiento or "pendiente",
        notificado_telegram=opp.notificado_telegram or False,
        user_notes=opp.user_notes,
        scored_at=opp.scored_at.isoformat() if opp.scored_at else "",
    )
