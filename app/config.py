from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    # General
    app_env: str = "production"
    log_level: str = "INFO"

    # Database
    db_path: str = "./data/compra_agil.db"

    # Directories
    downloads_dir: str = "./data/downloads"
    logs_dir: str = "./logs"

    # Scraper
    scraper_base_url: str = "https://datos-abiertos.chilecompra.cl/descargas/compra-agil"
    scraper_headless: bool = True
    scraper_timeout_ms: int = 60000
    scraper_download_wait_s: int = 30

    # Scheduler
    scheduler_interval_hours: int = 2

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 2
    api_secret_key: str = "CHANGE_ME_IN_PRODUCTION"

    # Pagination
    default_page_size: int = 100
    max_page_size: int = 1000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    def ensure_dirs(self):
        Path(self.downloads_dir).mkdir(parents=True, exist_ok=True)
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
