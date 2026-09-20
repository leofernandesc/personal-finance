from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class StructuredResult:
    content: str
    parsed: dict[str, Any] | None
    model: str


class LLMProvider(Protocol):
    """Provider seam used by the standalone local runner and future adapters."""

    def complete(self, messages: list[LLMMessage], *, tools: list[dict] | None = None) -> str: ...

    def complete_structured(
        self,
        messages: list[LLMMessage],
        *,
        json_schema: dict[str, Any],
    ) -> StructuredResult: ...
