import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    "values",
    [
        {
            "agent_shared_secret": "local-agent-secret-change-me",
            "cookie_secure": True,
            "debug": False,
        },
        {
            "agent_shared_secret": "production-secret-that-is-long-enough",
            "cookie_secure": False,
            "debug": False,
        },
        {
            "agent_shared_secret": "production-secret-that-is-long-enough",
            "cookie_secure": True,
            "debug": True,
        },
    ],
)
def test_production_rejects_insecure_runtime_settings(values):
    with pytest.raises(ValidationError):
        Settings(environment="production", **values)


def test_production_accepts_explicit_secure_runtime_settings():
    settings = Settings(
        environment="production",
        agent_shared_secret="production-secret-that-is-long-enough",
        cookie_secure=True,
        debug=False,
    )

    assert settings.environment == "production"


def test_unknown_environment_is_rejected():
    with pytest.raises(ValidationError):
        Settings(environment="prod")
