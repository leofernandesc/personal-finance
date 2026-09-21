import json
import sys
from types import ModuleType
from unittest.mock import patch

from agent.backend_client import AgentContext, BackendFinanceClient, current_context
from agent.config.settings import AgentSettings


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return b'{"ok": true}'


def test_backend_client_sends_identity_and_message_headers():
    settings = AgentSettings(
        api_base_url="http://api.test/integrations/agent", shared_secret="secret"
    )
    client = BackendFinanceClient(settings)
    context = AgentContext(
        provider="whatsapp", sender_id="+5592999999999", message_id="wamid-1"
    )

    with patch("agent.backend_client.urlopen", return_value=FakeResponse()) as urlopen:
        response = client.call("POST", "transactions", {"amount": 25}, context=context)

    assert json.loads(response)["ok"] is True
    request = urlopen.call_args.args[0]
    assert request.full_url.endswith("/transactions")
    assert request.get_header("X-agent-token") == "secret"
    assert request.get_header("X-agent-sender-id") == "+5592999999999"
    assert request.get_header("X-agent-message-id") == "wamid-1"


def test_backend_client_refuses_unidentified_or_non_idempotent_calls():
    settings = AgentSettings(
        api_base_url="http://api.test/integrations/agent",
        shared_secret="secret",
    )
    client = BackendFinanceClient(settings)

    with patch("agent.backend_client.urlopen") as urlopen:
        missing_sender = client.call(
            "GET",
            "balance",
            context=AgentContext(
                provider="whatsapp", sender_id="", message_id="wamid-1"
            ),
        )
        missing_message = client.call(
            "GET",
            "balance",
            context=AgentContext(
                provider="whatsapp",
                sender_id="+5592999999999",
                message_id=None,
            ),
        )

    assert "remetente" in json.loads(missing_sender)["error"]
    assert "idempotência" in json.loads(missing_message)["error"]
    urlopen.assert_not_called()


def test_current_context_canonicalizes_whatsapp_lid():
    gateway = ModuleType("gateway")
    whatsapp_identity = ModuleType("gateway.whatsapp_identity")
    whatsapp_identity.canonical_whatsapp_identifier = lambda _value: "5592999999999"
    gateway.whatsapp_identity = whatsapp_identity
    with (
        patch(
            "agent.backend_client._session_value",
            side_effect=lambda name, default="": {
                "HERMES_SESSION_PLATFORM": "whatsapp",
                "HERMES_SESSION_USER_ID": "123456789@lid",
                "HERMES_SESSION_MESSAGE_ID": "wamid-2",
            }.get(name, default),
        ),
        patch(
            "sys.modules",
            {
                **sys.modules,
                "gateway": gateway,
                "gateway.whatsapp_identity": whatsapp_identity,
            },
        ),
    ):
        context = current_context()

    assert context.provider == "whatsapp"
    assert context.sender_id == "5592999999999"
    assert context.message_id == "wamid-2"
