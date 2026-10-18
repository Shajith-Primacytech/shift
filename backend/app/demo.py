"""Provision synthetic judge accounts without putting passwords in source or logs."""

import argparse
import os
import secrets
from pathlib import Path

from dotenv import dotenv_values

from app.storage.database import connect, initialize
from app.storage.security import create_user, verify_password

ACCOUNTS = (
    ("judge-tech", "Hackathon Technician", "technician", "SHIFT_DEMO_TECHNICIAN_PASSWORD"),
    ("judge-supervisor", "Hackathon Supervisor", "supervisor", "SHIFT_DEMO_SUPERVISOR_PASSWORD"),
)


def provision(database_path: str, credentials_file: str):
    path = Path(credentials_file)
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise ValueError("Judge credential file must have mode 0600")
        credentials = dotenv_values(path)
        if any(not credentials.get(key) for *_, key in ACCOUNTS):
            raise ValueError("Judge credential file is incomplete")
    else:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        credentials = {key: secrets.token_urlsafe(24) for *_, key in ACCOUNTS}
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            output.write("# Private judge access. Never commit or include in public artifacts.\n")
            for username, _, _, key in ACCOUNTS:
                output.write(f"# Username: {username}\n{key}={credentials[key]}\n")
    initialize(database_path, seed=True)
    with connect(database_path) as db:
        for username, name, role, key in ACCOUNTS:
            existing = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if existing:
                if existing["role"] != role or not verify_password(credentials[key], existing["password_hash"]):
                    raise ValueError("An existing judge account differs; no password or role was changed")
            else:
                create_user(db, username, name, role, credentials[key])
    return {"accounts": [a[0] for a in ACCOUNTS], "synthetic": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-path", required=True)
    parser.add_argument("--credentials-file", required=True)
    args = parser.parse_args()
    provision(args.database_path, args.credentials_file)
    print("Synthetic technician and supervisor ready. Passwords are in the private credentials file only.")


if __name__ == "__main__":
    main()
