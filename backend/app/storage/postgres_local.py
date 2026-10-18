"""Explicit local synthetic bootstrap. Never reads .env or existing SQLite data.

Run only against a dedicated disposable loopback cluster/database. This is not
an importer, Supabase migration command, or production provisioning tool.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

from app.storage.backend import StorageUnavailable
from app.storage.postgres import local_connection_parameters

MIGRATION_DIR = Path(__file__).resolve().parents[2] / "postgres/supabase/migrations"


def bootstrap(conn, runtime_password):
    """Caller already validated a loopback DSN and owns this synthetic database."""
    from psycopg import sql
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb

    conn.row_factory = dict_row
    if (
        not conn.execute("SELECT current_database() AS name")
        .fetchone()["name"]
        .startswith(("shift_test_", "shift_dev_"))
    ):
        raise StorageUnavailable("Not a development database")
    with conn.transaction():
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended('shift:local-bootstrap', 0))"
        )
        for role in ("shift_owner", "shift_runtime"):
            existing = conn.execute(
                "SELECT rolcanlogin,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=%s",
                (role,),
            ).fetchone()
            if existing:
                if any(
                    existing[k]
                    for k in (
                        "rolsuper",
                        "rolbypassrls",
                        "rolcreatedb",
                        "rolcreaterole",
                    )
                ) or existing["rolcanlogin"] != (role == "shift_runtime"):
                    raise StorageUnavailable(
                        "Existing local development role is incompatible"
                    )
            elif role == "shift_owner":
                conn.execute(
                    "CREATE ROLE shift_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                )
            else:
                conn.execute(
                    sql.SQL(
                        "CREATE ROLE shift_runtime LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                    ).format(sql.Literal(runtime_password))
                )
        conn.execute("CREATE SCHEMA IF NOT EXISTS extensions")
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")
        extension = conn.execute(
            "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"
        ).fetchone()
        if extension["nspname"] != "extensions":
            raise StorageUnavailable("Local vector extension must be in extensions")
        conn.execute("GRANT USAGE ON SCHEMA extensions TO shift_owner,shift_runtime")
        conn.execute(
            "GRANT USAGE ON TYPE extensions.vector TO shift_owner,shift_runtime"
        )
        files = sorted(MIGRATION_DIR.glob("*.sql"))
        if len(files) != 1:
            raise StorageUnavailable("Unexpected Phase 2 migration set")
        migration = files[0]
        checksum = hashlib.sha256(migration.read_bytes()).hexdigest()
        if conn.execute("SELECT to_regnamespace('shift_private') AS schema").fetchone()[
            "schema"
        ]:
            rows = conn.execute(
                "SELECT version,checksum FROM shift_private.schema_migrations"
            ).fetchall()
            if rows != [{"version": migration.name, "checksum": checksum}]:
                raise StorageUnavailable(
                    "Local schema exists with a different migration ledger"
                )
        else:
            conn.execute(migration.read_text(), prepare=False)
            conn.execute(
                "INSERT INTO shift_private.schema_migrations (version,checksum) VALUES (%s,%s)",
                (migration.name, checksum),
            )
        # No shared Supabase roles are changed. PUBLIC has no schema/object access.
        for role in ("anon", "authenticated"):
            if conn.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)
            ).fetchone():
                if conn.execute(
                    "SELECT has_schema_privilege(%s, 'shift_private', 'USAGE') AS access",
                    (role,),
                ).fetchone()["access"]:
                    raise StorageUnavailable("Private schema is exposed to an API role")
        if conn.execute("SELECT 1 FROM shift_private.machines LIMIT 1").fetchone():
            return
        fixtures = json.loads(Path(__file__).with_name("synthetic.json").read_text())
        for m in fixtures["machines"]:
            conn.execute(
                "INSERT INTO shift_private.machines (id,data) VALUES (%s,%s)",
                (m["id"], Jsonb(m)),
            )
        for r in fixtures["knowledge"]:
            conn.execute(
                "INSERT INTO shift_private.knowledge_records (id,owner_id,created_at) VALUES (%s,NULL,%s)",
                (r["id"], r["date"]),
            )
            conn.execute(
                "INSERT INTO shift_private.knowledge_versions (id,record_id,revision,machine_id,title,symptom,content,kind,author,status,created_at) VALUES (%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s)",
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
                conn.execute(
                    "INSERT INTO shift_private.review_events (version_id,reviewer_name,previous_status,decision,note,created_at) VALUES (%s,%s,'Pending','Approved',%s,%s)",
                    (
                        r["id"] + "-v1",
                        r["reviewer"],
                        "Synthetic seed approval; not a real maintenance authorization.",
                        r["date"],
                    ),
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-synthetic", action="store_true", required=True)
    parser.parse_args()
    import psycopg

    try:
        params = local_connection_parameters(os.environ["SHIFT_PG_TEST_ADMIN_DSN"])
        password = os.environ["SHIFT_PG_TEST_RUNTIME_PASSWORD"]
        if not password:
            raise StorageUnavailable("A local runtime password is required")
        with psycopg.connect(**params, autocommit=True) as conn:
            bootstrap(conn, password)
    except (KeyError, StorageUnavailable, psycopg.Error):
        raise SystemExit(
            "Local PostgreSQL bootstrap failed; inspect the isolated test configuration privately"
        ) from None
    print(
        "Local synthetic PostgreSQL schema prepared. No SQLite database was accessed."
    )


if __name__ == "__main__":
    main()
