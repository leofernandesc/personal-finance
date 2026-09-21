from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import LLMMessage, StructuredResult


@dataclass(frozen=True)
class OpenAICompatibleProvider:
    """Small adapter for local OpenAI-compatible inference servers.

    Hermes talks to Ollama through this same protocol. Keeping this adapter
    independent from the financial tools allows the runner to use vLLM,
    llama.cpp, LM Studio or another local server without changing intent
    validation or backend dispatch.
    """

    base_url: str = "http://127.0.0.1:11434/v1"
    model: str = "qwen2.5:3b"
    api_key: str = ""
    timeout_seconds: float = 60.0
    temperature: float = 0.0
    seed: int = 7

    @property
    def _completion_url(self) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/chat/completions"

    def _post(self, payload: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            self._completion_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"Servidor OpenAI-compatible indisponível: {exc}"
            ) from exc

    @staticmethod
    def _messages(messages: list[LLMMessage]) -> list[dict[str, str]]:
        return [
            {"role": message.role, "content": message.content} for message in messages
        ]

    @staticmethod
    def _content(response: dict) -> str:
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        return str(content or "")

    def complete(
        self, messages: list[LLMMessage], *, tools: list[dict] | None = None
    ) -> str:
        payload = {
            "model": self.model,
            "messages": self._messages(messages),
            "temperature": self.temperature,
            "seed": self.seed,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        return self._content(self._post(payload))

    def complete_structured(
        self,
        messages: list[LLMMessage],
        *,
        json_schema: dict,
    ) -> StructuredResult:
        response = self._post(
            {
                "model": self.model,
                "messages": self._messages(messages),
                "temperature": self.temperature,
                "seed": self.seed,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "personal_finance_intent",
                        "strict": True,
                        "schema": json_schema,
                    },
                },
                "stream": False,
            }
        )
        content = self._content(response)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        return StructuredResult(content=content, parsed=parsed, model=self.model)
