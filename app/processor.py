"""
Procesador de CSVs de CompraÁgil.
Usa chunks de pandas para manejar archivos de 500+ MB sin OOM.
"""
import logging
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.database import bulk_upsert, get_session, map_row_to_model

logger = logging.getLogger(__name__)
settings = get_settings()

CHUNK_SIZE = 10_000   # filas por lote → ~50 MB RAM por chunk


def _detect_encoding(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1", "iso-8859-1", "cp1252"):
        try:
            with open(path, encoding=enc) as f:
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _detect_separator(path: Path, encoding: str) -> str:
    with open(path, encoding=encoding) as f:
        first_line = f.readline()
    counts = {sep: first_line.count(sep) for sep in [";", ",", "\t", "|"]}
    return max(counts, key=counts.get)


def _infer_region_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    # Formato: COT_YYYY-MM_nombrearchivo → "Cot YYYY-MM"
    parts = stem.split("_")
    if len(parts) >= 2:
        return f"Cot {parts[1]}" if parts[1] else stem
    return stem


def process_csv(path: Path) -> tuple[int, int]:
    """Lee un CSV en chunks, normaliza e inserta en SQLite."""
    logger.info("Procesando: %s (%.1f MB)", path.name, path.stat().st_size / 1024 / 1024)

    if not path.exists() or path.stat().st_size == 0:
        logger.warning("Archivo vacío o inexistente: %s", path)
        return 0, 0

    encoding = _detect_encoding(path)
    sep = _detect_separator(path, encoding)
    logger.debug("Encoding=%s  Separador='%s'", encoding, sep)

    region_origen = _infer_region_from_filename(path.name)
    total_inserted = 0
    total_skipped = 0
    chunk_num = 0

    try:
        reader = pd.read_csv(
            path,
            encoding=encoding,
            sep=sep,
            dtype=str,
            keep_default_na=False,
            on_bad_lines="warn",
            engine="python",
            chunksize=CHUNK_SIZE,
        )

        # Detectar columnas del primer chunk
        first_chunk = True

        for chunk in reader:
            chunk_num += 1

            # Limpiar nombres de columnas (solo una vez)
            chunk.columns = [c.strip() for c in chunk.columns]

            if first_chunk:
                logger.info("Columnas (%d): %s", len(chunk.columns), list(chunk.columns))
                first_chunk = False

            # Convertir a lista de dicts y mapear
            mapped_rows = []
            for _, row in chunk.iterrows():
                row_dict = {k: v for k, v in row.to_dict().items() if v != ""}
                if not row_dict:
                    continue
                mapped_rows.append(map_row_to_model(row_dict, region_origen, path.name))

            if not mapped_rows:
                continue

            # Insertar chunk en BD
            with get_session() as session:
                ins, skip = bulk_upsert(mapped_rows, session)
            total_inserted += ins
            total_skipped += skip

            if chunk_num % 10 == 0:
                logger.info(
                    "  chunk %d → %d insertadas, %d omitidas (total: %d)",
                    chunk_num, ins, skip, total_inserted,
                )

    except Exception as exc:
        logger.error("Error procesando %s en chunk %d: %s", path.name, chunk_num, exc)
        return total_inserted, total_skipped

    logger.info("  ✓ %s: %d insertadas, %d duplicadas", path.name, total_inserted, total_skipped)

    # Eliminar CSV tras procesar para liberar disco
    try:
        path.unlink()
        logger.debug("  Eliminado: %s", path.name)
    except Exception:
        pass

    return total_inserted, total_skipped


def process_all(paths: list[Path]) -> dict:
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
