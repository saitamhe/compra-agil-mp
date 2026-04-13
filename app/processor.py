"""
Procesador de CSVs descargados de CompraÁgil.

Responsabilidades:
- Detectar encoding y separador del CSV
- Normalizar columnas
- Mapear al esquema de BD
- Insertar con deduplicación
"""
import logging
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.database import bulk_upsert, get_session, map_row_to_model

logger = logging.getLogger(__name__)
settings = get_settings()


def _detect_encoding(path: Path) -> str:
    """Detecta el encoding del archivo probando los más comunes."""
    for enc in ("utf-8-sig", "utf-8", "latin-1", "iso-8859-1", "cp1252"):
        try:
            with open(path, encoding=enc) as f:
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _detect_separator(path: Path, encoding: str) -> str:
    """Detecta el separador del CSV (coma, punto y coma, tabulación)."""
    with open(path, encoding=encoding) as f:
        first_line = f.readline()
    counts = {sep: first_line.count(sep) for sep in [";", ",", "\t", "|"]}
    return max(counts, key=counts.get)


def _infer_region_from_filename(filename: str) -> str:
    """Extrae el nombre de región del nombre del archivo."""
    stem = Path(filename).stem
    # Formato: RegionName_YYYYMMDD_HHMMSS
    parts = stem.rsplit("_", 2)
    if len(parts) >= 3:
        return parts[0].replace("_", " ").title()
    return stem.replace("_", " ").title()


def process_csv(path: Path) -> tuple[int, int]:
    """
    Lee un CSV descargado, lo normaliza e inserta en SQLite.
    Retorna (filas_insertadas, filas_omitidas).
    """
    logger.info("Procesando: %s", path.name)

    if not path.exists() or path.stat().st_size == 0:
        logger.warning("Archivo vacío o inexistente: %s", path)
        return 0, 0

    # Detección automática de formato
    encoding = _detect_encoding(path)
    sep = _detect_separator(path, encoding)
    logger.debug("Encoding=%s  Separador='%s'", encoding, sep)

    try:
        df = pd.read_csv(
            path,
            encoding=encoding,
            sep=sep,
            dtype=str,            # todo como string, convertimos en db.map_row_to_model
            keep_default_na=False,
            on_bad_lines="warn",
            engine="python",
        )
    except Exception as exc:
        logger.error("Error leyendo CSV %s: %s", path.name, exc)
        return 0, 0

    if df.empty:
        logger.warning("CSV vacío después de leer: %s", path.name)
        return 0, 0

    # Limpiar nombres de columnas
    df.columns = [c.strip() for c in df.columns]
    logger.info("Columnas detectadas (%d): %s", len(df.columns), list(df.columns))

    # Región origen desde nombre de archivo
    region_origen = _infer_region_from_filename(path.name)

    # Convertir filas a dicts y mapear al modelo
    mapped_rows = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        # Eliminar columnas completamente vacías
        row_dict = {k: v for k, v in row_dict.items() if v != ""}
        if not row_dict:
            continue
        mapped = map_row_to_model(row_dict, region_origen, path.name)
        mapped_rows.append(mapped)

    if not mapped_rows:
        return 0, 0

    # Insertar en BD con deduplicación
    with get_session() as session:
        inserted, skipped = bulk_upsert(mapped_rows, session)

    logger.info("  ✓ %d insertadas, %d duplicadas (omitidas)", inserted, skipped)
    return inserted, skipped


def process_all(paths: list[Path]) -> dict:
    """Procesa múltiples archivos CSV. Retorna resumen."""
    total_inserted = 0
    total_skipped = 0
    errors = []

    for path in paths:
        try:
            ins, skip = process_csv(path)
            total_inserted += ins
            total_skipped += skip
        except Exception as exc:
            msg = f"{path.name}: {exc}"
            logger.error("Error procesando %s", msg)
            errors.append(msg)

    return {
        "files_processed": len(paths),
        "rows_inserted": total_inserted,
        "rows_skipped": total_skipped,
        "errors": errors,
    }
