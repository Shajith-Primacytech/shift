"""Isolated browser test server; never writes the user's development database."""

import os
from tempfile import TemporaryDirectory

import uvicorn

from app.api.speech import speech_service
from tests.speech_fakes import FakeSpeech
from app.api.capture import capture_service
from app.capture.service import CaptureService
from tests.capture_fakes import provider as capture_provider
from app.api.troubleshooting import rag_service
from app.config import Settings
from app.main import create_app
from app.rag.service import RagService
from app.storage.database import connect, initialize
from app.storage.security import create_user
from tests.rag_fakes import mocked_provider, test_retriever

with TemporaryDirectory(prefix="shift-e2e-") as directory:
    settings = Settings(
        environment="test", database_path=directory + "/test.sqlite3", _env_file=None
    )
    initialize(settings.database_path)
    with connect(settings.database_path) as db:
        for username, name, role in [
            ("tech", "Arun Patel", "technician"),
            ("super", "Maya Chen", "supervisor"),
            ("voice-tech", "Voice Test Technician", "technician"),
        ]:
            create_user(db, username, name, role, "browser-test-only-password")
    app = create_app(settings)
    if os.environ.get("SHIFT_E2E_LIVE") != "1":
        app.dependency_overrides[speech_service] = FakeSpeech
        app.dependency_overrides[capture_service] = lambda: CaptureService(
            capture_provider()
        )
        app.dependency_overrides[rag_service] = lambda: RagService(
            settings.database_path, mocked_provider(), test_retriever
        )
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("SHIFT_E2E_API_PORT", "8000")))
