"""
Generador de system prompts con GPT-4o-mini.
El usuario describe su empresa → la IA genera un prompt optimizado
para el scoring de Compras Ágiles de Mercado Público.
"""
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


GENERATOR_SYSTEM = """Eres un experto en licitaciones públicas chilenas (Mercado Público, Chile Compra).
Tu tarea es generar un "system prompt" óptimo para un agente de IA que analiza Compras Ágiles.

El system prompt que generes será usado para que otro agente evalúe cada compra ágil y asigne:
- score 0-100 (relevancia para la empresa)
- viabilidad: alta | media | baja
- accion: cotizar | investigar | ignorar
- resumen, justificacion, riesgo, precio_sugerido_clp

REGLAS del prompt que debes generar:
1. Describe las capacidades reales de la empresa de manera concreta
2. Lista qué rubros SÍ aplican (con rangos de montos si es posible)
3. Lista qué rubros NO aplican (descartar automáticamente)
4. Define criterios claros de score:
   - 80-100: match directo con capacidades core
   - 60-79: posible con adaptación
   - 40-59: dudoso
   - 0-39: no aplica
5. Incluye instrucción de responder SIEMPRE en JSON puro (sin markdown)
6. El prompt debe ser específico, no genérico

Responde SOLO con el system prompt listo para usar, sin explicaciones ni markdown."""


async def generate_system_prompt(
    business_description: str,
    company_name: Optional[str] = None,
    extra_context: Optional[str] = None,
) -> tuple[str, int]:
    """
    Genera un system prompt optimizado para scoring de MP.
    Retorna (prompt_text, tokens_used).
    """
    client = _get_client()

    company_info = f"Empresa: {company_name}\n" if company_name else ""
    extra = f"\nContexto adicional: {extra_context}" if extra_context else ""

    user_message = (
        f"{company_info}"
        f"Descripción del negocio:\n{business_description}"
        f"{extra}\n\n"
        "Genera el system prompt optimizado para analizar Compras Ágiles de Mercado Público Chile."
    )

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": GENERATOR_SYSTEM},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1500,
    )

    prompt = response.choices[0].message.content.strip()
    tokens = response.usage.total_tokens if response.usage else 0

    return prompt, tokens


async def score_opportunity(
    system_prompt: str,
    item_data: dict,
) -> dict:
    """
    Usa GPT-4o-mini con el system prompt del usuario para analizar una Compra Ágil.
    Retorna el dict con score, viabilidad, accion, etc.
    """
    client = _get_client()

    monto = item_data.get("monto_clp")
    monto_str = f"${int(monto):,} CLP".replace(",", ".") if monto else "No informado"

    user_prompt = (
        f"Analiza esta Compra Ágil y devuelve SOLO JSON:\n\n"
        f"CÓDIGO: {item_data.get('codigo', '')}\n"
        f"NOMBRE: {item_data.get('nombre', '')}\n"
        f"ORGANISMO: {item_data.get('organismo', '')}\n"
        f"UNIDAD: {item_data.get('unidad_compra', '')}\n"
        f"REGIÓN: {item_data.get('region', '')}\n"
        f"MONTO: {monto_str}\n"
        f"CIERRE: {item_data.get('fecha_cierre', 'No disponible')}\n\n"
        "JSON (sin markdown, sin texto extra):\n"
        "{\n"
        '  "score": <0-100>,\n'
        '  "viabilidad": "alta|media|baja",\n'
        '  "resumen": "<máx 2 líneas>",\n'
        '  "justificacion": "<máx 3 líneas>",\n'
        '  "riesgo": "<1 línea>",\n'
        '  "accion": "cotizar|investigar|ignorar",\n'
        '  "precio_sugerido_clp": <número o null>\n'
        "}"
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI error para %s: %s", item_data.get("codigo"), e)
        return _error_scoring(str(e))

    import json, re
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{[\s\S]*\}', clean)
        return json.loads(match.group(0) if match else clean)
    except Exception as e:
        return _error_scoring(f"Parse error: {raw[:200]}")


def _error_scoring(msg: str) -> dict:
    return {
        "score": 0,
        "viabilidad": "baja",
        "resumen": "Error al procesar",
        "justificacion": msg[:300],
        "riesgo": "Error de procesamiento",
        "accion": "ignorar",
        "precio_sugerido_clp": None,
    }
