from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSettings:
    api_base_url: str = os.getenv(
        "PERSONAL_FINANCE_API_URL",
        "http://127.0.0.1:8000/api/v1/integrations/agent",
    ).rstrip("/")
    shared_secret: str = os.getenv("AGENT_SHARED_SECRET", "change-me-in-development")
    request_timeout_seconds: float = float(
        os.getenv("PERSONAL_FINANCE_AGENT_TIMEOUT", "15")
    )


def get_settings() -> AgentSettings:
    return AgentSettings()
