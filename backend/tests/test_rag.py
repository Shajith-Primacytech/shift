import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.troubleshooting import rag_service
from app.config import Settings
from app.main import create_app
from app.rag.retrieval import valid_evidence
from app.rag.service import Question, RagFailure, RagService
from app.storage.database import connect, initialize
from app.storage.security import create_user
from tests.rag_fakes import (
    mocked_provider,
    response_for,
    selection,
)
from tests.rag_fakes import (
    test_retriever as make_retriever,
)


@pytest.fixture
def config(tmp_path):
    cfg = Settings(
        environment="test", database_path=str(tmp_path / "rag.sqlite3"), _env_file=None
    )
    initialize(cfg.database_path)
    with connect(cfg.database_path) as db:
        create_user(db, "tech", "Technician", "technician", "test-rag-password")
        for status in ("Rejected", "Revoked", "Pending"):
            rid = "PRIVATE-" + status
            db.execute(
                "INSERT INTO knowledge_records VALUES (?,NULL,?)", (rid, "2026-10-17")
            )
            db.execute(
                "INSERT INTO knowledge_versions (id,record_id,revision,machine_id,title,symptom,content,kind,author,status,created_at) VALUES (?,?,1,?,?,?,?,?,?,?,?)",
                (
                    rid + "-v1",
                    rid,
                    "CNC-01",
                    "Private vibration record",
                    "Spindle vibration",
                    "NEVER_SEND_"
                    + status
                    + " secret synthetic spindle vibration instruction.",
                    "Field note",
                    "Synthetic",
                    status,
                    "2026-10-17",
                ),
            )
    return cfg


def run_answer(
    config,
    handler=None,
    question="What should I check for spindle vibration?",
    machine="CNC-01",
):
    service = RagService(config.database_path, mocked_provider(handler), make_retriever)
    return asyncio.run(service.answer(Question(machine_id=machine, question=question)))


def test_retrieval_persists_chunks_vectors_fts_and_excludes_unapproved(config):
    retriever = make_retriever(config.database_path, "CNC-01")
    nodes = retriever.retrieve("spindle vibration")
    assert {n.node.metadata["record_id"] for n in nodes} == {"SOP-001", "NOTE-002"}
    assert valid_evidence(config.database_path, "CNC-01", nodes)
    ids = [n.node.node_id for n in nodes]
    assert [n.node.node_id for n in retriever.retrieve("spindle vibration")] == ids
    with connect(config.database_path) as db:
        assert db.execute("SELECT count(*) FROM chunk_embeddings").fetchone()[0] > 0
        assert (
            db.execute(
                "SELECT length(vector) FROM chunk_embeddings LIMIT 1"
            ).fetchone()[0]
            == 384 * 4
        )
        assert (
            db.execute(
                "SELECT count(*) FROM rag_fts WHERE rag_fts MATCH 'vibration'"
            ).fetchone()[0]
            > 0
        )
        assert (
            db.execute(
                "SELECT count(*) FROM knowledge_chunks WHERE version_id LIKE 'PRIVATE-%'"
            ).fetchone()[0]
            == 0
        )


def test_actual_outbound_model_prompt_approved_scoped_and_cited(config):
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return response_for(selection(request))

    result = run_answer(config, handler)
    assert result["status"] == "answered" and result["retrieval_mode"] == "hybrid"
    wire = json.dumps(captured)
    assert "NEVER_SEND" not in wire and "SOP-003" not in wire and "PRESS-01" not in wire
    assert len(captured) == 1
    evidence = json.loads(captured[0]["messages"][1]["content"])["approved_evidence"]
    source_text = {s["source_id"]: [p["text"] for p in s["passages"]] for s in evidence}
    assert all(s["text"] in source_text[s["citation_id"]] for s in result["steps"])
    assert all(c["machine_id"] == "CNC-01" for c in result["citations"])
    assert {s["citation_id"] for s in result["steps"]} == {
        c["id"] for c in result["citations"]
    }


@pytest.mark.parametrize(
    "machine,question",
    [
        ("CNC-02", "Spindle vibration"),
        ("CNC-01", "What is the capital of France?"),
        ("CNC-01", "How can I bypass the safety interlock?"),
        ("PRESS-01", "spindle vibration"),
    ],
)
def test_no_evidence_or_unsafe_question_never_calls_provider(config, machine, question):
    def handler(request):
        pytest.fail("No model call should occur")

    result = run_answer(config, handler, question, machine)
    assert result["status"] == "insufficient_evidence" and result["steps"] == []


def test_different_machine_evidence(config):
    result = run_answer(
        config, question="Hydraulic pressure fluctuation", machine="PRESS-01"
    )
    assert result["status"] == "answered"
    assert {c["record_id"] for c in result["citations"]} == {"SOP-003"}


def test_revocation_excludes_cached_vectors(config):
    nodes = make_retriever(config.database_path, "CNC-01").retrieve("spindle vibration")
    with connect(config.database_path) as db:
        db.execute(
            "UPDATE knowledge_versions SET status='Revoked' WHERE machine_id='CNC-01' AND status='Approved'"
        )
    assert not valid_evidence(config.database_path, "CNC-01", nodes)

    def handler(request):
        pytest.fail("Revoked cached sources must not reach inference")

    assert run_answer(config, handler)["status"] == "insufficient_evidence"


def test_superseded_source_excluded(config):
    retriever = make_retriever(config.database_path, "CNC-01")
    retriever.retrieve("spindle vibration")
    with connect(config.database_path) as db:
        db.execute(
            "INSERT INTO knowledge_versions (id,record_id,revision,machine_id,title,symptom,content,kind,author,status,created_at) SELECT 'SOP-001-v2',record_id,2,machine_id,title,symptom,'New unreviewed version',kind,author,'Pending',created_at FROM knowledge_versions WHERE id='SOP-001-v1'"
        )
    assert all(
        n.node.metadata["record_id"] != "SOP-001"
        for n in retriever.retrieve("spindle vibration")
    )


def test_revoked_during_inference_discards_entire_answer(config):
    def handler(request):
        with connect(config.database_path) as db:
            db.execute(
                "UPDATE knowledge_versions SET status='Revoked' WHERE id='SOP-001-v1'"
            )
        return response_for(selection(request))

    with pytest.raises(RagFailure) as caught:
        run_answer(config, handler)
    assert caught.value.code == "evidence_changed" and caught.value.status == 409


@pytest.mark.parametrize(
    "kind", ["invented_id", "invented_quote", "empty_steps", "bad_json"]
)
def test_invalid_answer_never_displayed(config, kind):
    def handler(request):
        chosen = selection(request)
        if kind == "invented_id":
            chosen["steps"][0]["source_id"] = "PRIVATE-Pending-v1"
        if kind == "invented_quote":
            chosen["steps"][0]["passage_id"] = "invented-passage"
        if kind == "empty_steps":
            chosen["steps"] = []
        if kind == "bad_json":
            return httpx.Response(
                200,
                json={
                    "model": "test",
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": "Not JSON"},
                            "finish_reason": "stop",
                        }
                    ],
                },
            )
        return response_for(chosen)

    with pytest.raises(RagFailure) as caught:
        run_answer(config, handler)
    assert caught.value.status == 502


@pytest.mark.parametrize("failure", ["authentication", "timeout", "network", "empty"])
def test_provider_failures_have_no_fabricated_guidance(config, failure):
    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("test timeout", request=request)
        if failure == "network":
            raise httpx.ReadError("test network error", request=request)
        if failure == "authentication":
            return httpx.Response(401, json={"error": "private provider diagnostic"})
        return httpx.Response(200, json={"choices": []})

    with pytest.raises(RagFailure) as caught:
        run_answer(config, handler)
    assert caught.value.status in (503, 504)
    assert "private provider diagnostic" not in str(caught.value)


def test_endpoint_authentication_machine_scope_and_csrf(config):
    app = create_app(config)
    app.dependency_overrides[rag_service] = lambda: RagService(
        config.database_path, mocked_provider(), make_retriever
    )
    with TestClient(app) as client:
        payload = {
            "machine_id": "CNC-01",
            "question": "Spindle vibration after a tool change",
        }
        assert (
            client.post(
                "/api/v1/troubleshoot", json=payload, headers={"X-Shift-Request": "1"}
            ).status_code
            == 401
        )
        client.post(
            "/api/v1/auth/login",
            json={"username": "tech", "password": "test-rag-password"},
            headers={"X-Shift-Request": "1"},
        )
        assert client.post("/api/v1/troubleshoot", json=payload).status_code == 403
        result = client.post(
            "/api/v1/troubleshoot", json=payload, headers={"X-Shift-Request": "1"}
        )
        assert result.status_code == 200 and result.json()["status"] == "answered"
        payload["machine_id"] = "UNKNOWN"
        assert (
            client.post(
                "/api/v1/troubleshoot", json=payload, headers={"X-Shift-Request": "1"}
            ).status_code
            == 404
        )
        payload["machine_id"] = "CNC-02"
        assert (
            client.post(
                "/api/v1/troubleshoot", json=payload, headers={"X-Shift-Request": "1"}
            ).json()["status"]
            == "insufficient_evidence"
        )


def test_new_approval_is_indexed_on_next_query(config):
    assert (
        make_retriever(config.database_path, "CNC-02").retrieve("spindle vibration")
        == []
    )
    with connect(config.database_path) as db:
        db.execute(
            "UPDATE knowledge_versions SET status='Approved' WHERE id='SUB-005-v1'"
        )
    assert make_retriever(config.database_path, "CNC-02").retrieve("spindle vibration")


def test_question_machine_conflict_does_not_call_provider(config):
    def handler(request):
        pytest.fail("Conflicting scope must not call the model")

    result = run_answer(
        config, handler, question="CNC-02 spindle vibration", machine="CNC-01"
    )
    assert result["status"] == "insufficient_evidence"


def test_long_query_is_rejected_without_embedding_truncation(config):
    with pytest.raises(RagFailure) as caught:
        run_answer(config, question=("tool " * 241).strip())
    assert caught.value.status == 422


def test_no_partial_response_on_provider_semantic_abstention(config):
    result = run_answer(
        config, lambda request: response_for({"sufficient": False, "steps": []})
    )
    assert result["status"] == "insufficient_evidence" and not result["steps"]


def test_selected_passages_preserve_source_order(config):
    expected = []

    def handler(request):
        evidence = json.loads(json.loads(request.content)["messages"][1]["content"])["approved_evidence"]
        source = evidence[0]
        chosen = source["passages"][:3]
        expected.extend(p["text"] for p in chosen)
        return response_for({"sufficient": True, "steps": [
            {"source_id": source["source_id"], "passage_id": p["passage_id"]}
            for p in reversed(chosen)
        ]})

    result = run_answer(config, handler)
    assert [s["text"] for s in result["steps"]] == expected
