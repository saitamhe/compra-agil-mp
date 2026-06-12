"""
Base de datos PostgreSQL — Multi-tenant SaaS schema.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Index, Integer,
    BigInteger, String, Text, UniqueConstraint,
    create_engine, text, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Modelos ORM
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name         = Column(String(255))
    company_name = Column(String(255))
    rut          = Column(String(20))
    plan         = Column(String(20), default="free")
    is_active    = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    config        = relationship("UserConfig", back_populates="user", uselist=False,
                                 cascade="all, delete-orphan")
    opportunities = relationship("UserOpportunity", back_populates="user",
                                 cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user",
                                  cascade="all, delete-orphan")


class UserConfig(Base):
    __tablename__ = "user_configs"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id              = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                                  unique=True, nullable=False)
    business_description = Column(Text)
    system_prompt        = Column(Text, nullable=False, default="")
    regions              = Column(ARRAY(Text), default=list)
    min_amount_clp       = Column(BigInteger, default=0)
    max_amount_clp       = Column(BigInteger)
    min_score            = Column(Integer, default=60)
    keywords_include     = Column(ARRAY(Text), default=list)
    keywords_exclude     = Column(ARRAY(Text), default=list)
    telegram_chat_id     = Column(String(50))
    telegram_enabled     = Column(Boolean, default=False)
    email_notifications  = Column(Boolean, default=True)
    webhook_url          = Column(Text)
    is_active            = Column(Boolean, default=True)
    last_run_at          = Column(DateTime(timezone=True))
    created_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                  onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="config")


class MpItem(Base):
    __tablename__ = "mp_items"

    codigo        = Column(String(50), primary_key=True)
    nombre        = Column(Text)
    organismo     = Column(Text)
    unidad_compra = Column(Text)
    region        = Column(Text)
    monto_clp     = Column(BigInteger)
    fecha_cierre  = Column(Date)
    estado        = Column(String(50), default="publicada")
    url_mp        = Column(Text)
    raw_data      = Column(JSONB)
    fetched_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    opportunities = relationship("UserOpportunity", back_populates="mp_item",
                                 cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_mp_items_fecha", "fecha_cierre"),
        Index("idx_mp_items_monto", "monto_clp"),
        Index("idx_mp_items_region", "region"),
    )


class UserOpportunity(Base):
    __tablename__ = "user_opportunities"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                                 nullable=False)
    mp_codigo           = Column(String(50), ForeignKey("mp_items.codigo"), nullable=False)
    score               = Column(Integer)
    viabilidad          = Column(String(10))
    accion              = Column(String(20))
    resumen             = Column(Text)
    justificacion       = Column(Text)
    riesgo              = Column(Text)
    precio_sugerido_clp = Column(BigInteger)
    estado_seguimiento  = Column(String(30), default="pendiente")
    notificado_telegram = Column(Boolean, default=False)
    notificado_email    = Column(Boolean, default=False)
    user_notes          = Column(Text)
    scored_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at          = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                 onupdate=lambda: datetime.now(timezone.utc))

    user    = relationship("User", back_populates="opportunities")
    mp_item = relationship("MpItem", back_populates="opportunities")

    __table_args__ = (
        UniqueConstraint("user_id", "mp_codigo", name="uq_user_opportunity"),
        Index("idx_uo_user_id", "user_id"),
        Index("idx_uo_score", "score"),
    )


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("user_opportunities.id"))
    channel        = Column(String(20))
    status         = Column(String(20))
    sent_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    error_message  = Column(Text)


class RunLog(Base):
    __tablename__ = "run_log"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    started_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at          = Column(DateTime(timezone=True))
    items_fetched        = Column(Integer, default=0)
    items_new            = Column(Integer, default=0)
    users_processed      = Column(Integer, default=0)
    opportunities_created = Column(Integer, default=0)
    status               = Column(String(20), default="running")
    error_msg            = Column(Text)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_rt_user_id", "user_id"),
        Index("idx_rt_token", "token_hash"),
    )


# ---------------------------------------------------------------------------
# Engine y sesión
# ---------------------------------------------------------------------------

_engine = None
_SessionLocal = None


def get_engine():
    return create_engine(
        settings.db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )


def init_db():
    global _engine, _SessionLocal
    _engine = get_engine()
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    logger.info("Base de datos PostgreSQL inicializada")


def get_session() -> Session:
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Compatibilidad legacy — ScraperRun para el router /admin/runs
# ---------------------------------------------------------------------------

class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    started_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at     = Column(DateTime(timezone=True))
    status          = Column(String(20), default="running")
    regions_scraped = Column(Integer, default=0)
    files_downloaded = Column(Integer, default=0)
    rows_inserted   = Column(Integer, default=0)
    rows_skipped    = Column(Integer, default=0)
    error_msg       = Column(Text)
