"""
Cliente para la API REST de Mercado Público v2 (compra-agil).
Reemplaza el scraper de CSV para obtener publicaciones en tiempo real.
"""
import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Optional

import httpx

from app.config import get_settings
from app.database import MpItem, RunLog, UserConfig, UserOpportunity, get_session
from app.prompt_ai import score_opportunity

logger = logging.getLogger(__name__)
settings = get_settings()

MP_API_BASE = settings.mp_api_base
MP_TICKET = settings.mp_ticket


# ---------------------------------------------------------------------------
# Fetcher principal
# ---------------------------------------------------------------------------

async def fetch_mp_items(regions: str = None, estado: str = "publicada") -> list[dict]:
    """
    Descarga todas las páginas de compras ágiles publicadas.
    Retorna lista de dicts con los campos normalizados.
    """
    regions = regions or settings.mp_regions_default
    items = []
    page = 1
    total_pages = 1
    retries = 0

    async with httpx.AsyncClient(timeout=30) as client:
        while page <= total_pages and retries < 5:
            try:
                resp = await client.get(
                    MP_API_BASE,
                    headers={"ticket": MP_TICKET},
                    params={
                        "region": regions,
                        "estado": estado,
                        "tamano_pagina": settings.mp_page_size,
                        "numero_pagina": page,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retries += 1
                    logger.warning("429 en página %d, reintento %d/5", page, retries)
                    await asyncio.sleep(5)
                    continue
                logger.error("HTTP error en página %d: %s", page, e)
                break
            except Exception as e:
                logger.error("Error fetching página %d: %s", page, e)
                break

            if data.get("success") != "OK" or not data.get("payload", {}).get("items"):
                logger.warning("API sin items en página %d", page)
                break

            payload = data["payload"]
            total_pages = payload["paginacion"]["total_paginas"]
            raw_items = payload["items"]
            items.extend(raw_items)
            logger.info("Página %d/%d — %d items (total: %d)", page, total_pages, len(raw_items), len(items))

            retries = 0
            page += 1
            if page <= total_pages:
                await asyncio.sleep(2)

    return items


def normalize_item(raw: dict) -> dict:
    """Normaliza un item de la API al formato interno."""
    codigo = raw.get("codigo", "")
    return {
        "codigo": codigo,
        "nombre": raw.get("nombre", ""),
        "organismo": raw.get("institucion", {}).get("organismo_comprador", ""),
        "unidad_compra": raw.get("institucion", {}).get("unidad_compra", ""),
        "region": raw.get("institucion", {}).get("nombre_region", ""),
        "monto_clp": raw.get("montos", {}).get("monto_disponible_clp"),
        "fecha_cierre": _parse_date(raw.get("fechas", {}).get("fecha_cierre")),
        "estado": (raw.get("estado") or {}).get("codigo", "publicada") if isinstance(raw.get("estado"), dict) else (raw.get("estado") or "publicada"),
        "url_mp": f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={codigo}",
        "raw_data": raw,
    }


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    return date_str.split(" ")[0] if " " in date_str else date_str[:10]


# ---------------------------------------------------------------------------
# Pipeline completo: fetch → cache → score por usuario
# ---------------------------------------------------------------------------

async def sync_mp_only() -> dict:
    """Fetch items de MP API y hace upsert en mp_items. Sin scoring."""
    db = get_session()
    try:
        raw_items = await fetch_mp_items()
        items = [
            normalize_item(r) for r in raw_items
            if (r.get("montos", {}).get("monto_disponible_clp") or 0) > 0
        ]
        new_count = _upsert_mp_items(items, db)
        logger.info("Sync MP: %d items totales, %d nuevos", len(items), new_count)
        return {"items_fetched": len(items), "items_new": new_count}
    finally:
        db.close()


async def score_user_from_db(config: UserConfig, db, max_items: int = 50) -> dict:
    """
    Lee mp_items de la BD y aplica scoring para un usuario específico.
    Solo procesa ítems que el usuario aún no tiene en user_opportunities.
    """
    # Obtener códigos ya procesados para este usuario
    existing_codes = {
        row[0] for row in
        db.query(UserOpportunity.mp_codigo).filter_by(user_id=config.user_id).all()
    }

    # Query base con filtros de monto
    query = db.query(MpItem).filter(MpItem.monto_clp > 0)
    if config.min_amount_clp:
        query = query.filter(MpItem.monto_clp >= config.min_amount_clp)
    if config.max_amount_clp:
        query = query.filter(MpItem.monto_clp <= config.max_amount_clp)

    # Convertir a dict (mismo formato que normalize_item devuelve)
    all_items = [
        {
            "codigo": i.codigo,
            "nombre": i.nombre or "",
            "organismo": i.organismo or "",
            "unidad_compra": i.unidad_compra or "",
            "region": i.region or "",
            "monto_clp": i.monto_clp,
            "fecha_cierre": i.fecha_cierre,
            "url_mp": i.url_mp,
            "raw_data": i.raw_data or {},
        }
        for i in query.all()
        if i.codigo not in existing_codes
    ]

    # Limitar para no saturar OpenAI en una sola llamada
    items_to_score = all_items[:max_items]
    remaining = max(0, len(all_items) - max_items)

    new_count = await _score_for_user(config, items_to_score, db)
    return {
        "available": len(all_items),
        "scored": len(items_to_score),
        "new_opportunities": new_count,
        "remaining": remaining,
    }


async def run_full_pipeline() -> dict:
    """
    Pipeline multi-tenant:
    1. Fetch items de MP API
    2. Guardar/actualizar caché en mp_items
    3. Para cada usuario activo con config, score personalizado
    4. Guardar oportunidades en user_opportunities
    """
    db = get_session()
    run = RunLog(status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # 1. Fetch
        logger.info("=== Iniciando pipeline MP ===")
        raw_items = await fetch_mp_items()
        items = [normalize_item(r) for r in raw_items if (r.get("montos", {}).get("monto_disponible_clp") or 0) > 0]
        run.items_fetched = len(items)
        db.commit()
        logger.info("Items con monto > 0: %d", len(items))

        # 2. Upsert caché
        items_new = _upsert_mp_items(items, db)
        run.items_new = items_new
        db.commit()

        # 3. Obtener usuarios activos con prompt configurado
        configs = (
            db.query(UserConfig)
            .filter(UserConfig.is_active == True)
            .filter(UserConfig.system_prompt != "")
            .all()
        )
        run.users_processed = len(configs)
        db.commit()
        logger.info("Usuarios activos con prompt: %d", len(configs))

        total_opportunities = 0
        for config in configs:
            result = await score_user_from_db(config, db, max_items=50)
            total_opportunities += result["new_opportunities"]

        run.opportunities_created = total_opportunities
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("=== Pipeline completo: %d oportunidades creadas ===", total_opportunities)
        return {
            "items_fetched": len(items),
            "items_new": items_new,
            "users_processed": len(configs),
            "opportunities_created": total_opportunities,
        }

    except Exception as e:
        logger.exception("Error en pipeline: %s", e)
        run.status = "failed"
        run.error_msg = str(e)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise
    finally:
        db.close()


def _upsert_mp_items(items: list[dict], db) -> int:
    new_count = 0
    for item in items:
        existing = db.query(MpItem).filter_by(codigo=item["codigo"]).first()
        if existing:
            for k, v in item.items():
                if k != "codigo":
                    setattr(existing, k, v)
        else:
            db.add(MpItem(**item))
            new_count += 1
    db.commit()
    return new_count


async def _score_for_user(config: UserConfig, items: list[dict], db) -> int:
    """Ejecuta el scoring personalizado de todos los items para un usuario."""
    user_id = config.user_id
    min_score = config.min_score or 60
    regions = set(config.regions or [])
    min_clp = config.min_amount_clp or 0
    max_clp = config.max_amount_clp

    # Filtrar items por región y monto
    filtered = []
    for item in items:
        if regions:
            item_region = item.get("region", "")
            # Comparar por número de región en el nombre (ej. "Los Lagos" ≈ región 10)
            region_match = any(
                r in item_region or item_region in r
                for r in regions
            )
            # Fallback: comparar código numérico de región (campo "region" en institucion)
            if not region_match and isinstance(item.get("raw_data"), dict):
                region_code = str(item["raw_data"].get("institucion", {}).get("region", ""))
                region_match = region_code in regions
            if not region_match:
                continue

        monto = item.get("monto_clp") or 0
        if monto < min_clp:
            continue
        if max_clp and monto > max_clp:
            continue

        filtered.append(item)

    created = 0
    for item in filtered:
        # Skip si ya existe oportunidad para este usuario + codigo
        exists = (
            db.query(UserOpportunity)
            .filter_by(user_id=user_id, mp_codigo=item["codigo"])
            .first()
        )
        if exists:
            continue

        scoring = await score_opportunity(config.system_prompt, item)
        score = int(scoring.get("score", 0))

        if score < min_score:
            continue

        opp = UserOpportunity(
            user_id=user_id,
            mp_codigo=item["codigo"],
            score=score,
            viabilidad=scoring.get("viabilidad", "baja"),
            accion=scoring.get("accion", "ignorar"),
            resumen=(scoring.get("resumen", "") or "")[:2000],
            justificacion=(scoring.get("justificacion", "") or "")[:2000],
            riesgo=(scoring.get("riesgo", "") or "")[:500],
            precio_sugerido_clp=scoring.get("precio_sugerido_clp"),
        )
        db.add(opp)
        created += 1

        # Pequeña pausa para no saturar OpenAI
        await asyncio.sleep(0.3)

    db.commit()

    # Actualizar last_run_at
    config.last_run_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Usuario %s: %d nuevas oportunidades", user_id, created)
    return created
