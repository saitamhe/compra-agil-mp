"""
Scheduler: ejecuta el pipeline SaaS multi-tenant cada N horas.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: AsyncIOScheduler | None = None


async def _pipeline_job():
    """Job principal: fetch MP API → score por usuario → notificaciones."""
    from app.mp_api import run_full_pipeline
    from app.notifications import send_pending_notifications

    logger.info("=== Job pipeline SaaS [%s] ===", datetime.now(timezone.utc).isoformat())
    try:
        result = await run_full_pipeline()
        logger.info("Pipeline: %s", result)
        await send_pending_notifications()
    except Exception as e:
        logger.exception("Error crítico en pipeline: %s", e)


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="America/Santiago")
    return _scheduler


def start_scheduler():
    sched = get_scheduler()
    if sched.running:
        return

    sched.add_job(
        _pipeline_job,
        trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
        id="mp_pipeline",
        name="Pipeline SaaS CompraÁgil",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    logger.info(
        "Scheduler iniciado — intervalo: %dh — próxima: %s",
        settings.scheduler_interval_hours,
        sched.get_job("mp_pipeline").next_run_time,
    )


def stop_scheduler():
    sched = get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)
        logger.info("Scheduler detenido")


def scheduler_status() -> dict:
    sched = get_scheduler()
    if not sched.running:
        return {"running": False, "next_run": None, "interval_hours": settings.scheduler_interval_hours}
    job = sched.get_job("mp_pipeline")
    return {
        "running": True,
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "interval_hours": settings.scheduler_interval_hours,
    }


async def trigger_now():
    """Disparar pipeline inmediatamente (llamado desde /admin/scrape)."""
    await _pipeline_job()
