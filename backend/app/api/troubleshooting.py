import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.storage import current_user, database
from app.storage.backend import is_postgres
from starlette.concurrency import run_in_threadpool
from app.rag.service import Question, RagFailure, RagService

router = APIRouter()


def rag_service(request: Request):
    if not hasattr(request.app.state, "rag_service"):
        request.app.state.rag_service = RagService(
            request.app.state.storage
            if request.app.state.settings.storage_backend == "postgres"
            else request.app.state.settings.database_path
        )
    return request.app.state.rag_service


@router.post("/troubleshoot")
async def troubleshoot(
    body: Question,
    request: Request,
    user=Depends(current_user, scope="function"),
    db=Depends(database, scope="function"),
    service=Depends(rag_service),
):
    exists = (
        (await run_in_threadpool(db.machine_exists, body.machine_id))
        if is_postgres(db)
        else db.execute(
            "SELECT 1 FROM machines WHERE id=?", (body.machine_id,)
        ).fetchone()
    )
    if not exists:
        raise HTTPException(404, "Machine not found")
    if not hasattr(request.app.state, "rag_request_lock"):
        request.app.state.rag_request_lock = asyncio.Lock()
    lock = request.app.state.rag_request_lock
    if lock.locked():
        raise HTTPException(
            429, "Another troubleshooting request is running. Please retry shortly."
        )
    async with lock:
        try:
            result = await service.answer(body)
        except RagFailure as e:
            return JSONResponse(
                {"detail": str(e), "execution": e.execution}, status_code=e.status
            )
        # Sessions can expire or be logged out while a slow provider request runs.
        await run_in_threadpool(current_user, request, db)
        return result
