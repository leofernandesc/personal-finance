"""Local deterministic bridge for testing Ollama -> FastAPI without WhatsApp.

Hermes is the production conversational host. This runner is intentionally
small and useful for smoke tests: Ollama extracts an intent, then this module
calls the same authenticated backend boundary used by Hermes tools.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .backend_client import AgentContext, BackendFinanceClient
from .llm import LLMMessage, OllamaProvider

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {
            "type": "string",
            "enum": [
                "create_transaction",
                "create_transfer",
                "get_month_summary",
                "get_balance",
                "get_category_summary",
                "get_transactions",
            ],
        },
        "type": {"type": "string", "enum": ["income", "expense"]},
        "amount": {"type": "number"},
        "description": {"type": "string"},
        "category_name": {"type": "string"},
        "account_name": {"type": "string"},
        "source_account_name": {"type": "string"},
        "destination_account_name": {"type": "string"},
        "transaction_date": {"type": "string"},
        "relative_date": {
            "type": "string",
            "enum": ["today", "yesterday", "tomorrow"],
        },
    },
    "required": ["tool"],
}


def interpret(text: str, provider: OllamaProvider) -> dict:
    result = provider.complete_structured(
        [
            LLMMessage(
                role="system",
                content=(
                    "Interprete a mensagem financeira em português brasileiro. "
                    "Retorne apenas o objeto no schema. Não calcule valores. "
                    "Para hoje, ontem ou amanhã use relative_date e não calcule a data. "
                    "Para uma pergunta sobre mês use get_month_summary; para saldo use get_balance."
                ),
            ),
            LLMMessage(role="user", content=text),
        ],
        json_schema=INTENT_SCHEMA,
    )
    if not result.parsed or not isinstance(result.parsed, dict):
        raise RuntimeError(f"Ollama não retornou uma intenção estruturada: {result.content}")
    return result.parsed


def dispatch(intent: dict, context: AgentContext) -> str:
    client = BackendFinanceClient()
    tool = intent.get("tool")
    payload = {key: value for key, value in intent.items() if key != "tool" and value is not None}
    if tool == "create_transaction":
        return client.call("POST", "transactions", payload, context=context)
    if tool == "create_transfer":
        return client.call("POST", "transfers", payload, context=context)
    if tool == "get_month_summary":
        return client.call("GET", "month-summary", context=context)
    if tool == "get_balance":
        return client.call("GET", "balance", context=context)
    if tool == "get_category_summary":
        from urllib.parse import urlencode

        return client.call(
            "GET",
            f"category-summary?{urlencode({'category_name': intent.get('category_name', '')})}",
            context=context,
        )
    if tool == "get_transactions":
        return client.call("GET", "transactions", context=context)
    raise ValueError(f"Tool não permitida no runner: {tool}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Ollama -> Personal Finance API")
    parser.add_argument("text", help="Mensagem financeira em português")
    parser.add_argument("--sender", required=True, help="Número WhatsApp em E.164")
    parser.add_argument("--message-id", default="local-runner-message")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))
    parser.add_argument(
        "--ollama-url", default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    )
    args = parser.parse_args()
    provider = OllamaProvider(base_url=args.ollama_url, model=args.model)
    intent = interpret(args.text, provider)
    result = dispatch(
        intent, AgentContext(provider="whatsapp", sender_id=args.sender, message_id=args.message_id)
    )
    print(
        json.dumps({"intent": intent, "backend": json.loads(result)}, ensure_ascii=False, indent=2)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
