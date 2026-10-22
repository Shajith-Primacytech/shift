"""Offline configuration and failure boundaries; no hosted project access."""

from pathlib import Path

import pytest
from app.config import Settings
from app.storage.backend import StorageUnavailable
from app.storage.postgres import PostgresSettings, connection_parameters
from pydantic import ValidationError


def config(ca, **kw):
    return PostgresSettings(
        _env_file=None,
        dsn="host=db.shift.test port=5432 dbname=postgres user=shift_runtime password=synthetic sslmode=verify-full",
        mode="direct",
        expected_host="db.shift.test",
        sslrootcert=str(ca),
        **kw,
    )


@pytest.fixture
def ca(monkeypatch):
    import os

    import certifi

    for key in os.environ:
        if key.startswith("PG"):
            monkeypatch.delenv(key)
    return Path(certifi.where())


def test_verified_parameters(ca):
    params = connection_parameters(config(ca), production=True)
    assert params["sslmode"] == "verify-full"
    assert params["sslrootcert"] == str(ca)
    assert params["passfile"] == "/dev/null"
    assert params["options"] == ""
    assert params["ssl_min_protocol_version"] == "TLSv1.2"


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "local"},
        {"expected_host": "other.test"},
        {"sslrootcert": "/missing/ca"},
        {"dsn": "service=untrusted"},
        *[
            {
                "dsn": "host=db.shift.test port=5432 dbname=postgres user=shift_runtime password=synthetic sslmode="
                + mode
            }
            for mode in ("disable", "prefer", "require", "verify-ca")
        ],
        *[
            {
                "dsn": "host=db.shift.test port=5432 dbname=postgres user=shift_runtime password=synthetic sslmode=verify-full "
                + extra
            }
            for extra in (
                "hostaddr=127.0.0.1",
                "options=-crole=postgres",
                "passfile=/tmp/pass",
                "service=x",
                "user=postgres",
                "port=6543",
            )
        ],
    ],
)
def test_unsafe_remote_config_is_rejected(ca, change):
    cfg = config(ca).model_copy(update=change)
    if "dsn" in change:
        from pydantic import SecretStr

        cfg.dsn = SecretStr(change["dsn"])
    with pytest.raises(StorageUnavailable):
        connection_parameters(cfg, production=True)


def test_ambient_libpq_is_rejected(ca, monkeypatch):
    monkeypatch.setenv("PGOPTIONS", "-c role=postgres")
    with pytest.raises(StorageUnavailable):
        connection_parameters(config(ca), production=True)


def test_session_role(ca):
    from pydantic import SecretStr

    cfg = config(ca).model_copy(
        update={
            "mode": "session",
            "dsn": SecretStr(
                "host=db.shift.test port=5432 dbname=postgres user=shift_runtime.projectref password=synthetic sslmode=verify-full"
            ),
        }
    )
    assert (
        connection_parameters(cfg, production=True)["user"]
        == "shift_runtime.projectref"
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"seed_synthetic": False},
        {"seed_synthetic": False, "cors_origins": []},
        {
            "seed_synthetic": False,
            "cors_origins": ["https://user:pass@shift.example.com"],
        },
        {"seed_synthetic": False, "cors_origins": ["https://shift.example.com/path"]},
    ],
)
def test_production_requires_explicit_safe_settings(overrides):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            storage_backend="postgres",
            **overrides,
        )


def test_sqlite_settings_unchanged():
    assert Settings(_env_file=None).storage_backend == "sqlite"
    assert (
        Settings(_env_file=None, environment="production").storage_backend == "sqlite"
    )


def test_failure_is_redacted_and_no_sqlite_fallback():
    from app.storage.postgres import PostgresStore

    class DriverError(Exception):
        pass

    class BrokenPool:
        def connection(self):
            raise DriverError("secret-password raw SQL parameter")

    store = PostgresStore.__new__(PostgresStore)
    store.pool, store._driver_error = BrokenPool(), DriverError
    with (
        pytest.raises(StorageUnavailable, match="^PostgreSQL operation failed$"),
        store.connection(),
    ):
        pytest.fail("must not yield a fallback connection")


def test_readiness_reports_database_failure_without_secrets():
    from app.main import create_app
    from fastapi.testclient import TestClient

    app = create_app(Settings(_env_file=None, storage_backend="postgres"))

    class Store:
        def connection(self):
            raise StorageUnavailable("private-dsn")

    app.state.storage = Store()
    # No lifespan: this deliberately tests the HTTP exception boundary alone.
    response = TestClient(app).get("/api/v1/ready")
    assert response.status_code == 503
    assert "private-dsn" not in response.text


def test_render_contract(monkeypatch):
    import importlib.util

    import yaml

    root = Path(__file__).resolve().parents[2]
    data = yaml.safe_load((root / "render.yaml").read_text())["services"][0]
    assert data["autoDeployTrigger"] == "off"
    assert data["healthCheckPath"] == "/api/v1/ready"
    spec = importlib.util.spec_from_file_location(
        "deploy_start", root / "backend/deploy_start.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("PORT", "12345")
    assert module.command()[module.command().index("--port") + 1] == "12345"
    assert module.command()[module.command().index("--workers") + 1] == "1"

    dockerfile = (root / "backend/Dockerfile.hackathon").read_text()
    assert "LLAMA_INDEX_CACHE_DIR=/tmp/llama_index" in dockerfile
    assert "chmod -R a+rX /opt/models" in dockerfile
