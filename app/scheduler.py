"""
Scheduler con APScheduler: ejecuta el scraper cada 2 horas.
"""
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database import ScraperRun, get_session, init_db

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: AsyncIOScheduler | None = None


async def _scrape_job():
    """Tarea principal del scheduler: scrape + procesamiento."""
    from app.scraper import run_scraper
    from app.processor import process_all

    logger.info("=== Iniciando job de scraping [%s] ===", datetime.utcnow().isoformat())

    # Registrar inicio en BD
    session = get_session()
    run = ScraperRun(started_at=datetime.utcnow(), status="running")
    session.add(run)
    session.commit()
    run_id = run.id

    try:
        # 1. Scraping
        downloaded_files = await run_scraper()

        # 2. Procesamiento
        result = process_all(downloaded_files)

        # 3. Actualizar registro
        run = session.get(ScraperRun, run_id)
        run.finished_at = datetime.utcnow()
        run.status = "success" if not result["errors"] else "partial"
        run.regions_scraped = len(downloaded_files)
        run.files_downloaded = result["files_processed"]
        run.rows_inserted = result["rows_inserted"]
        run.rows_skipped = result["rows_skipped"]
        if result["errors"]:
            run.error_msg = " | ".join(result["errors"])[:2000]
        session.commit()

        logger.info(
            "=== Job completado: %d filas nuevas, %d duplicadas ===",
            result["rows_inserted"],
            result["rows_skipped"],
        )

    except Exception as exc:
        logger.exception("Error crítico en job de scraping")
        run = session.get(ScraperRun, run_id)
        if run:
            run.finished_at = datetime.utcnow()
            run.status = "error"
            run.error_msg = str(exc)[:2000]
            session.commit()
    finally:
        session.close()


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="America/Santiago")
    return _scheduler


def start_scheduler():
    """Inicia el scheduler. Llamar al arrancar la app."""
    sched = get_scheduler()
    if sched.running:
        return

    sched.add_job(
        _scrape_job,
        trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
        id="compra_agil_scraper",
        name="Scraper CompraÁgil cada 2h",
        replace_existing=True,
        max_instances=1,          # no ejecutar en paralelo
        coalesce=True,            # si se perdió una ejecución, ejecutar una sola vez
    )

    sched.start()
    logger.info(
        "Scheduler iniciado — intervalo: %dh — próxima ejecución: %s",
        settings.scheduler_interval_hours,
        sched.get_job("compra_agil_scraper").next_run_time,
    )


def stop_scheduler():
    sched = get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)
        logger.info("Scheduler detenido")


def scheduler_status() -> dict:
    sched = get_scheduler()
    if not sched.running:
        return {"running": False}
    job = sched.get_job("compra_agil_scraper")
    return {
        "running": True,
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "interval_hours": settings.scheduler_interval_hours,
    }


async def trigger_now():
    """Disparar el job inmediatamente (para el endpoint /admin/scrape)."""
    await _scrape_job()
