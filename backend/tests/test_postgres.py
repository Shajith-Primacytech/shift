"""Synthetic integration suite; optional, loopback-only, creates its own databases.

Requires SHIFT_PG_TEST_ADMIN_DSN for a dedicated disposable PG17 cluster. The
fixture owns each random shift_test_* database and drops ONLY that database.
"""

import asyncio
import hashlib
import json
import os
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

psycopg = pytest.importorskip("psycopg", reason="install the optional postgres extra")
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from app.api.capture import capture_service
from app.api.speech import speech_service
from app.api.troubleshooting import rag_service
from app.capture.service import CaptureService
from app.config import Settings
from app.main import create_app
from app.rag.postgres import PostgresRetriever
from app.rag.retrieval import valid_evidence
from app.rag.service import Question, RagFailure, RagService
from app.storage.backend import StorageUnavailable
from app.storage.postgres import local_connection_parameters
from app.storage.postgres_local import bootstrap
from app.storage.security import hash_password, now, token_hash
from tests import test_storage as regression
from tests.capture_fakes import provider as capture_provider
from tests.rag_fakes import ConstantEmbedding, mocked_provider, response_for, selection
from tests.speech_fakes import FakeSpeech

pytestmark = pytest.mark.postgres
PREFIX = regression.PREFIX
HEADERS = regression.HEADERS
PASSWORD = regression.PASSWORD
login = regression.login
submit = regression.submit
decide = regression.decide


@pytest.fixture(scope="session")
def pg_admin():
    dsn = os.environ.get("SHIFT_PG_TEST_ADMIN_DSN")
    if not dsn:
        pytest.skip(
            "no explicit disposable loopback PostgreSQL test cluster configured"
        )
    params = local_connection_parameters(dsn)
    # Never infer credentials or a hosted database from .env, PG* or project links.
    password = os.environ.get("SHIFT_PG_TEST_RUNTIME_PASSWORD")
    if not password:
        pytest.fail(
            "set an explicit local SHIFT_PG_TEST_RUNTIME_PASSWORD for the disposable cluster"
        )
    return params, password


@pytest.fixture
def pg_database(pg_admin, monkeypatch, tmp_path):
    params, password = pg_admin
    name = "shift_test_" + secrets.token_hex(8)
    runtime_keys = {k: params[k] for k in ("host", "port") if k in params}
    runtime_dsn = make_conninfo(
        **runtime_keys, dbname=name, user="shift_runtime", password=password
    )
    with psycopg.connect(**params, autocommit=True) as control:
        control.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                sql.Identifier(name)
            )
        )
    database_params = dict(params, dbname=name)
    try:
        with psycopg.connect(
            **database_params, autocommit=True, row_factory=dict_row
        ) as admin:
            assert admin.info.server_version // 10000 == 17
            bootstrap(admin, password)
            for username, role in (
                ("tech", "technician"),
                ("other", "technician"),
                ("super", "supervisor"),
                ("super2", "supervisor"),
            ):
                admin.execute(
                    "INSERT INTO shift_private.users (id,username,name,role,password_hash,created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        username,
                        username,
                        username.title(),
                        role,
                        hash_password(PASSWORD),
                        now(),
                    ),
                )
        monkeypatch.setenv("SHIFT_POSTGRES_DSN", runtime_dsn)
        cfg = Settings(
            _env_file=None,
            environment="test",
            storage_backend="postgres",
            database_path=str(tmp_path / "must-not-be-created.sqlite3"),
        )
        yield {"settings": cfg, "admin": database_params}
        assert not (tmp_path / "must-not-be-created.sqlite3").exists()
    finally:
        with psycopg.connect(**params, autocommit=True) as control:
            # name is generated and created above, never read from user configuration.
            control.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def settings(pg_database):
    return pg_database["settings"]


@pytest.fixture
def admin(pg_database):
    with psycopg.connect(
        **pg_database["admin"], autocommit=True, row_factory=dict_row
    ) as conn:
        yield conn


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), headers=HEADERS) as value:
        yield value


@pytest.fixture
def store(client):
    return client.app.state.storage


# Run the existing HTTP behavior assertions unchanged on PostgreSQL.
test_auth_and_csrf = regression.test_auth_and_csrf
test_login_rate_limit = regression.test_login_rate_limit
test_capture_approve_restart_and_audit = (
    regression.test_capture_approve_restart_and_audit
)
test_rejection_and_revocation_gate_documents = (
    regression.test_rejection_and_revocation_gate_documents
)
test_revision_invalidates_old_approval_and_stale_reviews = (
    regression.test_revision_invalidates_old_approval_and_stale_reviews
)
test_self_approval_and_spoofing_rejected = (
    regression.test_self_approval_and_spoofing_rejected
)
test_supervisor_cannot_approve_own_revision_of_another_users_record = (
    regression.test_supervisor_cannot_approve_own_revision_of_another_users_record
)
test_other_technician_cannot_read_history_or_revise = (
    regression.test_other_technician_cannot_read_history_or_revise
)


def run_concurrent(settings, actors, operation):
    barrier = threading.Barrier(len(actors))

    def run(actor):
        with TestClient(create_app(settings), headers=HEADERS) as c:
            login(c, actor)
            barrier.wait(timeout=15)
            return operation(c)

    with ThreadPoolExecutor(max_workers=len(actors)) as executor:
        return list(executor.map(run, actors))


def test_concurrent_supervisor_reviews_are_atomic(client, settings, admin):
    login(client)
    record = submit(client)
    results = run_concurrent(settings, ["super", "super2"], lambda c: decide(c, record))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.review_events WHERE version_id=%s",
            (record["versionId"],),
        ).fetchone()["total"]
        == 1
    )


def revision(c, record):
    return c.post(
        PREFIX + f"/submissions/{record['id']}/revisions",
        data={
            "metadata": json.dumps(
                {
                    "machineId": "CNC-01",
                    "title": "Concurrent revision",
                    "symptom": "Vibration",
                    "content": "Synthetic revision must await independent approval.",
                }
            )
        },
    )


def test_concurrent_revisions_have_unique_monotonic_versions(client, settings):
    login(client)
    original = submit(client)
    results = run_concurrent(
        settings, ["tech", "tech"], lambda c: revision(c, original)
    )
    assert [r.status_code for r in results] == [201, 201]
    assert sorted(r.json()["revision"] for r in results) == [2, 3]
    versions = client.get(PREFIX + f"/submissions/{original['id']}/history").json()[
        "versions"
    ]
    assert [v["revision"] for v in versions] == [1, 2, 3]
    assert all(v["status"] == "Pending" for v in versions)


def test_review_versus_revision_never_exposes_old_approval(client, settings):
    login(client)
    original = submit(client)
    barrier = threading.Barrier(2)

    def run(actor):
        with TestClient(create_app(settings), headers=HEADERS) as c:
            login(c, actor)
            barrier.wait(timeout=15)
            return decide(c, original) if actor == "super" else revision(c, original)

    with ThreadPoolExecutor(max_workers=2) as executor:
        approval, revised = list(executor.map(run, ["super", "tech"]))
    assert approval.status_code in (200, 409)
    assert revised.status_code == 201
    assert original["id"] not in [
        r["id"] for r in client.get(PREFIX + "/knowledge").json()
    ]


def test_binary_documents_and_literal_search(client):
    login(client)
    data = bytes(range(256)) * 100
    record = submit(
        client,
        title="Literal %_ ÄBC",
        files=[("files", ("fixture.pdf", data, "application/pdf"))],
    )
    assert record["attachments"][0]["sha256"] == hashlib.sha256(data).hexdigest()
    login(client, "super")
    assert decide(client, record).status_code == 200
    doc = client.get(PREFIX + "/documents/" + record["attachments"][0]["id"])
    assert doc.content == data
    assert doc.headers["x-content-type-options"] == "nosniff"
    for query, found in (
        ("%_", True),
        ("ÄBC", True),
        ("äbc", False),
        ("x' OR 1=1 --", False),
    ):
        rows = client.get(PREFIX + "/knowledge", params={"q": query}).json()
        assert (record["id"] in [r["id"] for r in rows]) == found


def test_hashed_sessions_expiry_and_production_cookies(client, admin):
    login(client)
    token = client.cookies.get("shift_session")
    assert admin.execute("SELECT token_hash FROM shift_private.sessions").fetchone()[
        "token_hash"
    ] == token_hash(token)
    assert (
        admin.execute(
            "SELECT password_hash FROM shift_private.users WHERE username='tech'"
        ).fetchone()["password_hash"]
        != PASSWORD
    )
    admin.execute(
        "UPDATE shift_private.sessions SET expires_at=%s", (int(time.time()) - 1,)
    )
    assert client.get(PREFIX + "/auth/me").status_code == 401
    # Test the shared cookie formatter without enabling a production PG connection.
    client.app.state.settings.environment = "production"
    response = login(client)
    assert (
        "Secure" in response.headers["set-cookie"]
        and "HttpOnly" in response.headers["set-cookie"]
    )
    client.app.state.settings.environment = "test"


def test_upload_validation_leaves_no_partial_rows(client, admin):
    login(client)
    body = json.dumps(
        {
            "machineId": "CNC-01",
            "title": "Invalid upload",
            "symptom": "Vibration",
            "content": "Synthetic invalid file observation.",
        }
    )
    for name, data in (
        ("bad.exe", b"bad"),
        ("empty.txt", b""),
        ("big.txt", b"x" * (10 * 1024 * 1024 + 1)),
    ):
        assert (
            client.post(
                PREFIX + "/submissions",
                data={"metadata": body},
                files=[("files", (name, data))],
            ).status_code
            == 422
        )
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.knowledge_records WHERE owner_id IS NOT NULL"
        ).fetchone()["total"]
        == 0
    )


def pg_retriever(store, machine):
    return PostgresRetriever(
        store,
        machine,
        embed_model=ConstantEmbedding(),
        embedding_key="test-only-constant-384",
        token_fn=lambda text: text.split(),
    )


def test_pgvector_fts_and_approved_only_rag(store, admin):
    retriever = pg_retriever(store, "CNC-01")
    nodes = retriever.retrieve("spindle vibration")
    assert {n.node.metadata["record_id"] for n in nodes} == {"SOP-001", "NOTE-002"}
    assert valid_evidence(store, "CNC-01", nodes)
    assert (
        admin.execute(
            "SELECT extensions.vector_dims(vector) AS dims FROM shift_private.chunk_embeddings LIMIT 1"
        ).fetchone()["dims"]
        == 384
    )
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.knowledge_chunks WHERE search_vector @@ to_tsquery('simple','vibration')"
        ).fetchone()["total"]
        > 0
    )
    answer = asyncio.run(
        RagService(store, mocked_provider(), pg_retriever).answer(
            Question(
                machine_id="CNC-01",
                question="What should I check for spindle vibration?",
            )
        )
    )
    assert answer["status"] == "answered" and answer["citations"]
    assert all(c["machine_id"] == "CNC-01" for c in answer["citations"])
    admin.execute(
        "UPDATE shift_private.knowledge_versions SET status='Revoked' WHERE machine_id='CNC-01' AND status='Approved'"
    )
    assert not valid_evidence(store, "CNC-01", nodes)
    assert retriever.retrieve("spindle vibration") == []


def test_revocation_during_inference_discards_answer(store, admin):
    def handler(request):
        response = response_for(selection(request))
        admin.execute(
            "UPDATE shift_private.knowledge_versions SET status='Revoked' WHERE id='SOP-001-v1'"
        )
        return response

    with pytest.raises(RagFailure, match="revoked or superseded"):
        asyncio.run(
            RagService(store, mocked_provider(handler), pg_retriever).answer(
                Question(
                    machine_id="CNC-01",
                    question="What should I check for spindle vibration?",
                )
            )
        )


def test_source_or_chunk_tampering_invalidates_evidence(store, admin):
    nodes = pg_retriever(store, "CNC-01").retrieve("spindle vibration")
    admin.execute(
        "UPDATE shift_private.knowledge_chunks SET content='Changed synthetic chunk' WHERE id=%s",
        (nodes[0].node.node_id,),
    )
    assert not valid_evidence(store, "CNC-01", nodes)


def test_pending_revision_excludes_cached_evidence(store, admin):
    nodes = pg_retriever(store, "CNC-01").retrieve("spindle vibration")
    admin.execute(
        "INSERT INTO shift_private.knowledge_versions (id,record_id,revision,machine_id,title,symptom,content,kind,author,status,created_at) SELECT 'SOP-001-v2',record_id,2,machine_id,title,symptom,'Unreviewed synthetic revision',kind,author,'Pending',created_at FROM shift_private.knowledge_versions WHERE id='SOP-001-v1'"
    )
    assert not valid_evidence(store, "CNC-01", nodes)
    assert "SOP-001" not in {
        n.node.metadata["record_id"]
        for n in pg_retriever(store, "CNC-01").retrieve("spindle vibration")
    }


def test_empty_scope_never_calls_model_or_amd(store):
    def forbidden(request):
        pytest.fail("unsupported scope must not call AMD")

    answer = asyncio.run(
        RagService(store, mocked_provider(forbidden), pg_retriever).answer(
            Question(machine_id="CNC-02", question="Unsupported spindle vibration")
        )
    )
    assert answer["status"] == "insufficient_evidence"


def test_capture_ai_one_use_is_atomic(client, settings, admin):
    from tests.test_capture import SOURCE

    client.app.dependency_overrides[capture_service] = lambda: CaptureService(
        capture_provider()
    )
    login(client)
    structured = client.post(PREFIX + "/capture/structure", json=SOURCE)
    assert structured.status_code == 200
    result = structured.json()
    body = {
        **SOURCE,
        "aiReview": {
            "runId": result["runId"],
            "fields": result["fields"],
            "reviewed": True,
        },
    }
    results = run_concurrent(
        settings,
        ["tech", "tech"],
        lambda c: c.post(PREFIX + "/submissions", data={"metadata": json.dumps(body)}),
    )
    assert sorted(r.status_code for r in results) == [201, 422]
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.knowledge_records WHERE owner_id IS NOT NULL"
        ).fetchone()["total"]
        == 1
    )
    record = next(r.json() for r in results if r.status_code == 201)
    assert (
        record["aiCapture"]["fields"] == result["fields"]
        and record["status"] == "Pending"
    )
    assert record["id"] not in [
        r["id"] for r in client.get(PREFIX + "/knowledge").json()
    ]
    login(client, "super")
    assert decide(client, record).status_code == 200
    assert (
        decide(client, record, "Revoked", "Synthetic source withdrawn").status_code
        == 200
    )


def test_capture_session_rechecked_after_amd(client, admin):
    from tests.test_capture import SOURCE
    from tests.capture_fakes import handler

    def callback(request):
        admin.execute("DELETE FROM shift_private.sessions")
        return handler(request)

    client.app.dependency_overrides[capture_service] = lambda: CaptureService(
        capture_provider(callback)
    )
    login(client)
    assert client.post(PREFIX + "/capture/structure", json=SOURCE).status_code == 401
    assert (
        admin.execute("SELECT execution FROM shift_private.capture_ai_runs").fetchone()[
            "execution"
        ]["status"]
        == "success"
    )


def test_speech_uses_existing_provider_and_rechecks_session(client, admin):
    class Speech(FakeSpeech):
        def transcribe(self, data):
            admin.execute("DELETE FROM shift_private.sessions")
            return super().transcribe(data)

    client.app.dependency_overrides[speech_service] = Speech
    login(client)
    assert client.get(PREFIX + "/capture/voice/status").json()["available"]
    assert (
        client.post(
            PREFIX + "/capture/transcribe",
            files={"file": ("test.wav", b"synthetic audio", "audio/wav")},
        ).status_code
        == 401
    )
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.source_documents"
        ).fetchone()["total"]
        == 0
    )


def test_runtime_least_privilege_and_rls(store, admin):
    for command in (
        "CREATE TABLE shift_private.forbidden (id int)",
        "TRUNCATE shift_private.review_events",
        "DELETE FROM shift_private.review_events",
        "UPDATE shift_private.users SET role='supervisor'",
        "UPDATE shift_private.knowledge_versions SET content='forged'",
        "DELETE FROM shift_private.source_documents",
        "SELECT * FROM shift_private.schema_migrations",
        "SELECT * FROM shift_private.conversations",
        "SET ROLE shift_owner",
    ):
        with pytest.raises(StorageUnavailable):
            with store.connection() as conn:
                conn.execute(command)
    assert store.machines()  # failed transactions cannot poison the pool
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='shift_private' AND c.relkind='r' AND NOT c.relrowsecurity"
        ).fetchone()["total"]
        == 0
    )
    assert not admin.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_namespace n, LATERAL aclexplode(n.nspacl) a WHERE n.nspname='shift_private' AND a.grantee=0 AND a.privilege_type='USAGE') AS permitted"
    ).fetchone()["permitted"]


def test_bootstrap_is_idempotent_and_detects_drift(admin, pg_admin):
    bootstrap(admin, pg_admin[1])
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.machines"
        ).fetchone()["total"]
        == 6
    )
    admin.execute("UPDATE shift_private.schema_migrations SET checksum='invalid'")
    with pytest.raises(StorageUnavailable, match="different migration ledger"):
        bootstrap(admin, pg_admin[1])


def test_concurrent_failed_login_attempts_cannot_bypass_throttle(settings, admin):
    barrier = threading.Barrier(6)

    def attempt(_):
        with TestClient(create_app(settings), headers=HEADERS) as c:
            barrier.wait(timeout=15)
            return c.post(
                PREFIX + "/auth/login",
                json={"username": "tech", "password": "incorrect"},
            ).status_code

    with ThreadPoolExecutor(max_workers=6) as executor:
        statuses = list(executor.map(attempt, range(6)))
    assert statuses.count(401) == 5 and statuses.count(429) == 1
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.login_attempts"
        ).fetchone()["total"]
        == 5
    )


def test_capture_receipt_and_cooldown_are_committed_without_inference_transaction(
    client, settings, admin
):
    from tests.test_capture import SOURCE
    from tests.capture_fakes import handler

    store = client.app.state.storage

    def callback(request):
        stats = store.pool.get_stats()
        assert stats["pool_available"] == stats["pool_size"]
        assert (
            admin.execute(
                "SELECT execution FROM shift_private.capture_ai_runs"
            ).fetchone()["execution"]["status"]
            == "interrupted"
        )
        return handler(request)

    client.app.dependency_overrides[capture_service] = lambda: CaptureService(
        capture_provider(callback)
    )
    login(client)
    assert client.post(PREFIX + "/capture/structure", json=SOURCE).status_code == 200
    assert client.post(PREFIX + "/capture/structure", json=SOURCE).status_code == 429


def test_capture_cooldown_serializes_distinct_connections(store):
    from app.storage.capture_schema import SubmissionFields
    from tests.test_capture import SOURCE

    barrier = threading.Barrier(2)

    def receipt(_):
        barrier.wait(timeout=15)
        try:
            store.capture_receipt(SubmissionFields(**SOURCE), {"id": "tech"})
            return 200
        except Exception as exc:
            if getattr(exc, "status_code", None) != 429:
                raise
            return 429

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(receipt, range(2))) == [200, 429]


def test_capture_run_owner_and_original_source_are_preserved(client, admin):
    from tests.test_capture import SOURCE

    client.app.dependency_overrides[capture_service] = lambda: CaptureService(
        capture_provider()
    )
    login(client)
    result = client.post(PREFIX + "/capture/structure", json=SOURCE).json()
    body = {
        **SOURCE,
        "aiReview": {
            "runId": result["runId"],
            "fields": result["fields"],
            "reviewed": True,
        },
    }
    changed = {
        **body,
        "content": "Changed original observation invalidates the proposed structure.",
    }
    assert (
        client.post(
            PREFIX + "/submissions", data={"metadata": json.dumps(changed)}
        ).status_code
        == 422
    )
    login(client, "other")
    assert (
        client.post(
            PREFIX + "/submissions", data={"metadata": json.dumps(body)}
        ).status_code
        == 422
    )
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.knowledge_records WHERE owner_id IS NOT NULL"
        ).fetchone()["total"]
        == 0
    )
    assert (
        admin.execute(
            "SELECT version_id FROM shift_private.capture_ai_runs"
        ).fetchone()["version_id"]
        is None
    )


def test_troubleshooting_endpoint_uses_postgres_and_rechecks_session(client, admin):
    store = client.app.state.storage

    def callback(request):
        stats = store.pool.get_stats()
        assert stats["pool_available"] == stats["pool_size"]
        response = response_for(selection(request))
        admin.execute("DELETE FROM shift_private.sessions")
        return response

    client.app.dependency_overrides[rag_service] = lambda: RagService(
        store, mocked_provider(callback), pg_retriever
    )
    login(client)
    response = client.post(
        PREFIX + "/troubleshoot",
        json={
            "machine_id": "CNC-01",
            "question": "What should I check for spindle vibration?",
        },
    )
    assert response.status_code == 401


def test_embedding_key_change_during_inference_discards_answer(store, admin):
    def callback(request):
        response = response_for(selection(request))
        admin.execute(
            "UPDATE shift_private.chunk_embeddings SET embedding_key='changed-after-retrieval'"
        )
        return response

    with pytest.raises(RagFailure, match="revoked or superseded"):
        asyncio.run(
            RagService(store, mocked_provider(callback), pg_retriever).answer(
                Question(
                    machine_id="CNC-01",
                    question="What should I check for spindle vibration?",
                )
            )
        )


def test_pool_errors_are_sanitized_and_do_not_fallback(client, store):
    store.close()
    response = client.get(PREFIX + "/auth/me")
    assert response.status_code == 503
    assert "password" not in response.text and "postgresql" not in response.text


def test_target_columns_match_ephemeral_sqlite_schema(admin):
    import sqlite3
    from pathlib import Path

    # Create an in-memory source schema; never open an existing SQLite file.
    with sqlite3.connect(":memory:") as source:
        migrations = Path(__file__).resolve().parents[1] / "migrations"
        for path in sorted(migrations.glob("*.sql")):
            source.executescript(path.read_text())
        tables = [
            r[0]
            for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if not r[0].startswith("rag_fts")
        ]
        for table in tables:
            assert table.replace("_", "").isalnum()
            source_columns = {
                r[1] for r in source.execute(f'PRAGMA table_info("{table}")')
            }
            target_columns = {
                r["column_name"]
                for r in admin.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='shift_private' AND table_name=%s",
                    (table,),
                )
            }
            assert target_columns == source_columns | (
                {"search_vector"} if table == "knowledge_chunks" else set()
            )
            source_fks = list(source.execute(f'PRAGMA foreign_key_list("{table}")'))
            target_fks = admin.execute(
                "SELECT count(*) AS total FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='shift_private' AND t.relname=%s AND c.contype='f'",
                (table,),
            ).fetchone()["total"]
            assert target_fks == len(source_fks)


def test_failed_attachment_insert_rolls_back_entire_submission(store, admin):
    from app.storage.capture_schema import Submission

    body = Submission(
        machineId="CNC-01",
        title="Atomic upload",
        symptom="Vibration",
        content="Synthetic attachment transaction test.",
    )
    user = {"id": "tech", "name": "Tech", "role": "technician"}
    # Inject a DB-level failure after the first binary insert, inside the same UoW.
    with pytest.raises(StorageUnavailable):
        store.save_submission(
            body,
            [("first.txt", "text/plain", b"first"), ("second.txt", None, b"second")],
            user,
        )
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.knowledge_records WHERE owner_id IS NOT NULL"
        ).fetchone()["total"]
        == 0
    )
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.source_documents"
        ).fetchone()["total"]
        == 0
    )
    assert store.machines()


def test_failed_audit_insert_rolls_back_approval(client, admin):
    login(client)
    record = submit(client)
    login(client, "super")
    # Deny the audit insertion in this disposable database, after status UPDATE.
    admin.execute("REVOKE INSERT ON shift_private.review_events FROM shift_runtime")
    response = decide(client, record)
    assert response.status_code == 503
    assert (
        admin.execute(
            "SELECT status FROM shift_private.knowledge_versions WHERE id=%s",
            (record["versionId"],),
        ).fetchone()["status"]
        == "Pending"
    )
    assert (
        admin.execute(
            "SELECT count(*) AS total FROM shift_private.review_events WHERE version_id=%s",
            (record["versionId"],),
        ).fetchone()["total"]
        == 0
    )
