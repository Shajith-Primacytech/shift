from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "shift-api"
    version: str = "0.2.0"
    mode: Literal["storage"] = "storage"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Process health only. Storage initializes during startup; no AI integration."""
    return HealthResponse()


@router.get("/ready", response_model=HealthResponse)
def ready(request: Request) -> HealthResponse:
    """Readiness probes PostgreSQL; failure uses the shared redacted 503 handler."""
    if request.app.state.settings.storage_backend == "postgres":
        with request.app.state.storage.connection() as conn:
            conn.execute("SELECT 1")
    return HealthResponse()
