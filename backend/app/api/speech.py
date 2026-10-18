"""Authenticated local-only speech endpoint. Audio is not inserted into knowledge."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.storage import current_user, database
from app.speech.constants import MAX_BYTES
from app.speech.service import LocalSpeech, SpeechFailure

router = APIRouter()


def speech_service(request: Request):
    return LocalSpeech(request.app.state.settings.speech_model_path)


@router.get("/capture/voice/status")
def voice_status(
    user: Annotated[dict, Depends(current_user, scope="function")],
    service: Annotated[LocalSpeech, Depends(speech_service)],
):
    return service.status()


@router.post("/capture/transcribe")
async def transcribe(
    request: Request,
    file: Annotated[UploadFile, File()],
    user: Annotated[dict, Depends(current_user, scope="function")],
    db: Annotated[object, Depends(database, scope="function")],
    service: Annotated[LocalSpeech, Depends(speech_service)],
):
    if not (file.content_type or "").startswith("audio/"):
        raise HTTPException(422, "Choose an audio recording")
    data = await file.read(MAX_BYTES + 1)
    await file.close()
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(422, "Recording must be nonempty and at most 10 MB")
    if not hasattr(request.app.state, "speech_request_lock"):
        request.app.state.speech_request_lock = asyncio.Lock()
    lock = request.app.state.speech_request_lock
    if lock.locked():
        raise HTTPException(
            429,
            "Local transcription is busy. Wait for the current recording to finish; manual capture is available.",
        )
    async with lock:
        try:
            result = await run_in_threadpool(service.transcribe, data)
        except SpeechFailure as exc:
            raise HTTPException(exc.status, str(exc)) from None
        await run_in_threadpool(current_user, request, db)
        return result
