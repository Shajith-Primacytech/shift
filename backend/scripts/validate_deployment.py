"""Own two disposable local PG17 clusters, run tests, stop both. No hosted access.

Requires an existing PG17 installation with vector installed, OpenSSL CLI, and
backend dev/voice/postgres extras. Credentials are ephemeral and never printed.
"""

import argparse
import os
import secrets
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--openssl", default="openssl")
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(prefix="shift-deploy-test-", dir="/tmp"))
    password = secrets.token_urlsafe(32)
    started = []
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SHIFT_", "PG", "AMD_"))
    }

    def run(cmd, **kw):
        return subprocess.run([str(x) for x in cmd], check=True, env=env, **kw)

    def port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    local_port, production_port = port(), port()
    try:
        for name, user, number in (
            ("local", "postgres", local_port),
            ("production", "test_control", production_port),
        ):
            cluster = work / name
            with (work / (name + "-init.log")).open("w") as log:
                run(
                    [
                        args.pg_bin / "initdb",
                        "-D",
                        cluster,
                        "-U",
                        user,
                        "--auth-local=trust",
                        "--auth-host=scram-sha-256",
                    ],
                    stdout=log,
                    stderr=log,
                )
            options = f"-h 127.0.0.1 -p {number} -k {work}"
            if name == "production":
                run(
                    [
                        args.openssl,
                        "req",
                        "-new",
                        "-x509",
                        "-nodes",
                        "-days",
                        "1",
                        "-subj",
                        "/CN=db.shift.test",
                        "-addext",
                        "subjectAltName=DNS:db.shift.test",
                        "-keyout",
                        cluster / "server.key",
                        "-out",
                        cluster / "server.crt",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                os.chmod(cluster / "server.key", 0o600)
                options += " -c ssl=on"
            run(
                [
                    args.pg_bin / "pg_ctl",
                    "-D",
                    cluster,
                    "-l",
                    work / (name + "-server.log"),
                    "-o",
                    options,
                    "start",
                ],
                stdout=subprocess.DEVNULL,
            )
            started.append(cluster)
            with psycopg.connect(
                host=str(work),
                port=number,
                user=user,
                dbname="postgres",
                autocommit=True,
            ) as conn:
                if name == "local":
                    conn.execute(
                        sql.SQL("ALTER ROLE postgres PASSWORD {}").format(
                            sql.Literal(password)
                        )
                    )
                    conn.execute("CREATE DATABASE shift_test_control")
                else:
                    conn.execute(
                        sql.SQL("ALTER ROLE test_control PASSWORD {}").format(
                            sql.Literal(password)
                        )
                    )
                    conn.execute(
                        sql.SQL(
                            "CREATE ROLE postgres LOGIN CREATEDB CREATEROLE PASSWORD {}"
                        ).format(sql.Literal(password))
                    )
                    conn.execute("CREATE DATABASE shift_test_production OWNER postgres")
        test_env = dict(
            env,
            SHIFT_PG_TEST_ADMIN_DSN=make_conninfo(
                host="127.0.0.1",
                port=local_port,
                user="postgres",
                password=password,
                dbname="shift_test_control",
            ),
            SHIFT_PG_TEST_RUNTIME_PASSWORD=password,
            SHIFT_PG_PRODUCTION_TEST_ADMIN_DSN=make_conninfo(
                host="127.0.0.1",
                port=production_port,
                user="test_control",
                password=password,
                dbname="shift_test_production",
            ),
            SHIFT_PG_PRODUCTION_TEST_PASSWORD=password,
            SHIFT_PG_PRODUCTION_TEST_CA=str(work / "production/server.crt"),
            PYTHONPATH=str(backend),
        )
        result = subprocess.run(
            check=False,
            args=[
                sys.executable,
                "-m",
                "pytest",
                str(backend / "tests"),
                "-q",
                "-o",
                f"cache_dir={work}/pytest-cache",
            ],
            cwd=work,
            env=test_env,
        )
        print("Validation artifacts:", work)
        return result.returncode
    finally:
        for cluster in reversed(started):
            run(
                [args.pg_bin / "pg_ctl", "-D", cluster, "stop", "-m", "fast"],
                stdout=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    raise SystemExit(main())
