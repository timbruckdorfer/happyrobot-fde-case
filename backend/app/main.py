"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import calls as calls_api
from app.api import loads as loads_api
from app.api import metrics as metrics_api
from app.api import negotiate as negotiate_api
from app.api import verify as verify_api
from app.core.db import init_db
from app.core.limiter import limiter
from app.core.logging import RequestIDMiddleware, configure_logging
from app.core.settings import get_settings
from app.services.seeder import seed_loads

configure_logging()
log = structlog.get_logger("startup")
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    inserted = seed_loads(force=False)
    log.info("startup_complete", seeded_loads=inserted, env=settings.environment)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],
    allow_credentials=False,
)
app.add_middleware(RequestIDMiddleware)


@app.get("/healthz", tags=["health"])
def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": app.version})


app.include_router(verify_api.router, prefix="/api")
app.include_router(loads_api.router, prefix="/api")
app.include_router(negotiate_api.router, prefix="/api")
app.include_router(calls_api.router, prefix="/api")
app.include_router(metrics_api.router, prefix="/api")


_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.exists():
    assets_dir = _STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str = ""):
        if full_path.startswith(("api/", "healthz", "assets/")):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index_path = _STATIC_DIR / "index.html"
        return FileResponse(index_path)
else:
    @app.get("/", include_in_schema=False)
    def root() -> JSONResponse:
        return JSONResponse(
            {
                "service": settings.app_name,
                "docs": "/api/docs",
                "health": "/healthz",
            }
        )
