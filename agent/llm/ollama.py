from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import LLMMessage, StructuredResult


@dataclass(frozen=True)
class OllamaProvider:
    """Small stdlib-only Ollama adapter; no finance logic lives here."""

    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5:7b"
    timeout_seconds: float = 60.0

    def _post(self, payload: dict) -> dict:
        request = Request(
            f"{self.base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Ollama indisponível: {exc}") from exc

    @staticmethod
    def _messages(messages: list[LLMMessage]) -> list[dict[str, str]]:
        return [{"role": message.role, "content": message.content} for message in messages]

    def complete(self, messages: list[LLMMessage], *, tools: list[dict] | None = None) -> str:
        payload = {"model": self.model, "messages": self._messages(messages), "stream": False}
        if tools:
            payload["tools"] = tools
        response = self._post(payload)
        return str(response.get("message", {}).get("content", ""))

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
                "format": json_schema,
                "stream": False,
            }
        )
        content = str(response.get("message", {}).get("content", ""))
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        return StructuredResult(content=content, parsed=parsed, model=self.model)
