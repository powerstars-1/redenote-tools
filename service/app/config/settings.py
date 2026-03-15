from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REDNOTE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RedNote Tools Service"
    app_env: str = "dev"
    log_level: str = "INFO"
    upstream_timeout_seconds: float = 15.0
    max_page_count: int = 10
    spider_base_url: str = "https://edith.xiaohongshu.com"
    spider_node_modules_dir: Path | None = Field(default=None)
    database_path: Path | None = Field(default=None)
    default_sync_target: str = "openclaw_bitable"
    default_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    @property
    def resolved_node_modules_dir(self) -> Path:
        if self.spider_node_modules_dir is not None:
            return self.spider_node_modules_dir
        return Path(__file__).resolve().parents[2] / "node_modules"

    @property
    def resolved_database_path(self) -> Path:
        if self.database_path is not None:
            return self.database_path
        return Path(__file__).resolve().parents[3] / "data" / "app.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
