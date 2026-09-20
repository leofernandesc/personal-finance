from __future__ import annotations

import json
from pathlib import Path

from .tools.http_tools import register_tools

PROMPT_PATH = Path(__file__).with_name("prompts") / "system.md"


def register(ctx) -> None:
    register_tools(ctx)
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    ctx.register_system_prompt_section(
        "personal-finance.rules", prompt, position="after_memory", max_chars=4000
    )

    def record_tool_call(tool_name: str = "", result: str = "", **kwargs) -> None:
        del kwargs
        if not tool_name.startswith(("create_", "update_", "delete_")):
            return
        # The authoritative audit row is written by FastAPI. This hook only
        # emits a bounded technical line for Hermes logs and never logs payloads.
        if result:
            print(
                json.dumps(
                    {
                        "component": "personal-finance-agent",
                        "tool": tool_name,
                        "result_bytes": len(result),
                    },
                    ensure_ascii=False,
                )
            )

    ctx.register_hook("post_tool_call", record_tool_call)
