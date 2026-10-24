from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    database_url: str = "postgresql+psycopg://dealership:dealership@localhost:5432/dealership"
    # Required: anyone who knows this key can forge a token for any account.
    jwt_secret: str = ""
    jwt_access_token_minutes: int = Field(default=60, ge=1)
    initial_admin_email: str = ""
    initial_admin_password: str = ""
    # NoDecode hands the raw comma-separated string to split_origins instead of JSON-decoding it.
    allowed_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    @field_validator("jwt_secret")
    @classmethod
    def require_strong_jwt_secret(cls, value: str) -> str:
        if value == "change-me-in-development-only" or len(value) < 32:
            raise ValueError(
                "JWT_SECRET must be set to a random value of at least 32 characters, "
                "for example the output of `openssl rand -hex 32`."
            )
        return value

    @field_validator("allowed_cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
