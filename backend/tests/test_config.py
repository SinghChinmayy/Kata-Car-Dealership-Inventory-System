from pathlib import Path
from typing import Optional

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://localhost:5173", ["http://localhost:5173"]),
        (
            "http://localhost:5173, https://dealership.example.com",
            ["http://localhost:5173", "https://dealership.example.com"],
        ),
    ],
)
def test_cors_origins_accept_the_documented_comma_separated_format(
    tmp_path: Path, monkeypatch, raw: str, expected: list[str]
) -> None:
    """The .env.example format must load from both a .env file and the environment."""
    monkeypatch.delenv("ALLOWED_CORS_ORIGINS", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"ALLOWED_CORS_ORIGINS={raw}\n")

    from_file = Settings(_env_file=env_file)
    monkeypatch.setenv("ALLOWED_CORS_ORIGINS", raw)
    from_environment = Settings(_env_file=None)

    assert from_file.allowed_cors_origins == expected
    assert from_environment.allowed_cors_origins == expected


def test_example_env_file_loads(monkeypatch) -> None:
    """Copying .env.example to .env, as the README instructs, yields valid settings."""
    for name in ("DATABASE_URL", "JWT_SECRET", "ALLOWED_CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    example = Path(__file__).resolve().parents[2] / ".env.example"

    settings = Settings(_env_file=example)

    assert settings.allowed_cors_origins == ["http://localhost:5173"]


@pytest.mark.parametrize(
    "secret",
    [None, "", "change-me-in-development-only", "x" * 31],
    ids=["missing", "blank", "documented-placeholder", "31-chars"],
)
def test_weak_or_missing_jwt_secret_is_refused(monkeypatch, secret: Optional[str]) -> None:
    """Tokens signed with a guessable key could be forged for any account, so startup fails."""
    if secret is None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET", secret)

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None)


def test_strong_jwt_secret_is_accepted(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "s" * 32)

    assert Settings(_env_file=None).jwt_secret == "s" * 32
