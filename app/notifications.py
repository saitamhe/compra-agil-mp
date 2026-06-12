"""
Notificaciones por Telegram y webhook para cada usuario.
"""
import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.database import MpItem, NotificationLog, UserConfig, UserOpportunity, get_session

logger = logging.getLogger(__name__)
settings = get_settings()

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def send_pending_notifications():
    """Envía notificaciones Telegram para oportunidades no notificadas."""
    db = get_session()
    try:
        # Obtener oportunidades pendientes de notificación con telegram habilitado
        rows = (
            db.query(UserOpportunity, MpItem, UserConfig)
            .join(MpItem, UserOpportunity.mp_codigo == MpItem.codigo)
            .join(UserConfig, UserOpportunity.user_id == UserConfig.user_id)
            .filter(
                UserOpportunity.notificado_telegram == False,
                UserConfig.telegram_enabled == True,
                UserConfig.telegram_chat_id.isnot(None),
                UserOpportunity.score >= UserConfig.min_score,
            )
            .all()
        )

        logger.info("Pendientes de notificación Telegram: %d", len(rows))

        async with httpx.AsyncClient(timeout=15) as client:
            for opp, item, config in rows:
                success = await _send_telegram(client, config.telegram_chat_id, opp, item)
                status = "sent" if success else "failed"

                opp.notificado_telegram = success
                db.add(NotificationLog(
                    user_id=opp.user_id,
                    opportunity_id=opp.id,
                    channel="telegram",
                    status=status,
                ))
                db.commit()

    finally:
        db.close()


async def _send_telegram(
    client: httpx.AsyncClient,
    chat_id: str,
    opp: UserOpportunity,
    item: MpItem,
) -> bool:
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN no configurado")
        return False

    monto_str = f"${int(item.monto_clp):,}".replace(",", ".") + " CLP" if item.monto_clp else "No informado"
    accion_emoji = {"cotizar": "🎯", "investigar": "🔍", "ignorar": "❌"}.get(opp.accion or "", "📋")
    viab_emoji = {"alta": "✅", "media": "⚠️", "baja": "🔴"}.get(opp.viabilidad or "", "")

    text = (
        f"{accion_emoji} *Score {opp.score}/100 — {(opp.accion or '').upper()}*\n\n"
        f"📋 *{item.nombre or ''}*\n"
        f"🏛 {item.organismo or ''}\n"
        f"📍 {item.region or ''}\n"
        f"💰 {monto_str}\n"
        f"📅 Cierre: {item.fecha_cierre or 'No disponible'}\n\n"
        f"{viab_emoji} *{(opp.viabilidad or '').upper()}* — {opp.resumen or ''}\n"
        f"💡 {opp.justificacion or ''}\n"
        f"⚠️ {opp.riesgo or ''}\n\n"
        f"🔗 [Ver en Mercado Público]({item.url_mp or ''})"
    )

    url = TELEGRAM_API.format(token=settings.telegram_bot_token)
    try:
        resp = await client.post(url, json={
            "chat_id": chat_id,
            "text": text[:4096],
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        })
        if resp.status_code == 200:
            return True
        logger.warning("Telegram error %d para chat %s: %s", resp.status_code, chat_id, resp.text[:200])
        return False
    except Exception as e:
        logger.error("Telegram excepción para chat %s: %s", chat_id, e)
        return False
