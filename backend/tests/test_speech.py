import io
import json
import subprocess
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.api.speech import speech_service
from app.speech.constants import MAX_BYTES, MAX_SECONDS, MODEL, PROVIDER
from app.speech.service import ERRORS, LocalSpeech, SpeechFailure
from app.storage.database import connect

from tests.rag_fakes import test_retriever as make_retriever
from tests.speech_fakes import TEXT, FakeSpeech
from tests.test_capture import SOURCE, decision, login
from tests.test_capture import workspace as workspace  # noqa: PLC0414 -- explicit pytest fixture re-export


@pytest.fixture
def engine(tmp_path, monkeypatch):
    service = LocalSpeech(tmp_path)
    monkeypatch.setattr(service, "status", lambda: {"available": True})
    return service


def test_missing_model_is_safe_unavailable(tmp_path):
    service = LocalSpeech(tmp_path)
    assert service.status()["available"] is False
    with pytest.raises(SpeechFailure) as caught:
        service.transcribe(b"opaque audio")
    assert caught.value.code == "unavailable" and caught.value.status == 503


@pytest.mark.parametrize("data", [b"", b"x" * (MAX_BYTES + 1)])
def test_empty_and_oversize_input_rejected_before_worker(engine, data):
    with pytest.raises(SpeechFailure):
        engine.transcribe(data)


def test_worker_is_offline_private_bounded_and_cleaned_up(engine, monkeypatch):
    paths = []
    monkeypatch.setenv("AMD_API_KEY", "private-test-credential")
    monkeypatch.setenv("HF_TOKEN", "private-download-token")

    def worker(args, **kwargs):
        audio, output = Path(args[-3]), Path(args[-1])
        assert audio.read_bytes() == b"private audio"
        paths.append(audio.parent)
        assert kwargs["timeout"] == 60 and kwargs["stdout"] == subprocess.DEVNULL
        assert kwargs["stderr"] == subprocess.DEVNULL
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        assert "AMD_API_KEY" not in kwargs["env"] and "HF_TOKEN" not in kwargs["env"]
        output.write_text(json.dumps({"text": TEXT, "duration_seconds": 3}))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", worker)
    result = engine.transcribe(b"private audio")
    assert (
        result["text"] == TEXT
        and result["provider"] == PROVIDER
        and result["model"] == MODEL
    )
    assert all(not p.exists() for p in paths)


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {"text": ""},
        {"text": "ok", "duration_seconds": 121},
        {"text": "ok", "duration_seconds": float("nan")},
        {"error": ["untrusted"]},
        {"text": "x" * 8001, "duration_seconds": 1},
    ],
)
def test_invalid_worker_result_never_leaks_private_diagnostics(
    engine, monkeypatch, body
):
    def worker(args, **kwargs):
        Path(args[-1]).write_text(
            "private invalid result" if body is None else json.dumps(body)
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", worker)
    with pytest.raises(SpeechFailure) as caught:
        engine.transcribe(b"private audio")
    assert caught.value.code == "transcription_failed"
    assert "private" not in str(caught.value)


@pytest.mark.parametrize(
    "code", ["no_speech", "too_long", "empty_audio", "invalid_audio"]
)
def test_decoder_and_speech_errors_are_explicit(engine, monkeypatch, code):
    def worker(args, **kwargs):
        Path(args[-1]).write_text(json.dumps({"error": code}))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", worker)
    with pytest.raises(SpeechFailure) as caught:
        engine.transcribe(b"audio")
    assert caught.value.code == code and str(caught.value) == ERRORS[code]


def test_timeout_cleanup_without_automatic_retry(engine, monkeypatch):
    calls = []

    def worker(args, **kwargs):
        calls.append(Path(args[-3]).parent)
        raise subprocess.TimeoutExpired("private worker diagnostic", 60)

    monkeypatch.setattr(subprocess, "run", worker)
    with pytest.raises(SpeechFailure) as caught:
        engine.transcribe(b"audio")
    assert caught.value.code == "timeout" and caught.value.status == 504
    assert len(calls) == 1 and not calls[0].exists()
    assert "private" not in str(caught.value)


def wav(seconds):
    output = io.BytesIO()
    with wave.open(output, "wb") as handle:
        handle.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        handle.writeframes(b"\0\0" * int(seconds * 16000))
    return output.getvalue()


@pytest.mark.parametrize(
    "seconds,code",
    [(0.05, "empty_audio"), (1, "no_speech"), (MAX_SECONDS + 1, "too_long")],
)
def test_real_decoder_enforces_duration_and_silence(tmp_path, seconds, code):
    pytest.importorskip("av")
    from app.speech.worker import AudioFailure, decode_bounded

    path = tmp_path / "sample.wav"
    path.write_bytes(wav(seconds))
    with pytest.raises(AudioFailure) as caught:
        decode_bounded(str(path))
    assert str(caught.value) == code


def test_speech_api_auth_csrf_validation_and_no_knowledge_write(workspace):
    client, config = workspace
    client.app.dependency_overrides[speech_service] = FakeSpeech
    files = {"file": ("voice.webm", b"audio", "audio/webm")}
    assert client.get("/api/v1/capture/voice/status").status_code == 401
    assert client.post("/api/v1/capture/transcribe", files=files).status_code == 401
    login(client)
    assert client.get("/api/v1/capture/voice/status").json()["available"] is True
    assert (
        client.post(
            "/api/v1/capture/transcribe", files=files, headers={"X-Shift-Request": ""}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/capture/transcribe",
            files={"file": ("bad.txt", b"data", "text/plain")},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/capture/transcribe",
            files={"file": ("empty.wav", b"", "audio/wav")},
        ).status_code
        == 422
    )
    response = client.post("/api/v1/capture/transcribe", files=files)
    assert response.status_code == 200 and response.json()["text"] == TEXT
    with connect(config.database_path) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM knowledge_records WHERE owner_id IS NOT NULL"
            ).fetchone()[0]
            == 0
        )
        assert db.execute("SELECT count(*) FROM source_documents").fetchone()[0] == 0


def test_failed_speech_retains_manual_capture_and_session_rechecked(workspace):
    client, config = workspace

    class Failed(FakeSpeech):
        def transcribe(self, data):
            raise SpeechFailure("timeout", 504)

    client.app.dependency_overrides[speech_service] = Failed
    login(client)
    response = client.post(
        "/api/v1/capture/transcribe",
        files={"file": ("voice.wav", b"audio", "audio/wav")},
    )
    assert response.status_code == 504 and "timed out" in response.text.lower()
    assert (
        client.post(
            "/api/v1/submissions", data={"metadata": json.dumps(SOURCE)}
        ).status_code
        == 201
    )

    class Revoked(FakeSpeech):
        def transcribe(self, data):
            with connect(config.database_path) as db:
                db.execute("DELETE FROM sessions")
            return super().transcribe(data)

    client.app.dependency_overrides[speech_service] = Revoked
    response = client.post(
        "/api/v1/capture/transcribe",
        files={"file": ("voice.wav", b"audio", "audio/wav")},
    )
    assert response.status_code == 401 and "text" not in response.json()


def test_reviewed_voice_text_structures_then_requires_supervisor_approval(workspace):
    client, config = workspace
    client.app.dependency_overrides[speech_service] = FakeSpeech
    login(client)
    transcript = client.post(
        "/api/v1/capture/transcribe",
        files={"file": ("voice.wav", b"PRIVATE_AUDIO_BYTES", "audio/wav")},
    ).json()["text"]
    reviewed = transcript + " Technician correction: inspection remains pending."
    source = {**SOURCE, "content": reviewed}
    ai = client.post("/api/v1/capture/structure", json=source).json()
    # Gemma receives the reviewed text through the unchanged capture source schema.
    assert ai["fields"]["observations"] == reviewed
    response = client.post(
        "/api/v1/submissions",
        data={
            "metadata": json.dumps(
                {
                    **source,
                    "aiReview": {
                        "runId": ai["runId"],
                        "fields": ai["fields"],
                        "reviewed": True,
                    },
                }
            )
        },
        files=[("files", ("voice.wav", b"PRIVATE_AUDIO_BYTES", "audio/wav"))],
    )
    assert response.status_code == 201
    record = response.json()
    assert record["content"] == reviewed and record["status"] == "Pending"
    assert make_retriever(config.database_path, "CNC-02").retrieve("vibration") == []
    assert decision(client, record).status_code == 403
    login(client, "other")
    assert (
        client.get("/api/v1/documents/" + record["attachments"][0]["id"]).status_code
        == 404
    )
    login(client, "super")
    assert (
        client.get("/api/v1/documents/" + record["attachments"][0]["id"]).content
        == b"PRIVATE_AUDIO_BYTES"
    )
    assert decision(client, record).status_code == 200
    nodes = make_retriever(config.database_path, "CNC-02").retrieve("vibration")
    assert nodes and any("Technician correction" in n.node.text for n in nodes)
    assert all("PRIVATE_AUDIO_BYTES" not in n.node.text for n in nodes)
