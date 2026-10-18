"""Configuration safety tests without a database or private environment."""

import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.storage.backend import StorageUnavailable, open_postgres


def test_sqlite_default_does_not_import_postgres_driver(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.main import create_app; from app.config import Settings; import sys; assert Settings(_env_file=None).storage_backend == 'sqlite'; assert 'psycopg' not in sys.modules",
        ],
        cwd=tmp_path,
        env={"PYTHONPATH": str(backend)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_postgres_production_path_is_disabled_before_connecting():
    with pytest.raises(StorageUnavailable, match="local development only"):
        open_postgres(
            Settings(
                _env_file=None, environment="production", storage_backend="postgres"
            )
        )


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://user:synthetic@remote.invalid/shift_test_fixture",
        "host=127.0.0.1 dbname=postgres user=user password=synthetic",
        "host=127.0.0.1 hostaddr=203.0.113.1 dbname=shift_test_fixture user=user password=synthetic",
        "service=untrusted",
        "host=127.0.0.1 dbname=shift_test_fixture user=user password=synthetic options=-csearch_path=public",
        "host=127.0.0.1 dbname=shift_test_fixture user=user password=synthetic passfile=/private/path",
    ],
)
def test_remote_and_implicit_targets_are_rejected(dsn):
    pytest.importorskip("psycopg")
    from app.storage.postgres import local_connection_parameters

    with pytest.raises(StorageUnavailable):
        local_connection_parameters(dsn)


def test_postgres_credentials_never_load_from_dotenv(monkeypatch, tmp_path):
    from app.storage.postgres import PostgresSettings
    from pydantic import ValidationError

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SHIFT_POSTGRES_DSN", raising=False)
    (tmp_path / ".env").write_text("SHIFT_POSTGRES_DSN=synthetic-should-not-be-read\n")
    with pytest.raises(ValidationError):
        PostgresSettings()


@pytest.mark.parametrize(
    "value", [[1.0] * 383, [0.0] * 384, [float("inf")] * 384, [float("nan")] * 384]
)
def test_vectors_reject_invalid_values(value):
    from app.rag.postgres import vector384

    with pytest.raises(ValueError, match="Invalid embedding"):
        vector384(value)
