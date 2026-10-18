import pytest
from app.demo import provision
from app.storage.database import connect
from app.storage.security import verify_password
from dotenv import dotenv_values


def test_judge_accounts_are_private_idempotent_and_do_not_change_roles(tmp_path):
    database = str(tmp_path / "judge.sqlite3")
    credentials = tmp_path / "judge.env"
    provision(database, str(credentials))
    assert credentials.stat().st_mode & 0o777 == 0o600
    values = dotenv_values(credentials)
    provision(database, str(credentials))
    with connect(database) as db:
        tech = db.execute("SELECT * FROM users WHERE username='judge-tech'").fetchone()
        assert tech["role"] == "technician"
        assert verify_password(values["SHIFT_DEMO_TECHNICIAN_PASSWORD"], tech["password_hash"])
        assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 2
        assert db.execute("SELECT count(*) FROM machines").fetchone()[0] > 0
        db.execute("UPDATE users SET role='technician' WHERE username='judge-supervisor'")
    with pytest.raises(ValueError, match="no password or role was changed"):
        provision(database, str(credentials))


def test_judge_credentials_refuse_world_readable_file(tmp_path):
    path = tmp_path / "unsafe.env"
    path.write_text("private")
    path.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        provision(str(tmp_path / "judge.sqlite3"), str(path))


def test_production_judge_login_uses_secure_cookie_and_permissions(tmp_path):
    from app.config import Settings
    from app.main import create_app
    from fastapi.testclient import TestClient
    database = str(tmp_path / "production.sqlite3")
    credentials = tmp_path / "judges.env"
    provision(database, str(credentials))
    values = dotenv_values(credentials)
    app = create_app(Settings(_env_file=None, environment="production", database_path=database))
    with TestClient(app, base_url="https://demo.shift.test", headers={"X-Shift-Request": "1"}) as client:
        response = client.post("/api/v1/auth/login", json={"username":"judge-tech", "password":values["SHIFT_DEMO_TECHNICIAN_PASSWORD"]})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
        assert client.get("/api/v1/auth/me").json()["role"] == "technician"
        assert client.post("/api/v1/submissions/nonexistent/review", json={"versionId":"none", "decision":"Approved", "note":"Synthetic test"}).status_code == 403
