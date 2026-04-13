"""
Modelos Pydantic para la API REST.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Respuesta de una compra
# ---------------------------------------------------------------------------

class CompraResponse(BaseModel):
    id: int
    codigo_oc: Optional[str] = None
    tipo_oc: Optional[str] = None
    nombre_organismo: Optional[str] = None
    rut_organismo: Optional[str] = None
    region: Optional[str] = None
    nombre_producto: Optional[str] = None
    descripcion: Optional[str] = None
    cantidad: Optional[float] = None
    unidad_medida: Optional[str] = None
    precio_unitario: Optional[float] = None
    monto_total: Optional[float] = None
    fecha_publicacion: Optional[str] = None
    fecha_cierre: Optional[str] = None
    estado: Optional[str] = None
    nombre_proveedor: Optional[str] = None
    rut_proveedor: Optional[str] = None
    region_origen: Optional[str] = None
    fecha_descarga: Optional[datetime] = None
    archivo_origen: Optional[str] = None

    model_config = {"from_attributes": True}


class CompraDetalle(CompraResponse):
    """Incluye los datos crudos del CSV original."""
    raw_data: Optional[str] = None


# ---------------------------------------------------------------------------
# Paginación
# ---------------------------------------------------------------------------

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    data: list[CompraResponse]


# ---------------------------------------------------------------------------
# Estadísticas
# ---------------------------------------------------------------------------

class StatsResponse(BaseModel):
    total_compras: int
    monto_total_sum: Optional[float] = None
    monto_promedio: Optional[float] = None
    regiones: list[dict]       # [{region, total, monto_sum}]
    organismos_top10: list[dict]
    estados: list[dict]
    ultima_actualizacion: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class ScrapeResponse(BaseModel):
    mensaje: str
    job_id: Optional[str] = None


class ScraperRunResponse(BaseModel):
    id: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: str
    regions_scraped: int
    files_downloaded: int
    rows_inserted: int
    rows_skipped: int
    error_msg: Optional[str] = None

    model_config = {"from_attributes": True}


class SchedulerStatusResponse(BaseModel):
    running: bool
    next_run: Optional[str] = None
    interval_hours: Optional[int] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    db_ok: bool
    scheduler_running: bool
    total_records: int
    version: str = "1.0.0"
