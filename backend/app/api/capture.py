"""Authenticated optional capture structuring; never creates approved knowledge."""

import asyncio
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.storage import current_user, database
from app.storage.backend import is_postgres
from starlette.concurrency import run_in_threadpool
from app.capture.service import MODEL, PROVIDER, CaptureService
from app.storage.capture_schema import SubmissionFields
from app.storage.security import now

router = APIRouter()


def capture_service():
    return CaptureService()


@router.post("/capture/structure")
async def structure_capture(
    body: SubmissionFields,
    request: Request,
    user: Annotated[dict, Depends(current_user, scope="function")],
    db: Annotated[object, Depends(database, scope="function")],
    service: Annotated[CaptureService, Depends(capture_service)],
):
    exists = (
        (await run_in_threadpool(db.machine_exists, body.machineId))
        if is_postgres(db)
        else db.execute(
            "SELECT 1 FROM machines WHERE id=?", (body.machineId,)
        ).fetchone()
    )
    if not exists:
        raise HTTPException(422, "Unknown machine")
    if not hasattr(request.app.state, "capture_request_lock"):
        request.app.state.capture_request_lock = asyncio.Lock()
    lock = request.app.state.capture_request_lock
    if lock.locked():
        raise HTTPException(
            429, "Another structuring request is running. Manual capture is available."
        )
    async with lock:
        if is_postgres(db):
            run_id = await run_in_threadpool(db.capture_receipt, body, user)
            result, status = await service.structure(body)
            await run_in_threadpool(db.capture_result, run_id, result)
            await run_in_threadpool(current_user, request, db)
            return JSONResponse({"runId": run_id, **result}, status_code=status)
        db.execute("BEGIN IMMEDIATE")
        cutoff = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
        if db.execute(
            "SELECT 1 FROM capture_ai_runs WHERE owner_id=? AND created_at>?",
            (user["id"], cutoff),
        ).fetchone():
            raise HTTPException(
                429, "Wait 30 seconds between AI requests. Manual capture is available."
            )
        run_id = secrets.token_hex(16)
        timestamp = now()
        # Commit the receipt before outbound inference. No write transaction spans the call.
        db.execute(
            "INSERT INTO capture_ai_runs (id,owner_id,original_submission,execution,created_at) VALUES (?,?,?,?,?)",
            (
                run_id,
                user["id"],
                body.model_dump_json(),
                json.dumps(
                    {
                        "provider": PROVIDER,
                        "requested_model": MODEL,
                        "model_id": MODEL,
                        "requested_at": timestamp,
                        "latency_ms": None,
                        "usage": None,
                        "status": "interrupted",
                        "http_status": None,
                        "error_code": "interrupted",
                    }
                ),
                timestamp,
            ),
        )
        db.commit()
        result, status = await service.structure(body)
        db.execute(
            "UPDATE capture_ai_runs SET proposal=?,execution=? WHERE id=?",
            (
                json.dumps(result.get("proposal")) if "proposal" in result else None,
                json.dumps(result["execution"]),
                run_id,
            ),
        )
        db.commit()
        # As with troubleshooting, recheck the session after slow external work.
        current_user(request, db)
        return JSONResponse({"runId": run_id, **result}, status_code=status)
