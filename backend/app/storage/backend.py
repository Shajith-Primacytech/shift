"""Backend selection. Never imports PostgreSQL dependencies for the local demo."""


class StorageUnavailable(Exception):
    """Safe boundary for driver errors (no DSN, SQL parameters or diagnostics)."""


def is_postgres(value):
    return getattr(value, "backend", None) == "postgres"


def open_postgres(settings):
    # Keep Phase 2 away from production even if a selector is set accidentally.
    if settings.environment == "production":
        raise StorageUnavailable("PostgreSQL Phase 2 is local development only")
    from app.storage.postgres import PostgresSettings, PostgresStore

    return PostgresStore(PostgresSettings())
