"""Backend selection. Never imports PostgreSQL dependencies for the local demo."""


class StorageUnavailable(Exception):
    """Safe boundary for driver errors (no DSN, SQL parameters or diagnostics)."""


def is_postgres(value):
    return getattr(value, "backend", None) == "postgres"


def open_postgres(settings):
    from app.storage.postgres import PostgresSettings, PostgresStore

    try:
        config = PostgresSettings()
    except ValueError:
        raise StorageUnavailable("Invalid PostgreSQL configuration") from None
    return PostgresStore(config, production=settings.environment == "production")
