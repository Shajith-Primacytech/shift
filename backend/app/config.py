from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SHIFT_", env_file=".env", extra="ignore"
    )
    environment: Literal["development", "test", "production"] = "development"
    # PostgreSQL requires explicit opt-in; SQLite remains the default.
    storage_backend: Literal["sqlite", "postgres"] = "sqlite"
    database_path: str = "data/shift.sqlite3"
    seed_synthetic: bool = True
    session_hours: int = 12
    speech_model_path: str = "data/speech/tiny.en"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            if origin == "*" or not origin.startswith(("http://", "https://")):
                raise ValueError("CORS requires explicit HTTP(S) origins")
            if origin.endswith("/"):
                raise ValueError("Origins must not have a trailing slash")
        return origins

    @model_validator(mode="after")
    def production_postgres(self):
        if self.environment == "production" and self.storage_backend == "postgres":
            from urllib.parse import urlsplit

            if self.seed_synthetic or not self.cors_origins:
                raise ValueError(
                    "Production PostgreSQL requires seed_synthetic=false and HTTPS origins"
                )
            for origin in self.cors_origins:
                url = urlsplit(origin)
                if (
                    url.scheme != "https"
                    or not url.hostname
                    or url.username
                    or url.password
                    or url.path
                    or url.query
                    or url.fragment
                    or url.hostname in ("localhost", "127.0.0.1", "::1")
                ):
                    raise ValueError(
                        "Production requires explicit HTTPS frontend origins"
                    )
        return self


class AMDSettings(BaseSettings):
    """Explicit AMD aliases; optional until the isolated adapter is invoked."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    api_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="AMD_API_KEY", exclude=True, repr=False
    )
    base_url: str = Field(
        default="https://developer.amd.com.cn/radeon/api/v1",
        validation_alias="AMD_BASE_URL",
        repr=False,
    )
    model: str = Field(
        default="DeepSeek-V4-Flash",
        validation_alias="AMD_MODEL",
        min_length=1,
        max_length=160,
    )
    connect_timeout: float = Field(
        default=5,
        gt=0,
        le=60,
        allow_inf_nan=False,
        validation_alias="AMD_CONNECT_TIMEOUT",
    )
    read_timeout: float = Field(
        default=45,
        gt=0,
        le=120,
        allow_inf_nan=False,
        validation_alias="AMD_READ_TIMEOUT",
    )
    overall_timeout: float = Field(
        default=55,
        gt=0,
        le=180,
        allow_inf_nan=False,
        validation_alias="AMD_OVERALL_TIMEOUT",
    )
    max_retries: int = Field(default=1, ge=0, le=2, validation_alias="AMD_MAX_RETRIES")

    @field_validator("base_url")
    @classmethod
    def verified_endpoint(cls, value: str) -> str:
        # Model changes require configuration only; credentials never follow a new host.
        value = value.rstrip("/")
        if value != "https://developer.amd.com.cn/radeon/api/v1":
            raise ValueError("Use the verified AMD HTTPS endpoint")
        return value

    @field_validator("model")
    @classmethod
    def model_identifier(cls, value: str) -> str:
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("Invalid model identifier")
        return value.strip()
