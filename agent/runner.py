"""Local deterministic bridge for testing Ollama -> FastAPI without WhatsApp.

Hermes is the production conversational host. This runner is intentionally
small and useful for smoke tests: Ollama extracts an intent, then this module
calls the same authenticated backend boundary used by Hermes tools.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

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
            "description": "A única tool que deve ser chamada para a mensagem.",
        },
        "type": {
            "type": "string",
            "enum": ["income", "expense"],
            "description": "Use expense para gastei/paguei e income para recebi/entrou.",
        },
        "amount": {"type": "number", "minimum": 0.01},
        "description": {"type": "string"},
        "category_name": {"type": "string"},
        "account_name": {"type": "string"},
        "source_account_name": {"type": "string"},
        "destination_account_name": {"type": "string"},
        "transaction_date": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
        },
        "relative_date": {
            "type": "string",
            "enum": ["today", "yesterday", "tomorrow"],
        },
    },
    "required": ["tool"],
    "additionalProperties": False,
}

PROMPT_PATH = Path(__file__).with_name("prompts") / "system.md"


def _interpretation_prompt() -> str:
    return f"""{PROMPT_PATH.read_text(encoding="utf-8")}

Tarefa desta chamada: extraia a intenção de UMA mensagem do usuário.
Retorne exatamente um objeto JSON válido conforme o schema, sem markdown ou texto extra.
Escolha exatamente uma tool.

Regras de classificação adicionais:
- “gastei”, “paguei”, “comprei” e “usei” significam create_transaction com type=expense.
- “recebi”, “ganhei” e “entrou” significam create_transaction com type=income.
- “transferi”, “mandei de uma conta para outra” significam create_transfer.
- “quanto”, “qual meu saldo” e “quais foram” significam uma tool de consulta.
- “quanto gastei com alimentação/transporte/lazer este mês?” significa
  get_category_summary com o nome da categoria; “quanto gastei este mês?” sem categoria
  significa get_month_summary.
- Nunca use get_balance para uma frase que registra gasto ou receita.
- amount é sempre positivo; nunca use valor negativo para representar uma despesa.
- Se a mensagem disser hoje, ontem ou amanhã, use relative_date=today, relative_date=yesterday
  ou relative_date=tomorrow, sem calcular uma data absoluta.
- Para exemplos comuns, use os nomes existentes do seed quando forem compatíveis: almoço,
  restaurante e comida -> Alimentação; gasolina e combustível -> Combustível; Uber e 99 ->
  Aplicativos.
- Extraia a conta explicitamente quando a mensagem disser “pelo Nubank”, “na conta Inter”,
  “usando Dinheiro” ou equivalente: nesse caso account_name deve conter somente o nome da
  conta e a descrição não deve repetir esse trecho.

Exemplo obrigatório de comportamento:
“Gastei R$ 25 com almoço hoje.” -> tool=create_transaction, type=expense, amount=25,
description=Almoço, category_name=Alimentação, relative_date=today.
“Gastei R$ 25 com almoço hoje pelo Nubank.” deve incluir account_name=Nubank e
description=Almoço.
"""


def interpret(text: str, provider: OllamaProvider) -> dict:
    messages = [
        LLMMessage(role="system", content=_interpretation_prompt()),
        LLMMessage(role="user", content=text),
    ]
    last_error: RuntimeError | None = None
    for attempt in range(2):
        result = provider.complete_structured(messages, json_schema=INTENT_SCHEMA)
        if not result.parsed or not isinstance(result.parsed, dict):
            last_error = RuntimeError(
                f"Ollama não retornou uma intenção estruturada: {result.content}"
            )
        else:
            try:
                return _normalize_intent(result.parsed, text)
            except RuntimeError as error:
                last_error = error
        if attempt == 0:
            messages.append(
                LLMMessage(
                    role="user",
                    content=(
                        "A saída anterior estava inválida. Corrija agora: escolha a tool que "
                        "corresponde ao verbo da mensagem, preencha type e amount para uma "
                        "transação, use valores positivos e retorne somente o JSON completo."
                    ),
                )
            )
    raise last_error or RuntimeError("Não foi possível interpretar a mensagem")


def _normalize_intent(intent: dict, text: str = "") -> dict:
    normalized = dict(intent)
    relative_date = normalized.get("relative_date")
    if relative_date in {"today", "yesterday", "tomorrow"}:
        normalized.pop("transaction_date", None)

    tool = normalized.get("tool")
    normalized_text = text.casefold()
    is_query = bool(re.search(r"\b(quanto|qual|quais|compare|comparar)\b", normalized_text))
    if (
        not is_query
        and re.search(r"\b(gastei|paguei|comprei|usei)\b", normalized_text)
        and (tool != "create_transaction" or normalized.get("type") != "expense")
    ):
        raise RuntimeError("A mensagem de gasto precisa virar uma despesa")
    if (
        not is_query
        and re.search(r"\b(recebi|ganhei|entrou)\b", normalized_text)
        and (tool != "create_transaction" or normalized.get("type") != "income")
    ):
        raise RuntimeError("A mensagem de recebimento precisa virar uma receita")
    if (
        not is_query
        and re.search(r"\b(transferi|transferência|transferencia)\b", normalized_text)
        and (tool != "create_transfer")
    ):
        raise RuntimeError("A mensagem de transferência precisa virar uma transferência")
    if (
        is_query
        and re.search(r"\bquanto\s+gastei\s+com\b", normalized_text)
        and tool != "get_category_summary"
    ):
        raise RuntimeError("A pergunta nomeia uma categoria e precisa de seu resumo")
    if re.search(
        r"\b(pelo|pela|na conta|no banco|usando)\b", normalized_text
    ) and not normalized.get("account_name"):
        raise RuntimeError("A mensagem informou uma conta, mas a intenção não a extraiu")
    if tool == "create_transaction":
        if normalized.get("type") not in {"income", "expense"}:
            raise RuntimeError("A intenção de transação não informou income ou expense")
        amount = normalized.get("amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise RuntimeError("A intenção de transação não informou um valor positivo")
    elif tool == "create_transfer":
        amount = normalized.get("amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise RuntimeError("A intenção de transferência não informou um valor positivo")
        if not normalized.get("source_account_name") or not normalized.get(
            "destination_account_name"
        ):
            raise RuntimeError("A intenção de transferência não informou as duas contas")
    elif tool == "get_category_summary" and not normalized.get("category_name"):
        raise RuntimeError("A consulta de categoria não informou a categoria")
    return normalized


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
        intent,
        AgentContext(provider="whatsapp", sender_id=args.sender, message_id=args.message_id),
    )
    print(
        json.dumps(
            {"intent": intent, "backend": json.loads(result)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
