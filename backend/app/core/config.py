from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    database_url: str = "postgresql+psycopg://dealership:dealership@localhost:5432/dealership"
    jwt_secret: str = "change-me-in-development-only"
    jwt_access_token_minutes: int = Field(default=60, ge=1)
    allowed_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("allowed_cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
