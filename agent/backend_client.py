from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config.settings import AgentSettings, get_settings


def _session_value(name: str, default: str = "") -> str:
    try:
        from gateway.session_context import get_session_env

        value = get_session_env(name, "")
        if value:
            return str(value)
    except (ImportError, AttributeError):
        return os.getenv(name, default)
    return os.getenv(name, default)


def _canonical_sender_id(provider: str, sender_id: str) -> str:
    """Use Hermes' WhatsApp LID map when this code runs inside Hermes.

    Baileys may expose a contact as ``<lid>@lid`` even when the user linked
    the account with an E.164 phone number. The backend deliberately stores
    and resolves phone numbers, so the adapter boundary must normalize this
    alias before sending authentication headers. The import is optional: the
    deterministic local runner and unit tests can run without Hermes' source
    tree and simply retain the value they were given.
    """
    if provider != "whatsapp" or not sender_id:
        return sender_id
    try:
        from gateway.whatsapp_identity import canonical_whatsapp_identifier

        return canonical_whatsapp_identifier(sender_id) or sender_id
    except (ImportError, AttributeError, OSError, RuntimeError):
        return sender_id


@dataclass(frozen=True)
class AgentContext:
    provider: str
    sender_id: str
    message_id: str | None


def current_context() -> AgentContext:
    provider = _session_value("HERMES_SESSION_PLATFORM", "whatsapp") or "whatsapp"
    sender_id = _session_value("HERMES_SESSION_USER_ID") or _session_value(
        "HERMES_SESSION_CHAT_ID"
    )
    return AgentContext(
        provider=provider,
        sender_id=_canonical_sender_id(provider, sender_id),
        message_id=_session_value("HERMES_SESSION_MESSAGE_ID") or None,
    )


class BackendFinanceClient:
    def __init__(self, settings: AgentSettings | None = None):
        self.settings = settings or get_settings()

    def call(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        context: AgentContext | None = None,
    ) -> str:
        ctx = context or current_context()
        if not ctx.sender_id:
            return json.dumps(
                {"error": "Não foi possível identificar o remetente WhatsApp."},
                ensure_ascii=False,
            )
        if not ctx.message_id:
            return json.dumps(
                {
                    "error": "Não foi possível identificar a mensagem para garantir idempotência."
                },
                ensure_ascii=False,
            )
        headers = {
            "Content-Type": "application/json",
            "X-Agent-Token": self.settings.shared_secret,
            "X-Agent-Provider": ctx.provider,
            "X-Agent-Sender-Id": ctx.sender_id,
        }
        if ctx.message_id:
            headers["X-Agent-Message-Id"] = ctx.message_id
        request = Request(
            f"{self.settings.api_base_url}/{path.lstrip('/')}",
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(
                request, timeout=self.settings.request_timeout_seconds
            ) as response:
                body = response.read().decode("utf-8")
                return body or json.dumps({"ok": True})
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(body)
            except json.JSONDecodeError:
                detail = {"detail": body}
            return json.dumps({"error": detail}, ensure_ascii=False)
        except (URLError, TimeoutError) as exc:
            return json.dumps(
                {"error": f"Backend financeiro indisponível: {exc}"}, ensure_ascii=False
            )
