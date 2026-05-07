"""Runtime configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[3]
_BACKEND_ROOT = _HERE.parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_REPO_ROOT / ".env"),
            str(_BACKEND_ROOT / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HappyRobot Inbound Carrier API"
    environment: str = "dev"

    api_key: str = "dev-api-key-change-me"
    fmcsa_api_key: str = ""

    database_url: str = "sqlite:///./data/app.db"

    cors_origins: str = "*"

    negotiation_floor_pct: float = 0.92
    negotiation_ceiling_pct: float = 1.10
    negotiation_max_rounds: int = 3

    fmcsa_base_url: str = "https://mobile.fmcsa.dot.gov/qc/services"
    fmcsa_cache_ttl_seconds: int = 3600

    rate_limit_verify: str = "30/minute"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
