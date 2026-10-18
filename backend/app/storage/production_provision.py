"""Prepare a private account/machine SQL artifact OFFLINE. Never connects to a DB."""

import argparse
import json
import os
import secrets
from getpass import getpass
from pathlib import Path

from app.storage.security import hash_password, now


def account_sql(username, name, role, password):
    from psycopg import sql

    if (
        not username.strip()
        or len(username) > 100
        or not name.strip()
        or role not in ("technician", "supervisor")
    ):
        raise ValueError("Invalid account details")
    return (
        sql.SQL(
            "INSERT INTO shift_private.users(id,username,name,role,password_hash,created_at) VALUES ({});\n"
        )
        .format(
            sql.SQL(",").join(
                map(
                    sql.Literal,
                    (
                        secrets.token_hex(16),
                        username.strip().lower(),
                        name.strip(),
                        role,
                        hash_password(password),
                        now(),
                    ),
                )
            )
        )
        .as_string()
    )


def main():
    from psycopg import sql
    from psycopg.types.json import Jsonb

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--machines-json",
        required=True,
        type=Path,
        help="JSON list of reviewed machine objects with unique id",
    )
    args = parser.parse_args()
    machines = json.loads(args.machines_json.read_text())
    if (
        not isinstance(machines, list)
        or not machines
        or any(
            not isinstance(m, dict) or not isinstance(m.get("id"), str) or not m["id"]
            for m in machines
        )
    ):
        parser.error("Review a nonempty machine list with explicit IDs")
    if len({m["id"] for m in machines}) != len(machines):
        parser.error("Duplicate machine IDs")
    statements = [
        "BEGIN;\nGRANT shift_owner TO postgres;\nSET LOCAL ROLE shift_owner;\n"
    ]
    usernames = set()
    for role in ("technician", "supervisor", "supervisor"):
        username = input(f"{role} username: ")
        if username.strip().lower() in usernames:
            parser.error("Use distinct account usernames")
        usernames.add(username.strip().lower())
        name = input("Display name: ")
        password = getpass("Unique password (12–256 characters): ")
        if password != getpass("Confirm password: "):
            parser.error("Passwords do not match")
        statements.append(account_sql(username, name, role, password))
    for machine in machines:
        statements.append(
            sql.SQL("INSERT INTO shift_private.machines(id,data) VALUES ({},{});\n")
            .format(sql.Literal(machine["id"]), sql.Literal(Jsonb(machine)))
            .as_string()
        )
    statements.append("RESET ROLE;\nREVOKE shift_owner FROM postgres;\nCOMMIT;\n")
    # Refuse overwrite/symlink and ensure hashes are private even with a loose umask.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write("".join(statements))
    print(
        "Private SQL prepared offline. Review privately; applying it requires deployment approval."
    )


if __name__ == "__main__":
    main()
