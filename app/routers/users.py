"""
Router de usuarios: perfil, configuración y generador de prompt con IA.
"""
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import get_current_user_id, hash_password, verify_password
from app.database import User, UserConfig, get_db
from app.prompt_ai import generate_system_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Usuarios"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ProfileResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    company_name: Optional[str]
    rut: Optional[str]
    plan: str
    email_verified: bool

    model_config = {"from_attributes": True}


class ConfigResponse(BaseModel):
    business_description: Optional[str]
    system_prompt: str
    regions: list[str]
    min_amount_clp: int
    max_amount_clp: Optional[int]
    min_score: int
    keywords_include: list[str]
    keywords_exclude: list[str]
    telegram_chat_id: Optional[str]
    telegram_enabled: bool
    email_notifications: bool
    webhook_url: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class UpdateConfigRequest(BaseModel):
    business_description: Optional[str] = None
    system_prompt: Optional[str] = None
    regions: Optional[list[str]] = None
    min_amount_clp: Optional[int] = None
    max_amount_clp: Optional[int] = None
    min_score: Optional[int] = None
    keywords_include: Optional[list[str]] = None
    keywords_exclude: Optional[list[str]] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    webhook_url: Optional[str] = None
    is_active: Optional[bool] = None


class GeneratePromptRequest(BaseModel):
    business_description: str
    company_name: Optional[str] = None
    extra_context: Optional[str] = None


class GeneratePromptResponse(BaseModel):
    system_prompt: str
    tokens_used: int


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/me", response_model=ProfileResponse)
def get_profile(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    return ProfileResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        company_name=user.company_name,
        rut=user.rut,
        plan=user.plan,
        email_verified=user.email_verified,
    )


@router.get("/me/config", response_model=ConfigResponse)
def get_config(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    config = _get_config_or_create(user_id, db)
    return config


@router.put("/me/config", response_model=ConfigResponse)
def update_config(
    body: UpdateConfigRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    config = _get_config_or_create(user_id, db)

    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


@router.post("/me/generate-prompt", response_model=GeneratePromptResponse)
async def generate_prompt(
    body: GeneratePromptRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Llama a GPT-4o-mini para generar un system prompt optimizado
    basado en la descripción del negocio del usuario.
    Guarda automáticamente el prompt generado en la config del usuario.
    """
    _get_user_or_404(user_id, db)

    try:
        prompt, tokens = await generate_system_prompt(
            business_description=body.business_description,
            company_name=body.company_name,
            extra_context=body.extra_context,
        )
    except Exception as e:
        logger.exception("Error generando prompt: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al generar prompt: {e}")

    # Guardar en config del usuario
    config = _get_config_or_create(user_id, db)
    config.business_description = body.business_description
    config.system_prompt = prompt
    db.commit()

    return GeneratePromptResponse(system_prompt=prompt, tokens_used=tokens)


class RefreshResponse(BaseModel):
    message: str
    background: bool = True


async def _bg_score(user_id: str):
    """Scoring en background con sesión DB propia."""
    from app.database import UserConfig, get_session
    from app.mp_api import score_user_from_db
    db = get_session()
    try:
        config = db.query(UserConfig).filter_by(user_id=user_id).first()
        if config and config.system_prompt:
            await score_user_from_db(config, db, max_items=50)
    except Exception as e:
        logger.exception("Error en scoring background para %s: %s", user_id, e)
    finally:
        db.close()


@router.post("/me/refresh", response_model=RefreshResponse)
async def refresh_opportunities(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Lanza el análisis IA en background y retorna inmediatamente.
    El frontend hace polling a /opportunities/stats para ver los resultados.
    """
    config = _get_config_or_create(user_id, db)
    if not config.system_prompt:
        raise HTTPException(
            status_code=400,
            detail="Debes configurar tu perfil de empresa antes de actualizar. "
                   "Ve a Configuración y genera o escribe tu prompt.",
        )

    background_tasks.add_task(_bg_score, user_id)
    return RefreshResponse(
        message="⏳ Análisis iniciado. Los resultados aparecerán en unos segundos...",
        background=True,
    )


@router.post("/me/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres")
    user.password_hash = hash_password(body.new_password)
    db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_or_404(user_id: str, db: Session) -> User:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def _get_config_or_create(user_id: str, db: Session) -> UserConfig:
    config = db.query(UserConfig).filter_by(user_id=user_id).first()
    if not config:
        config = UserConfig(
            user_id=user_id,
            regions=["10", "11", "9"],
            system_prompt="",
            min_score=60,
            keywords_include=[],
            keywords_exclude=[],
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config
