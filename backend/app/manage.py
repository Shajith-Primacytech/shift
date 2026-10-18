"""Local administrative CLI. Passwords are prompted, never command arguments."""

import argparse
from getpass import getpass

from app.config import Settings
from app.storage.database import connect, initialize
from app.storage.security import create_user


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db", "create-user"])
    parser.add_argument("--username")
    parser.add_argument("--name")
    parser.add_argument("--role", choices=["technician", "supervisor"])
    args = parser.parse_args()
    settings = Settings()
    if settings.storage_backend != "sqlite":
        parser.error(
            "Phase 2 PostgreSQL provisioning uses the explicit local synthetic bootstrap; SQLite was not opened"
        )
    initialize(settings.database_path, settings.seed_synthetic)
    if args.command == "create-user":
        if not all((args.username, args.name, args.role)):
            parser.error("--username, --name and --role are required")
        password = getpass("Password (12+ characters): ")
        if password != getpass("Confirm password: "):
            parser.error("Passwords do not match")
        with connect(settings.database_path) as db:
            create_user(db, args.username, args.name, args.role, password)
        print("User created. Sign in through the SHIFT frontend.")
    else:
        print("Database migrations applied.")


if __name__ == "__main__":
    main()
