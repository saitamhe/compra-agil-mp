from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    # General
    app_env: str = "production"
    log_level: str = "INFO"
    app_name: str = "CompraÁgil SaaS"
    frontend_url: str = "https://mp.heforge.cl"

    # Database — PostgreSQL
    db_host: str = "postgres"          # nombre del servicio docker
    db_port: int = 5432
    db_user: str = "saas_mp"
    db_password: str = "SaasMP2025!SecurePass"
    db_name: str = "mp_saas"

    # Directories (para logs y downloads CSV legacy)
    downloads_dir: str = "./data/downloads"
    logs_dir: str = "./logs"

    # Mercado Público API
    mp_ticket: str = "B62A4372-14A4-4C86-8B06-FFF908CE0FBD"
    mp_api_base: str = "https://api2.mercadopublico.cl/v2/compra-agil"
    mp_regions_default: str = "10,11,9"
    mp_page_size: int = 50

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Auth JWT
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION_RANDOM_256BIT"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "mercadopublcio2025"   # legacy admin key

    # Scheduler
    scheduler_interval_hours: int = 2

    # Pagination
    default_page_size: int = 50
    max_page_size: int = 200

    # Telegram Bot (admin / fallback)
    telegram_bot_token: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def db_url_async(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def ensure_dirs(self):
        Path(self.downloads_dir).mkdir(parents=True, exist_ok=True)
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
