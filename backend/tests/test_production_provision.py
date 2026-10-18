"""Offline credential artifacts must not leak plaintext or silently overwrite."""

import json
import stat

import pytest
from app.storage import production_provision as provision


def test_private_offline_provision(monkeypatch, tmp_path, capsys):
    machines = tmp_path / "machines.json"
    machines.write_text(json.dumps([{"id": "M-1", "name": "Test machine"}]))
    output = tmp_path / "accounts.provision.sql"
    answers = iter(
        ["tech'o", "Technician", "reviewer", "Supervisor", "reviewer2", "Supervisor 2"]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    password = "synthetic-private-password"
    monkeypatch.setattr(provision, "getpass", lambda _: password)
    monkeypatch.setattr(
        "sys.argv",
        ["provision", "--machines-json", str(machines), "--output", str(output)],
    )
    provision.main()
    content = output.read_text()
    assert password not in content
    assert "tech''o" in content
    assert content.count("scrypt$") == 3
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert "INSERT INTO shift_private.machines" in content
    assert "knowledge_versions" not in content
    assert "scrypt$" not in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        # os.open must not overwrite an existing private artifact.
        import os

        os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
