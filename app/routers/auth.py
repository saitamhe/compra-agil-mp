"""
Router de autenticación: registro, login, refresh, logout.
"""
from datetime import timezone
from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token, generate_refresh_token, hash_password,
    hash_refresh_token, refresh_token_expires, verify_password,
)
from app.database import RefreshToken, User, UserConfig, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    company_name: Optional[str] = None
    rut: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: Optional[str]


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        company_name=body.company_name,
        rut=body.rut,
    )
    db.add(user)
    db.flush()

    # Crear config vacía por defecto
    config = UserConfig(
        user_id=user.id,
        regions=["10", "11", "9"],
        system_prompt="",
        min_score=60,
    )
    db.add(config)
    db.commit()
    db.refresh(user)

    return _issue_tokens(user, db)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")
    return _issue_tokens(user, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    rt = (
        db.query(RefreshToken)
        .filter_by(token_hash=token_hash, revoked=False)
        .first()
    )
    if not rt:
        raise HTTPException(status_code=401, detail="Refresh token inválido o revocado")

    from datetime import datetime
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expirado")

    # Revocar el token actual y emitir nuevos
    rt.revoked = True
    db.commit()

    user = db.query(User).filter_by(id=rt.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no válido")

    return _issue_tokens(user, db)


@router.post("/logout", status_code=204)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    rt = db.query(RefreshToken).filter_by(token_hash=token_hash).first()
    if rt:
        rt.revoked = True
        db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue_tokens(user: User, db: Session) -> TokenResponse:
    access = create_access_token(str(user.id), user.email)
    raw_refresh, hashed_refresh = generate_refresh_token()

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=refresh_token_expires(),
    )
    db.add(rt)
    db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        user_id=str(user.id),
        email=user.email,
        name=user.name,
    )
