"""
Router principal: endpoints de consulta de compras ágiles.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import CompraAgil, get_session
from app.models import (
    CompraDetalle, CompraResponse,
    PaginatedResponse, StatsResponse,
)
from app.config import get_settings

router = APIRouter(prefix="/compras", tags=["Compras Ágiles"])
settings = get_settings()


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /compras
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse, summary="Listar compras con filtros")
def list_compras(
    # Filtros
    region: Optional[str] = Query(None, description="Filtrar por región (parcial, case-insensitive)"),
    organismo: Optional[str] = Query(None, description="Filtrar por nombre de organismo (parcial)"),
    rut_organismo: Optional[str] = Query(None, description="RUT del organismo comprador"),
    proveedor: Optional[str] = Query(None, description="Nombre del proveedor (parcial)"),
    rut_proveedor: Optional[str] = Query(None, description="RUT del proveedor"),
    estado: Optional[str] = Query(None, description="Estado de la OC"),
    fecha_desde: Optional[str] = Query(None, description="Fecha publicación desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha publicación hasta (YYYY-MM-DD)"),
    monto_min: Optional[float] = Query(None, description="Monto total mínimo"),
    monto_max: Optional[float] = Query(None, description="Monto total máximo"),
    q: Optional[str] = Query(None, description="Búsqueda libre en descripción/producto"),
    # Ordenamiento
    order_by: str = Query("id", description="Campo para ordenar: id, monto_total, fecha_publicacion"),
    order_dir: str = Query("desc", description="Dirección: asc | desc"),
    # Paginación
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    db: Session = Depends(get_db),
):
    query = db.query(CompraAgil)

    # Aplicar filtros
    if region:
        query = query.filter(CompraAgil.region.ilike(f"%{region}%"))
    if organismo:
        query = query.filter(CompraAgil.nombre_organismo.ilike(f"%{organismo}%"))
    if rut_organismo:
        query = query.filter(CompraAgil.rut_organismo == rut_organismo)
    if proveedor:
        query = query.filter(CompraAgil.nombre_proveedor.ilike(f"%{proveedor}%"))
    if rut_proveedor:
        query = query.filter(CompraAgil.rut_proveedor == rut_proveedor)
    if estado:
        query = query.filter(CompraAgil.estado.ilike(f"%{estado}%"))
    if fecha_desde:
        query = query.filter(CompraAgil.fecha_publicacion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(CompraAgil.fecha_publicacion <= fecha_hasta)
    if monto_min is not None:
        query = query.filter(CompraAgil.monto_total >= monto_min)
    if monto_max is not None:
        query = query.filter(CompraAgil.monto_total <= monto_max)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (CompraAgil.nombre_producto.ilike(like)) |
            (CompraAgil.descripcion.ilike(like))
        )

    # Ordenamiento
    allowed_order = {"id", "monto_total", "fecha_publicacion", "fecha_descarga"}
    if order_by not in allowed_order:
        order_by = "id"
    col = getattr(CompraAgil, order_by)
    query = query.order_by(desc(col) if order_dir == "desc" else col)

    # Paginación
    total = query.count()
    pages = math.ceil(total / page_size) if total else 1
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        data=items,
    )


# ---------------------------------------------------------------------------
# GET /compras/{id}
# ---------------------------------------------------------------------------

@router.get("/{compra_id}", response_model=CompraDetalle, summary="Detalle de una compra")
def get_compra(compra_id: int, db: Session = Depends(get_db)):
    obj = db.query(CompraAgil).filter(CompraAgil.id == compra_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return obj


# ---------------------------------------------------------------------------
# GET /compras/stats/resumen
# ---------------------------------------------------------------------------

@router.get("/stats/resumen", response_model=StatsResponse, summary="Estadísticas generales")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(CompraAgil.id)).scalar() or 0
    monto_sum = db.query(func.sum(CompraAgil.monto_total)).scalar()
    monto_avg = db.query(func.avg(CompraAgil.monto_total)).scalar()

    # Por región
    region_rows = (
        db.query(
            CompraAgil.region,
            func.count(CompraAgil.id).label("total"),
            func.sum(CompraAgil.monto_total).label("monto_sum"),
        )
        .group_by(CompraAgil.region)
        .order_by(desc("total"))
        .all()
    )
    regiones = [
        {"region": r.region, "total": r.total, "monto_sum": r.monto_sum}
        for r in region_rows
    ]

    # Top 10 organismos
    org_rows = (
        db.query(
            CompraAgil.nombre_organismo,
            CompraAgil.rut_organismo,
            func.count(CompraAgil.id).label("total"),
            func.sum(CompraAgil.monto_total).label("monto_sum"),
        )
        .group_by(CompraAgil.rut_organismo, CompraAgil.nombre_organismo)
        .order_by(desc("monto_sum"))
        .limit(10)
        .all()
    )
    organismos = [
        {
            "nombre_organismo": o.nombre_organismo,
            "rut_organismo": o.rut_organismo,
            "total": o.total,
            "monto_sum": o.monto_sum,
        }
        for o in org_rows
    ]

    # Por estado
    estado_rows = (
        db.query(
            CompraAgil.estado,
            func.count(CompraAgil.id).label("total"),
        )
        .group_by(CompraAgil.estado)
        .order_by(desc("total"))
        .all()
    )
    estados = [{"estado": e.estado, "total": e.total} for e in estado_rows]

    # Última descarga
    ultima = db.query(func.max(CompraAgil.fecha_descarga)).scalar()

    return StatsResponse(
        total_compras=total,
        monto_total_sum=float(monto_sum) if monto_sum else None,
        monto_promedio=float(monto_avg) if monto_avg else None,
        regiones=regiones,
        organismos_top10=organismos,
        estados=estados,
        ultima_actualizacion=ultima,
    )


# ---------------------------------------------------------------------------
# GET /compras/regiones/lista
# ---------------------------------------------------------------------------

@router.get("/regiones/lista", summary="Lista de regiones disponibles en BD")
def get_regiones(db: Session = Depends(get_db)):
    rows = (
        db.query(CompraAgil.region, func.count(CompraAgil.id).label("total"))
        .group_by(CompraAgil.region)
        .order_by(CompraAgil.region)
        .all()
    )
    return [{"region": r.region, "total": r.total} for r in rows]


# ---------------------------------------------------------------------------
# GET /compras/organismos/lista
# ---------------------------------------------------------------------------

@router.get("/organismos/lista", summary="Lista de organismos disponibles")
def get_organismos(
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(
        CompraAgil.nombre_organismo,
        CompraAgil.rut_organismo,
        func.count(CompraAgil.id).label("total"),
    ).group_by(CompraAgil.rut_organismo, CompraAgil.nombre_organismo)

    if region:
        query = query.filter(CompraAgil.region.ilike(f"%{region}%"))

    rows = query.order_by(CompraAgil.nombre_organismo).all()
    return [
        {"nombre": r.nombre_organismo, "rut": r.rut_organismo, "total": r.total}
        for r in rows
    ]
