from __future__ import annotations

import logging
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from starlette.responses import Response

from app.api.auth import router as auth_router
from app.api.credentials import router as credential_router
from app.api.detection import router as detection_router
from app.api.ingestion import router as ingestion_router
from app.api.graph import router as graph_router
from app.api.incidents import router as incidents_router
from app.api.investigation import router as investigation_router
from app.api.ml import router as ml_router
from app.api.processing import router as processing_router
from app.api.response import router as response_router
from app.api.risk import router as risk_router
from app.api.sdk import router as sdk_router
from app.api.threat_intel import router as threat_intel_router
from app.api.websites import router as website_router
from app.config.settings import settings
from app.database.database import check_database_connection, init_db
from app.database import database
from app.database.models import Website
from app.database.repositories import normalize_website_address


def configure_logging() -> None:
    """Configure application logging without exposing sensitive data."""

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="WebIntelX AI project foundation API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def is_active_website_origin(origin: str) -> bool:
    try:
        normalized_origin = normalize_website_address(origin)[1]
    except ValueError:
        return False
    with database.SessionLocal() as db:
        return db.execute(
            select(Website.id).where(
                Website.origin == normalized_origin,
                Website.status == "active",
            )
        ).first() is not None


@app.middleware("http")
async def customer_website_ingestion_cors(request, call_next):
    if request.url.path != "/api/ingest/events":
        return await call_next(request)

    origin = request.headers.get("origin")
    allowed = bool(origin and is_active_website_origin(origin))
    if request.method == "OPTIONS" and allowed:
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "content-type",
                "Access-Control-Max-Age": "600",
                "Vary": "Origin",
            },
        )

    response = await call_next(request)
    if allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response

api_router = APIRouter(prefix="/api/v1")
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(website_router)
app.include_router(credential_router)
app.include_router(ingestion_router)
app.include_router(investigation_router)
app.include_router(processing_router)
app.include_router(detection_router)
app.include_router(ml_router)
app.include_router(sdk_router)
app.include_router(graph_router)
app.include_router(incidents_router)
app.include_router(risk_router)
app.include_router(response_router)
app.include_router(threat_intel_router)


@app.on_event("startup")
def startup() -> None:
    """Initialize the SQLite metadata when the API starts."""

    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    """Return the service health status for monitoring and tests."""

    database_ok = check_database_connection()
    status = "healthy" if database_ok else "degraded"
    database_status = "connected" if database_ok else "unavailable"

    return {
        "status": status,
        "application": settings.app_name,
        "environment": settings.app_env,
        "database": database_status,
    }
