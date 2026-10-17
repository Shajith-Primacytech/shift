from typing import Literal

from fastapi import APIRouter
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
