"""Runs only in a separately supplied disposable loopback deployment cluster.

The admin must be a synthetic superuser OTHER than postgres, and the fresh
postgres role must have CREATEDB/CREATEROLE but NOT SUPERUSER. Roles are cluster
wide: never share this cluster with local bootstrap tests or other applications.
"""

import os
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
from app.storage.postgres import local_connection_parameters
from psycopg import sql
from psycopg.rows import dict_row


@pytest.fixture(scope="module")
def deployed():
    dsn = os.environ.get("SHIFT_PG_PRODUCTION_TEST_ADMIN_DSN")
    if not dsn:
        pytest.skip("separate disposable deployment test cluster not configured")
    params = local_connection_parameters(dsn)
    assert params["user"] != "postgres"
    with psycopg.connect(**params, autocommit=True, row_factory=dict_row) as admin:
        assert not admin.execute(
            "SELECT rolsuper FROM pg_roles WHERE rolname='postgres'"
        ).fetchone()["rolsuper"]
        assert not admin.execute(
            "SELECT 1 FROM pg_roles WHERE rolname IN ('shift_owner','shift_runtime')"
        ).fetchone()
        for role in ("anon", "authenticated", "service_role", "authenticator"):
            admin.execute(
                sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role))
            )
        admin.execute("CREATE SCHEMA extensions")
        admin.execute("CREATE EXTENSION vector WITH SCHEMA extensions")
        admin.execute("GRANT USAGE ON SCHEMA extensions TO postgres WITH GRANT OPTION")
        admin.execute(
            "GRANT USAGE ON TYPE extensions.vector TO postgres WITH GRANT OPTION"
        )
        admin.execute("CREATE SCHEMA shift_private AUTHORIZATION postgres")
        # Previously empty schema with accidental API grants must be secured.
        admin.execute("GRANT USAGE ON SCHEMA shift_private TO anon,authenticated")
        migration = next(
            (
                Path(__file__).parents[1] / "postgres/production/supabase/migrations"
            ).glob("*.sql")
        )
        migration_params = dict(
            params,
            user="postgres",
            password=os.environ["SHIFT_PG_PRODUCTION_TEST_PASSWORD"],
        )
        with psycopg.connect(**migration_params, autocommit=True) as conn:
            conn.execute(migration.read_text(), prepare=False)
        admin.execute(
            sql.SQL("ALTER ROLE shift_runtime LOGIN PASSWORD {}").format(
                sql.Literal(os.environ["SHIFT_PG_PRODUCTION_TEST_PASSWORD"])
            )
        )

        class PrivateFixture(tuple):
            def __repr__(self):
                return "<synthetic deployment fixture; credentials redacted>"

        yield PrivateFixture(
            (
                admin,
                dict(
                    params,
                    user="shift_runtime",
                    password=os.environ["SHIFT_PG_PRODUCTION_TEST_PASSWORD"],
                ),
                migration,
                migration_params,
            )
        )


def test_production_migration_rls_and_grants(deployed):
    admin, runtime, _, _ = deployed
    tables = admin.execute(
        "SELECT c.relname,c.relrowsecurity,pg_get_userbyid(c.relowner) AS owner FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='shift_private' AND c.relkind='r'"
    ).fetchall()
    assert len(tables) == 15
    assert all(t["relrowsecurity"] and t["owner"] == "shift_owner" for t in tables)
    assert not admin.execute(
        "SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid WHERE r.rolname='shift_owner' AND member=(SELECT oid FROM pg_roles WHERE rolname='postgres') AND (inherit_option OR set_option)"
    ).fetchone()
    with psycopg.connect(**runtime, autocommit=True) as conn:
        conn.execute(
            "SELECT vector::extensions.vector(384) FROM shift_private.chunk_embeddings LIMIT 0"
        )
        conn.execute("SELECT * FROM shift_private.users")
        for statement in (
            "INSERT INTO shift_private.users VALUES ('x','x','x','supervisor','x','x')",
            "UPDATE shift_private.review_events SET note='tampered'",
            "DELETE FROM shift_private.review_events",
            "TRUNCATE shift_private.sessions",
            "UPDATE shift_private.knowledge_versions SET content='tampered'",
            "DELETE FROM shift_private.source_documents",
            "CREATE TABLE shift_private.evil(id int)",
            "SET ROLE shift_owner",
            "SELECT * FROM shift_private.schema_migrations",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
        assert (
            conn.execute("SELECT count(*) FROM shift_private.machines").fetchone()[0]
            == 0
        )
    for role in ("anon", "authenticated", "service_role", "authenticator"):
        assert not admin.execute(
            "SELECT has_schema_privilege(%s,'shift_private','USAGE') AS allowed",
            (role,),
        ).fetchone()["allowed"]


def test_reapply_refuses_without_modification(deployed):
    admin, _, migration, migration_params = deployed
    with psycopg.connect(**migration_params, autocommit=True) as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="already exist"):
            conn.execute(migration.read_text(), prepare=False)
        conn.execute("ROLLBACK")
    assert (
        admin.execute(
            "SELECT count(*) AS n FROM shift_private.schema_migrations"
        ).fetchone()["n"]
        == 1
    )


def test_tls_certificate_and_hostname_verification(deployed):
    _, runtime, _, _ = deployed
    cert = os.environ["SHIFT_PG_PRODUCTION_TEST_CA"]
    params = dict(
        runtime, host="db.shift.test", sslmode="verify-full", sslrootcert=cert
    )
    # The test-only loopback address supplies DNS without changing /etc/hosts.
    with psycopg.connect(**params) as conn:
        assert conn.info.pgconn.ssl_in_use
    import certifi

    for change in (
        {"host": "wrong.shift.test"},
        {"sslrootcert": cert + ".missing"},
        {"sslrootcert": certifi.where()},
    ):
        with pytest.raises(psycopg.OperationalError):
            psycopg.connect(**dict(params, **change))
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(**dict(params, password="wrong-synthetic-password"))
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(**dict(params, port="55441", connect_timeout=1))


def test_production_store_startup_and_permission_drift(deployed, monkeypatch):
    from app.storage.backend import StorageUnavailable
    from app.storage.postgres import (
        PostgresSettings,
        PostgresStore,
        connection_parameters,
    )

    admin, runtime, _, _ = deployed
    cert = os.environ["SHIFT_PG_PRODUCTION_TEST_CA"]
    cfg = PostgresSettings(
        _env_file=None,
        mode="direct",
        expected_host="db.shift.test",
        sslrootcert=cert,
        dsn="host=db.shift.test port=5432 dbname=shift_test_production user=shift_runtime password="
        + runtime["password"]
        + " sslmode=verify-full",
    )
    original = connection_parameters

    # Route ONLY the socket to this test cluster; keep real verify-full and role checks.
    def route(config, **kwargs):
        return dict(
            original(config, **kwargs), hostaddr="127.0.0.1", port=runtime["port"]
        )

    monkeypatch.setattr("app.storage.postgres.connection_parameters", route)
    store = PostgresStore(cfg, production=True)
    try:
        store.validate()
        admin.execute("GRANT DELETE ON shift_private.review_events TO shift_runtime")
        try:
            with pytest.raises(StorageUnavailable, match="privileges differ"):
                store.validate()
        finally:
            admin.execute(
                "REVOKE DELETE ON shift_private.review_events FROM shift_runtime"
            )
        admin.execute("GRANT CREATE ON SCHEMA public TO shift_runtime")
        try:
            with pytest.raises(StorageUnavailable, match="create database objects"):
                store.validate()
        finally:
            admin.execute("REVOKE CREATE ON SCHEMA public FROM shift_runtime")
        admin.execute("ALTER TABLE shift_private.users DISABLE ROW LEVEL SECURITY")
        try:
            with pytest.raises(StorageUnavailable, match="RLS"):
                store.validate()
        finally:
            admin.execute("ALTER TABLE shift_private.users ENABLE ROW LEVEL SECURITY")
    finally:
        store.close()
