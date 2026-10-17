import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(
            Settings(
                environment="test",
                database_path=str(tmp_path / "test.sqlite3"),
                _env_file=None,
            )
        )
    ) as client:
        yield client


def test_health_without_external_services(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "shift-api",
        "version": "0.2.0",
        "mode": "storage",
    }


def test_allowed_browser_origin(client):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_untrusted_browser_origin(client):
    response = client.get(
        "/api/v1/health", headers={"Origin": "https://untrusted.example"}
    )
    assert "access-control-allow-origin" not in response.headers


def test_preflight(client):
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_environment_settings(monkeypatch):
    monkeypatch.setenv("SHIFT_CORS_ORIGINS", '["http://localhost:4000"]')
    assert Settings(_env_file=None).cors_origins == ["http://localhost:4000"]


def test_wildcard_origin_rejected():
    with pytest.raises(ValidationError):
        Settings(cors_origins=["*"], _env_file=None)


def test_unknown_route(client):
    assert client.get("/api/v1/missing").status_code == 404
