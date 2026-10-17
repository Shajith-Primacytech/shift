"""Local passwords and opaque, revocable sessions; no client-supplied roles."""

import hashlib
import hmac
import secrets
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 256:
        raise ValueError("Password must contain 12–256 characters")
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=16384, r=8, p=1
    ).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    _, salt, expected = stored.split("$")
    actual = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=16384, r=8, p=1
    ).hex()
    return hmac.compare_digest(actual, expected)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(db, username: str, name: str, role: str, password: str):
    if (
        role not in ("technician", "supervisor")
        or not username.strip()
        or not name.strip()
    ):
        raise ValueError("Username, name and a valid role are required")
    db.execute(
        "INSERT INTO users VALUES (?,?,?,?,?,?)",
        (
            secrets.token_hex(16),
            username.strip().lower(),
            name.strip(),
            role,
            hash_password(password),
            now(),
        ),
    )
