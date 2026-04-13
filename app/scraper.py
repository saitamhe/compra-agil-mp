"""
Downloader directo para CompraÁgil.

La página https://datos-abiertos.chilecompra.cl/descargas/compra-agil
documenta que los archivos están disponibles en:
  https://transparenciachc.blob.core.windows.net/trnspchc/COT_{año}-{mes}.zip

Un ZIP mensual por cada mes, sin separación por región.
Cada ZIP contiene uno o más CSV con todos los registros de ese mes.
No se necesita Playwright — descarga HTTP directa.
"""
import asyncio
import io
import logging
import zipfile
from datetime import datetime
from pathlib import Path

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BASE_URL = "https://transparenciachc.blob.core.windows.net/trnspchc/COT_{year}-{month:02d}.zip"

# Cuántos meses hacia atrás intentar en cada run (acumula histórico)
MONTHS_LOOKBACK = 3


def _month_list(lookback: int = MONTHS_LOOKBACK) -> list[tuple[int, int, str]]:
    """Genera [(año, mes, url), ...] desde el mes actual hacia atrás."""
    now = datetime.now()
    year, month = now.year, now.month
    results = []
    for _ in range(lookback + 1):
        url = BASE_URL.format(year=year, month=month)
        results.append((year, month, url))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return results


async def _download_month(
    year: int, month: int, url: str,
    downloads_dir: Path, client: httpx.AsyncClient
) -> list[Path]:
    """Descarga el ZIP de un mes y extrae los CSV. Retorna lista de rutas."""
    logger.info("Descargando %d-%02d → %s", year, month, url)
    try:
        r = await client.get(url, timeout=120, follow_redirects=True)
        if r.status_code == 404:
            logger.info("  Archivo no disponible aún (404): %d-%02d", year, month)
            return []
        r.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Error HTTP %d-%02d: %s", year, month, exc)
        return []

    logger.info("  Descargado %d KB", len(r.content) // 1024)

    # Extraer CSVs del ZIP en memoria
    csv_paths: list[Path] = []
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for name in zf.namelist():
                if name.lower().endswith(".csv"):
                    dest = downloads_dir / f"COT_{year}-{month:02d}_{Path(name).name}"
                    dest.write_bytes(zf.read(name))
                    logger.info("  CSV extraído: %s (%d KB)", dest.name, dest.stat().st_size // 1024)
                    csv_paths.append(dest)
    except zipfile.BadZipFile as exc:
        logger.error("ZIP corrupto %d-%02d: %s", year, month, exc)

    return csv_paths


async def run_scraper() -> list[Path]:
    """
    Punto de entrada principal del scraper.
    Descarga los últimos MONTHS_LOOKBACK meses y retorna rutas de CSV.
    """
    downloads_dir = Path(settings.downloads_dir)
    downloads_dir.mkdir(parents=True, exist_ok=True)

    months = _month_list(MONTHS_LOOKBACK)
    logger.info(
        "Iniciando descarga de %d meses: %s",
        len(months),
        [f"{y}-{m:02d}" for y, m, _ in months],
    )

    all_csvs: list[Path] = []
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; CompraAgilBot/1.0)"},
        follow_redirects=True,
        timeout=httpx.Timeout(120.0),
    ) as client:
        for year, month, url in months:
            csvs = await _download_month(year, month, url, downloads_dir, client)
            all_csvs.extend(csvs)
            await asyncio.sleep(1)

    logger.info("Descarga completada: %d archivos CSV obtenidos", len(all_csvs))
    return all_csvs
