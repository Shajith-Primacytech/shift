"""SQLite source of truth. Ordered SQL migrations run transactionally and once."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SEED = Path(__file__).with_name("synthetic.json")


@contextmanager
def connect(path: str):
    db = sqlite3.connect(path, timeout=10, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def initialize(path: str, seed: bool = True):
    Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_WRONLY, 0o600)
    os.close(fd)
    os.chmod(path, 0o600)
    with connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)"
        )
        db.commit()
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            db.execute("BEGIN IMMEDIATE")
            if not db.execute(
                "SELECT 1 FROM schema_migrations WHERE version=?", (migration.name,)
            ).fetchone():
                for statement in migration.read_text().split(";"):
                    if statement.strip():
                        db.execute(statement)
                db.execute(
                    "INSERT INTO schema_migrations VALUES (?)", (migration.name,)
                )
            db.commit()
        if seed:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM machines LIMIT 1").fetchone():
                return
            fixtures = json.loads(SEED.read_text())
            for machine in fixtures["machines"]:
                db.execute(
                    "INSERT INTO machines VALUES (?,?)",
                    (machine["id"], json.dumps(machine)),
                )
            for r in fixtures["knowledge"]:
                db.execute(
                    "INSERT INTO knowledge_records VALUES (?,NULL,?)",
                    (r["id"], r["date"]),
                )
                db.execute(
                    "INSERT INTO knowledge_versions (id,record_id,revision,machine_id,title,symptom,content,kind,author,status,created_at) VALUES (?,?,1,?,?,?,?,?,?,?,?)",
                    (
                        r["id"] + "-v1",
                        r["id"],
                        r["machineId"],
                        r["title"],
                        r["symptom"],
                        r["content"],
                        r["kind"],
                        r["author"],
                        r["status"],
                        r["date"],
                    ),
                )
                if r["status"] == "Approved":
                    db.execute(
                        "INSERT INTO review_events (version_id,reviewer_name,previous_status,decision,note,created_at) VALUES (?,?,?,?,?,?)",
                        (
                            r["id"] + "-v1",
                            r["reviewer"],
                            "Pending",
                            "Approved",
                            "Synthetic seed approval; not a real maintenance authorization.",
                            r["date"],
                        ),
                    )
