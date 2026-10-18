"""Authenticated presentation metadata. This endpoint never calls inference."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.storage import current_user
from app.capture.service import MODEL, PROVIDER
from app.config import AMDSettings

router = APIRouter()


@router.get("/ai/configuration")
def ai_configuration(user: Annotated[dict, Depends(current_user, scope="function")]):
    model = None
    configured = False
    try:
        config = AMDSettings()
        key = config.api_key.get_secret_value().strip()
        # Guard against an accidentally pasted credential in the model setting.
        if not key or key not in config.model:
            model = config.model
        configured = bool(key and model)
    except ValidationError:
        pass
    return {
        "capture": {
            "provider": PROVIDER,
            "requested_model": MODEL,
            "developer": "Google",
            "status": "configured" if configured else "unavailable",
        },
        "troubleshooting": {
            "provider": PROVIDER,
            "requested_model": model,
            "status": "configured" if configured else "unavailable",
        },
    }
