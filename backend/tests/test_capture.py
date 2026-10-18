import asyncio
import json

import httpx
import pytest
from app.api.capture import capture_service
from app.capture.service import MODEL, CaptureService, configured_capture_provider
from app.config import Settings
from app.main import create_app
from app.storage.capture_schema import ProposedStructure, SubmissionFields
from app.storage.database import connect, initialize
from app.storage.security import create_user
from fastapi.testclient import TestClient

from tests.capture_fakes import KEY, handler, proposal_for, provider, response_for
from tests.rag_fakes import test_retriever as make_retriever

SOURCE = {
    "machineId": "CNC-02",
    "title": "Synthetic vibration observation",
    "symptom": "Vibration",
    "content": "Synthetic vibration after a tool change. Cause is unconfirmed. Inspection is planned.",
}
HEADERS = {"X-Shift-Request": "1"}
PASSWORD = "capture-test-only-password"


def run(callback=handler, source=SOURCE):
    return asyncio.run(
        CaptureService(provider(callback)).structure(SubmissionFields(**source))
    )


def test_success_is_extractive_json_and_pinned_gemma():
    seen = []

    def callback(request):
        payload = json.loads(request.content)
        seen.append(payload)
        assert payload["model"] == MODEL
        assert payload["response_format"]["type"] == "json_schema"
        schema = payload["response_format"]["json_schema"]
        assert schema["strict"] is True
        assert len(schema["schema"]["required"]) == 10
        assert payload["stream"] is False
        return handler(request)

    result, status = run(callback)
    assert status == 200 and len(seen) == 1
    assert result["fields"]["observations"] == SOURCE["content"]
    assert result["fields"]["confirmedRootCause"] == ""
    assert result["execution"]["provider"] == "AMD Token Factory"
    assert result["execution"]["model_id"] == "self-dploy/" + MODEL
    assert result["execution"]["usage"]["total_tokens"] == 150
    assert result["execution"]["status"] == "success"
    assert result["execution"]["latency_ms"] >= 0
    assert KEY not in json.dumps(result)


@pytest.mark.parametrize(
    "variant",
    [
        "malformed",
        "fenced",
        "extra",
        "missing",
        "fabricated",
        "empty",
        "wrong_type",
        "oversized",
        "wrong_model",
    ],
)
def test_invalid_structures_never_become_proposals(variant):
    calls = []

    def callback(request):
        calls.append(request)
        proposal = proposal_for(SOURCE)
        if variant == "extra":
            proposal["diagnosis"] = "Invented repair"
        if variant == "missing":
            del proposal["faultCodes"]
        if variant == "fabricated":
            proposal["observations"][0]["quote"] = "Repair completed successfully."
        if variant == "empty":
            proposal["observations"] = []
        if variant == "wrong_type":
            proposal["observations"] = "Plain text"
        if variant == "oversized":
            proposal["observations"] *= 6
        response = response_for(proposal)
        body = response.json()
        if variant == "malformed":
            body["choices"][0]["message"]["content"] = "not valid JSON"
        if variant == "fenced":
            body["choices"][0]["message"]["content"] = (
                "```json\n" + json.dumps(proposal) + "\n```"
            )
        if variant == "wrong_model":
            body["model"] = "DeepSeek-V4-Flash"
        return httpx.Response(200, json=body)

    result, status = run(callback)
    assert status == 502 and len(calls) == 1
    assert "fields" not in result and "proposal" not in result
    assert result["execution"]["status"] == "failure"
    assert result["execution"]["usage"]["total_tokens"] == 150
    assert KEY not in json.dumps(result)


@pytest.mark.parametrize(
    "status,code,outgoing",
    [
        (400, "http", 503),
        (422, "http", 503),
        (401, "authentication", 503),
        (429, "rate_limit", 429),
        (503, "http", 503),
    ],
)
def test_upstream_errors_have_metadata_and_no_fallback_or_retry(status, code, outgoing):
    calls = []

    def callback(request):
        calls.append(request)
        return httpx.Response(
            status,
            json={"error": {"message": "private provider details " + KEY}},
            headers={"Retry-After": "0"},
        )

    result, response_status = run(callback)
    assert response_status == outgoing and len(calls) == 1
    assert result["execution"]["http_status"] == status
    assert result["execution"]["error_code"] == code
    assert KEY not in json.dumps(
        result
    ) and "private provider details" not in json.dumps(result)
    if status in (400, 422):
        assert "structured-output" in result["detail"]


@pytest.mark.parametrize(
    "exception", [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError]
)
def test_timeouts_and_connection_failures_are_never_replayed(exception):
    calls = []

    def callback(request):
        calls.append(request)
        raise exception(KEY, request=request)

    result, status = run(callback)
    assert status in (503, 504) and len(calls) == 1
    assert result["execution"]["status"] == "failure" and "proposal" not in result
    assert KEY not in json.dumps(result)


def test_missing_credentials_and_pin_do_not_change_troubleshooting(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AMD_API_KEY", raising=False)
    monkeypatch.setenv("AMD_MODEL", "DeepSeek-V4-Flash")
    monkeypatch.setenv("AMD_MAX_RETRIES", "2")
    adapter = configured_capture_provider()
    assert adapter._settings.model == MODEL and adapter._settings.max_retries == 0
    assert __import__("os").environ["AMD_MODEL"] == "DeepSeek-V4-Flash"
    result, status = asyncio.run(CaptureService().structure(SubmissionFields(**SOURCE)))
    assert status == 503 and result["execution"]["error_code"] == "configuration"


@pytest.fixture
def workspace(tmp_path):
    config = Settings(
        _env_file=None,
        environment="test",
        database_path=str(tmp_path / "capture.sqlite3"),
    )
    initialize(config.database_path)
    with connect(config.database_path) as db:
        for username, role in [
            ("tech", "technician"),
            ("other", "technician"),
            ("super", "supervisor"),
        ]:
            create_user(db, username, username.title(), role, PASSWORD)
    app = create_app(config)
    app.dependency_overrides[capture_service] = lambda: CaptureService(provider())
    with TestClient(app, headers=HEADERS) as client:
        yield client, config


def login(client, username="tech"):
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
        ).status_code
        == 200
    )


def structure(client):
    response = client.post("/api/v1/capture/structure", json=SOURCE)
    assert response.status_code == 200, response.text
    return response.json()


def save(client, result, **overrides):
    fields = dict(
        result["fields"],
        observedOutcome="Inspection escalated; no repair or resolution confirmed.",
    )
    payload = {
        **SOURCE,
        "aiReview": {"runId": result["runId"], "fields": fields, "reviewed": True},
        **overrides,
    }
    return client.post("/api/v1/submissions", data={"metadata": json.dumps(payload)})


def decision(client, record, status="Approved", note=""):
    return client.post(
        f"/api/v1/submissions/{record['id']}/review",
        json={"versionId": record["versionId"], "decision": status, "note": note},
    )


def test_end_to_end_pending_edit_approve_index_and_revoke(workspace):
    client, config = workspace
    login(client)
    result = structure(client)
    # A draft does not create a knowledge version or a review event.
    with connect(config.database_path) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM knowledge_records WHERE owner_id IS NOT NULL"
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT version_id FROM capture_ai_runs WHERE id=?", (result["runId"],)
            ).fetchone()[0]
            is None
        )
    assert make_retriever(config.database_path, "CNC-02").retrieve("vibration") == []
    response = save(client, result)
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["status"] == "Pending" and record["content"] == SOURCE["content"]
    assert record["aiCapture"]["original"]["content"] == SOURCE["content"]
    assert "no repair" in record["aiCapture"]["fields"]["observedOutcome"]
    assert record["aiCapture"]["execution"] == result["execution"]
    assert make_retriever(config.database_path, "CNC-02").retrieve("vibration") == []
    assert client.get("/api/v1/knowledge", params={"machine": "CNC-02"}).json() == []
    assert decision(client, record).status_code == 403
    login(client, "other")
    assert record["id"] not in [
        r["id"] for r in client.get("/api/v1/submissions").json()
    ]
    login(client, "super")
    assert decision(client, record).status_code == 200
    nodes = make_retriever(config.database_path, "CNC-02").retrieve("vibration")
    assert nodes and {n.node.metadata["record_id"] for n in nodes} == {record["id"]}
    assert any("no repair" in n.node.text for n in nodes)
    assert decision(client, record).status_code == 409
    history = client.get(f"/api/v1/submissions/{record['id']}/history").json()
    assert len(history["reviews"]) == 1 and len(history["versions"]) == 1
    assert history["versions"][0]["aiCapture"]["execution"] == result["execution"]
    assert decision(client, record, "Revoked", "Source withdrawn").status_code == 200
    assert make_retriever(config.database_path, "CNC-02").retrieve("vibration") == []
    # Reopen app / database, AI provenance and original remain durable.
    with TestClient(create_app(config), headers=HEADERS) as restarted:
        login(restarted)
        saved = next(
            r
            for r in restarted.get("/api/v1/submissions").json()
            if r["id"] == record["id"]
        )
        assert saved["aiCapture"]["original"]["content"] == SOURCE["content"]
        assert saved["aiCapture"]["execution"] == result["execution"]


def test_run_ownership_stale_source_confirmation_and_one_use(workspace):
    client, config = workspace
    login(client)
    result = structure(client)
    assert (
        save(
            client, result, content=SOURCE["content"] + " Changed after AI."
        ).status_code
        == 422
    )
    unreviewed = {
        "runId": result["runId"],
        "fields": result["fields"],
        "reviewed": False,
    }
    assert save(client, result, aiReview=unreviewed).status_code == 422
    login(client, "other")
    assert save(client, result).status_code == 422
    login(client)
    assert save(client, result).status_code == 201
    assert save(client, result).status_code == 422
    with connect(config.database_path) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM knowledge_records WHERE owner_id IS NOT NULL"
            ).fetchone()[0]
            == 1
        )


def test_failed_run_cannot_submit_ai_but_manual_capture_survives(workspace):
    client, config = workspace
    client.app.dependency_overrides[capture_service] = lambda: CaptureService(
        provider(lambda req: httpx.Response(429, json={"error": KEY}))
    )
    login(client)
    failed = client.post("/api/v1/capture/structure", json=SOURCE)
    assert (
        failed.status_code == 429 and failed.json()["execution"]["status"] == "failure"
    )
    fake = {
        **failed.json(),
        "fields": {name: "" for name in ProposedStructure.model_fields},
    }
    assert save(client, fake).status_code == 422
    manual = client.post("/api/v1/submissions", data={"metadata": json.dumps(SOURCE)})
    assert manual.status_code == 201 and manual.json()["aiCapture"] is None
    assert (
        manual.json()["content"] == SOURCE["content"]
        and manual.json()["status"] == "Pending"
    )
    with connect(config.database_path) as db:
        execution = json.loads(
            db.execute("SELECT execution FROM capture_ai_runs").fetchone()[0]
        )
        assert execution["error_code"] == "rate_limit" and KEY not in json.dumps(
            execution
        )


def test_endpoint_auth_csrf_machine_validation_and_cost_guard(workspace):
    client, config = workspace
    assert client.post("/api/v1/capture/structure", json=SOURCE).status_code == 401
    login(client)
    assert (
        client.post(
            "/api/v1/capture/structure", json=SOURCE, headers={"X-Shift-Request": ""}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/capture/structure", json={**SOURCE, "machineId": "UNKNOWN"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/capture/structure", json={**SOURCE, "status": "Approved"}
        ).status_code
        == 422
    )
    structure(client)
    assert client.post("/api/v1/capture/structure", json=SOURCE).status_code == 429
    with connect(config.database_path) as db:
        assert db.execute("SELECT count(*) FROM capture_ai_runs").fetchone()[0] == 1


def test_session_revoked_during_inference_returns_no_proposal(workspace):
    client, config = workspace

    def callback(request):
        with connect(config.database_path) as db:
            db.execute("DELETE FROM sessions")
        return handler(request)

    client.app.dependency_overrides[capture_service] = lambda: CaptureService(
        provider(callback)
    )
    login(client)
    response = client.post("/api/v1/capture/structure", json=SOURCE)
    assert response.status_code == 401 and "proposal" not in response.json()


def test_truncated_completion_preserves_safe_usage_but_not_a_proposal():
    def callback(request):
        body = response_for(proposal_for(SOURCE)).json()
        body["choices"][0]["finish_reason"] = "length"
        return httpx.Response(200, json=body)

    result, status = run(callback)
    assert status == 503 and "proposal" not in result
    assert result["execution"]["status"] == "failure"
    assert result["execution"]["error_code"] == "model"
    assert result["execution"]["usage"]["total_tokens"] == 150


def test_model_configuration_is_authenticated_sanitized_and_never_inference(
    workspace, monkeypatch, tmp_path
):
    client, _ = workspace
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AMD_API_KEY", KEY)
    monkeypatch.setenv("AMD_MODEL", "DeepSeek-V4-Flash")
    assert client.get("/api/v1/ai/configuration").status_code == 401
    login(client)
    response = client.get("/api/v1/ai/configuration")
    assert response.status_code == 200 and KEY not in response.text
    assert response.json()["capture"] == {
        "provider": "AMD Token Factory",
        "requested_model": MODEL,
        "developer": "Google",
        "status": "configured",
    }
    assert response.json()["troubleshooting"]["requested_model"] == "DeepSeek-V4-Flash"
    assert "returned_model" not in response.text
    monkeypatch.delenv("AMD_API_KEY")
    assert (
        client.get("/api/v1/ai/configuration").json()["capture"]["status"]
        == "unavailable"
    )
    monkeypatch.setenv("AMD_API_KEY", KEY)
    monkeypatch.setenv("AMD_MODEL", KEY)
    assert KEY not in client.get("/api/v1/ai/configuration").text
