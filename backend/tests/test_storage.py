import json
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.storage.database import connect, initialize
from app.storage.security import create_user

PREFIX = "/api/v1"
HEADERS = {"X-Shift-Request": "1"}
PASSWORD = "test-only-long-password"


@pytest.fixture
def settings(tmp_path):
    settings = Settings(
        environment="test",
        database_path=str(tmp_path / "shift.sqlite3"),
        _env_file=None,
    )
    initialize(settings.database_path)
    with connect(settings.database_path) as db:
        for username, role in [
            ("tech", "technician"),
            ("other", "technician"),
            ("super", "supervisor"),
        ]:
            create_user(db, username, username.title(), role, PASSWORD)
    return settings


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), headers=HEADERS) as client:
        yield client


def login(client, name="tech"):
    r = client.post(
        PREFIX + "/auth/login", json={"username": name, "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return r


def submit(client, files=None, **fields):
    body = dict(
        machineId="CNC-01",
        title="Synthetic observation",
        symptom="Vibration",
        content="Observed vibration after a synthetic tooling change.",
        kind="Field note",
    )
    body.update(fields)
    response = client.post(
        PREFIX + "/submissions", data={"metadata": json.dumps(body)}, files=files
    )
    assert response.status_code == 201, response.text
    return response.json()


def decide(client, r, decision="Approved", note=""):
    return client.post(
        PREFIX + f"/submissions/{r['id']}/review",
        json={"versionId": r["versionId"], "decision": decision, "note": note},
    )


def test_auth_and_csrf(client):
    assert client.get(PREFIX + "/knowledge").status_code == 401
    assert (
        client.post(
            PREFIX + "/auth/login",
            headers={"X-Shift-Request": ""},
            json={"username": "tech", "password": PASSWORD},
        ).status_code
        == 403
    )
    assert (
        client.post(
            PREFIX + "/auth/login",
            headers={"Origin": "https://evil.example"},
            json={"username": "tech", "password": PASSWORD},
        ).status_code
        == 403
    )
    response = login(client)
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert "password_hash" not in response.text
    assert client.get(PREFIX + "/auth/me").json()["role"] == "technician"
    client.post(PREFIX + "/auth/logout")
    assert client.get(PREFIX + "/auth/me").status_code == 401


def test_login_rate_limit(client):
    for _ in range(5):
        assert (
            client.post(
                PREFIX + "/auth/login", json={"username": "tech", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            PREFIX + "/auth/login", json={"username": "tech", "password": PASSWORD}
        ).status_code
        == 429
    )


def test_session_expiry_and_hashed_storage(client, settings):
    login(client)
    cookie = client.cookies.get("shift_session")
    with connect(settings.database_path) as db:
        assert db.execute("SELECT token_hash FROM sessions").fetchone()[0] != cookie
        assert (
            not db.execute("SELECT password_hash FROM users").fetchone()[0] == PASSWORD
        )
        db.execute("UPDATE sessions SET expires_at=?", (int(time.time()) - 1,))
    assert client.get(PREFIX + "/auth/me").status_code == 401


def test_capture_approve_restart_and_audit(client, settings):
    login(client)
    r = submit(
        client,
        files=[("files", ("note.txt", b"Synthetic supporting evidence", "text/plain"))],
    )
    assert r["author"] == "Tech" and r["status"] == "Pending"
    assert r["id"] not in [v["id"] for v in client.get(PREFIX + "/knowledge").json()]
    assert decide(client, r).status_code == 403
    login(client, "other")
    assert r["id"] not in [v["id"] for v in client.get(PREFIX + "/submissions").json()]
    document = r["attachments"][0]["id"]
    assert client.get(PREFIX + "/documents/" + document).status_code == 404
    login(client, "super")
    assert decide(client, r).status_code == 200
    assert decide(client, r).status_code == 409
    history = client.get(PREFIX + f"/submissions/{r['id']}/history").json()
    assert len(history["reviews"]) == 1
    assert history["reviews"][0]["reviewer_name"] == "Super"
    # A fresh application and connection use the same on-disk database.
    with TestClient(create_app(settings), headers=HEADERS) as restarted:
        login(restarted, "other")
        found = restarted.get(
            PREFIX + "/knowledge", params={"q": "tooling", "machine": "CNC-01"}
        ).json()
        assert r["id"] in [v["id"] for v in found]
        assert (
            restarted.get(PREFIX + "/documents/" + document).content
            == b"Synthetic supporting evidence"
        )
        assert (
            restarted.get(
                PREFIX + "/knowledge", params={"machine": "PRESS-01", "q": "tooling"}
            ).json()
            == []
        )


def test_rejection_and_revocation_gate_documents(client):
    login(client)
    rejected = submit(client)
    approved = submit(
        client, files=[("files", ("note.md", b"Synthetic markdown", "text/markdown"))]
    )
    login(client, "super")
    assert decide(client, rejected, "Rejected").status_code == 422
    assert (
        decide(client, rejected, "Rejected", "Unsupported observation").status_code
        == 200
    )
    assert decide(client, approved).status_code == 200
    assert decide(client, approved, "Revoked", "Source withdrawn").status_code == 200
    login(client, "other")
    ids = [r["id"] for r in client.get(PREFIX + "/knowledge").json()]
    assert rejected["id"] not in ids and approved["id"] not in ids
    assert (
        client.get(
            PREFIX + "/documents/" + approved["attachments"][0]["id"]
        ).status_code
        == 404
    )


def test_revision_invalidates_old_approval_and_stale_reviews(client):
    login(client)
    original = submit(client)
    login(client, "super")
    assert decide(client, original).status_code == 200
    login(client)
    body = dict(
        machineId="CNC-01",
        title="Updated observation",
        symptom="Vibration",
        content="New unreviewed observation must remain excluded.",
    )
    result = client.post(
        PREFIX + f"/submissions/{original['id']}/revisions",
        data={"metadata": json.dumps(body)},
    )
    assert result.status_code == 201
    revised = result.json()
    assert revised["revision"] == 2 and revised["status"] == "Pending"
    assert original["id"] not in [
        r["id"] for r in client.get(PREFIX + "/knowledge").json()
    ]
    login(client, "super")
    assert decide(client, original).status_code == 409
    assert decide(client, revised).status_code == 200
    history = client.get(PREFIX + f"/submissions/{original['id']}/history").json()
    assert len(history["versions"]) == 2 and len(history["reviews"]) == 2


def test_self_approval_and_spoofing_rejected(client):
    login(client, "super")
    r = submit(client)
    assert decide(client, r).status_code == 403
    payload = dict(
        machineId="CNC-01",
        title="Spoof",
        symptom="Vibration",
        content="Synthetic observation text",
        status="Approved",
        author="Someone else",
    )
    assert (
        client.post(
            PREFIX + "/submissions", data={"metadata": json.dumps(payload)}
        ).status_code
        == 422
    )
    assert (
        client.post(
            PREFIX + f"/submissions/{r['id']}/review",
            json={
                "versionId": r["versionId"],
                "decision": "Approved",
                "reviewer": "Spoof",
            },
        ).status_code
        == 422
    )


def test_upload_validation_and_rollback(client, settings):
    login(client)
    body = json.dumps(
        dict(
            machineId="CNC-01",
            title="Invalid source",
            symptom="Vibration",
            content="Synthetic observation text",
        )
    )
    for name, data in [
        ("bad.exe", b"bad"),
        ("empty.txt", b""),
        ("big.txt", b"x" * (10 * 1024 * 1024 + 1)),
    ]:
        assert (
            client.post(
                PREFIX + "/submissions",
                data={"metadata": body},
                files=[("files", (name, data))],
            ).status_code
            == 422
        )
    with connect(settings.database_path) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM knowledge_records WHERE owner_id IS NOT NULL"
            ).fetchone()[0]
            == 0
        )


def test_migration_and_seed_are_idempotent(settings):
    initialize(settings.database_path)
    initialize(settings.database_path)
    with connect(settings.database_path) as db:
        assert db.execute("SELECT count(*) FROM machines").fetchone()[0] == 6
        assert db.execute("SELECT count(*) FROM knowledge_records").fetchone()[0] == 6
        assert db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 3
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_supervisor_cannot_approve_own_revision_of_another_users_record(client):
    login(client)
    original = submit(client)
    login(client, "super")
    body = dict(
        machineId="CNC-01",
        title="Supervisor revision",
        symptom="Vibration",
        content="Changed content requires independent review.",
    )
    revised = client.post(
        PREFIX + f"/submissions/{original['id']}/revisions",
        data={"metadata": json.dumps(body)},
    ).json()
    assert decide(client, revised).status_code == 403


def test_other_technician_cannot_read_history_or_revise(client):
    login(client)
    original = submit(client)
    login(client, "other")
    assert (
        client.get(PREFIX + f"/submissions/{original['id']}/history").status_code == 404
    )
    body = dict(
        machineId="CNC-01",
        title="Unauthorized revision",
        symptom="Vibration",
        content="This revision must not be accepted.",
    )
    assert (
        client.post(
            PREFIX + f"/submissions/{original['id']}/revisions",
            data={"metadata": json.dumps(body)},
        ).status_code
        == 404
    )
