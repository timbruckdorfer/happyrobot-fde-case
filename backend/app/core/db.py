"""SQLModel engine and session helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from .settings import get_settings


def _ensure_sqlite_dir(database_url: str) -> None:
    if database_url.startswith("sqlite:///"):
        path = Path(database_url.replace("sqlite:///", "", 1))
        if not path.is_absolute():
            path = Path.cwd() / path
        path.parent.mkdir(parents=True, exist_ok=True)


_settings = get_settings()
_ensure_sqlite_dir(_settings.database_url)

connect_args: dict[str, object] = {}
if _settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    _settings.database_url,
    echo=os.getenv("SQL_ECHO") == "1",
    connect_args=connect_args,
)


def init_db() -> None:
    """Create tables and seed if needed (idempotent)."""
    from app.models.call import Call  # noqa: F401  (register tables)
    from app.models.load import Load  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
