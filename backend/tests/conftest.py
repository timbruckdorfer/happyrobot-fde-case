"""Shared fixtures: in-memory SQLite + test client with API key."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("FMCSA_API_KEY", "test-fmcsa")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/hr_fde_test.db")
os.environ.setdefault("CORS_ORIGINS", "*")


@pytest.fixture(scope="session", autouse=True)
def _prepare_db() -> Iterator[None]:
    db_path = os.environ["DATABASE_URL"].replace("sqlite:///", "")
    if os.path.exists(db_path):
        os.remove(db_path)
    yield
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.core.db import init_db
    from app.main import app
    from app.services.seeder import seed_loads

    init_db()
    seed_loads(force=False)

    with TestClient(app) as c:
        c.headers.update({"X-API-Key": os.environ["API_KEY"]})
        yield c
