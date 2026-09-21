import json
from unittest.mock import patch

from agent.llm import LLMMessage, OpenAICompatibleProvider


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(
            {"choices": [{"message": {"content": '{"tool":"get_balance"}'}}]}
        ).encode()


def test_openai_compatible_provider_sends_structured_schema():
    provider = OpenAICompatibleProvider(
        base_url="http://llm.test/v1", model="local-model", api_key="local-key"
    )
    with patch(
        "agent.llm.openai_compatible.urlopen", return_value=FakeResponse()
    ) as urlopen:
        result = provider.complete_structured(
            [LLMMessage(role="user", content="Qual meu saldo?")],
            json_schema={"type": "object", "properties": {"tool": {"type": "string"}}},
        )

    request = urlopen.call_args.args[0]
    body = json.loads(request.data)
    assert request.full_url == "http://llm.test/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer local-key"
    assert body["response_format"]["type"] == "json_schema"
    assert result.parsed == {"tool": "get_balance"}
