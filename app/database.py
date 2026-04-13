"""
Base de datos SQLite con SQLAlchemy.
Esquema flexible: almacena datos crudos + columnas indexadas para filtros rápidos.
"""
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Column, Integer, Text, Float, DateTime, String,
    UniqueConstraint, Index, create_engine, text
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    pass


class CompraAgil(Base):
    __tablename__ = "compras_agiles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Columnas principales indexadas (mapeadas desde CSV)
    codigo_oc = Column(String(100), nullable=True, index=True)
    tipo_oc = Column(String(100), nullable=True)
    nombre_organismo = Column(Text, nullable=True)
    rut_organismo = Column(String(20), nullable=True, index=True)
    region = Column(String(100), nullable=True, index=True)
    nombre_producto = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    cantidad = Column(Float, nullable=True)
    unidad_medida = Column(String(100), nullable=True)
    precio_unitario = Column(Float, nullable=True)
    monto_total = Column(Float, nullable=True, index=True)
    fecha_publicacion = Column(String(50), nullable=True, index=True)
    fecha_cierre = Column(String(50), nullable=True)
    estado = Column(String(100), nullable=True, index=True)
    nombre_proveedor = Column(Text, nullable=True)
    rut_proveedor = Column(String(20), nullable=True, index=True)

    # Metadatos de ingesta
    region_origen = Column(String(100), nullable=True)   # región del archivo descargado
    fecha_descarga = Column(DateTime, nullable=True)
    archivo_origen = Column(String(255), nullable=True)

    # Datos crudos completos en JSON para no perder ninguna columna
    raw_data = Column(Text, nullable=True)

    # Hash para deduplicación
    hash_row = Column(String(64), unique=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("hash_row", name="uq_hash_row"),
        Index("ix_fecha_region", "fecha_publicacion", "region"),
        Index("ix_organismo_estado", "rut_organismo", "estado"),
    )

    def __repr__(self):
        return f"<CompraAgil id={self.id} codigo={self.codigo_oc} region={self.region}>"


class ScraperRun(Base):
    """Registro de cada ejecución del scraper."""
    __tablename__ = "scraper_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="running")   # running | success | partial | error
    regions_scraped = Column(Integer, default=0)
    files_downloaded = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    error_msg = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Engine y sesión
# ---------------------------------------------------------------------------

def get_engine():
    settings.ensure_dirs()
    engine = create_engine(
        settings.db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    # WAL mode para concurrencia lectores/escritor
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.execute(text("PRAGMA cache_size=-64000"))  # 64 MB
        conn.commit()
    return engine


_engine = None
_SessionLocal = None


def init_db():
    global _engine, _SessionLocal
    _engine = get_engine()
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    logger.info("Base de datos inicializada: %s", settings.db_path)


def get_session() -> Session:
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


# ---------------------------------------------------------------------------
# Utilidades de inserción
# ---------------------------------------------------------------------------

# Mapas de nombres de columnas CSV → modelo (case-insensitive, sin espacios)
_COLUMN_MAP = {
    # Variantes de nombres que puede traer el CSV de ChileCompra
    "codigooc": "codigo_oc",
    "nrooc": "codigo_oc",
    "numerodeordendecompra": "codigo_oc",
    "tipodeoc": "tipo_oc",
    "tipooc": "tipo_oc",
    "nombreorganismo": "nombre_organismo",
    "organismo": "nombre_organismo",
    "rutorganismo": "rut_organismo",
    "rutentidadcompradora": "rut_organismo",
    "region": "region",
    "nombreregion": "region",
    "nombreproducto": "nombre_producto",
    "descripcion": "descripcion",
    "descripcionproducto": "descripcion",
    "cantidad": "cantidad",
    "unidadmedida": "unidad_medida",
    "preciounitario": "precio_unitario",
    "preciounitarionetoestimado": "precio_unitario",
    "montototal": "monto_total",
    "montototalneto": "monto_total",
    "montoocneto": "monto_total",
    "fechapublicacion": "fecha_publicacion",
    "fechacreacionoc": "fecha_publicacion",
    "fechacierre": "fecha_cierre",
    "fechacierrerecepcionofertas": "fecha_cierre",
    "estado": "estado",
    "estadooc": "estado",
    "nombreproveedor": "nombre_proveedor",
    "proveedor": "nombre_proveedor",
    "rutproveedor": "rut_proveedor",
}


def _normalize_key(k: str) -> str:
    return k.lower().replace(" ", "").replace("_", "").replace("-", "").strip()


def compute_row_hash(row: dict) -> str:
    canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def map_row_to_model(row: dict, region_origen: str, archivo: str) -> dict:
    """Mapea un dict de fila CSV al esquema del modelo."""
    mapped: dict = {}
    raw = {}

    for k, v in row.items():
        normalized = _normalize_key(k)
        raw[k] = v
        model_field = _COLUMN_MAP.get(normalized)
        if model_field and model_field not in mapped:
            mapped[model_field] = v if v != "" else None

    # Convertir numéricos
    for field in ("cantidad", "precio_unitario", "monto_total"):
        val = mapped.get(field)
        if val is not None:
            try:
                mapped[field] = float(str(val).replace(".", "").replace(",", "."))
            except (ValueError, TypeError):
                mapped[field] = None

    mapped["region_origen"] = region_origen
    mapped["archivo_origen"] = archivo
    mapped["fecha_descarga"] = datetime.utcnow()
    mapped["raw_data"] = json.dumps(raw, ensure_ascii=False, default=str)
    mapped["hash_row"] = compute_row_hash(raw)

    return mapped


def bulk_upsert(rows: list[dict], session: Session) -> tuple[int, int]:
    """Inserta filas ignorando duplicados. Retorna (insertadas, omitidas)."""
    inserted = 0
    skipped = 0
    for row in rows:
        exists = session.query(CompraAgil.id).filter_by(hash_row=row["hash_row"]).first()
        if exists:
            skipped += 1
            continue
        obj = CompraAgil(**row)
        session.add(obj)
        inserted += 1
    session.commit()
    return inserted, skipped
