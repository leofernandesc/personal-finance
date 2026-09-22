from __future__ import annotations

import json
import unicodedata
from collections import OrderedDict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import Lock
from typing import Any

from .tools.http_tools import register_tools

PROMPT_PATH = Path(__file__).with_name("prompts") / "system.md"
_MAX_TOOL_RESULTS = 128
_RESULT_LOCK = Lock()
_LAST_TOOL_RESULTS: OrderedDict[str, tuple[str, str]] = OrderedDict()

_FINANCIAL_INTENT_MARKERS = (
    "saldo",
    "dinheiro",
    "gastei",
    "gasto",
    "despesa",
    "recebi",
    "receita",
    "transferi",
    "transferencia",
    "conta",
    "categoria",
    "orcamento",
    "meta",
    "divida",
    "fatura",
    "pagamento",
    "compra",
    "mercado",
    "almoço",
    "almoco",
    "gasolina",
    "uber",
    "transporte",
    "alimentacao",
    "alimentação",
    "quanto gastei",
    "quanto tenho",
)


def _brl(value: Any) -> str:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return "R$ —"
    formatted = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _latest_user_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
    return ""


def require_financial_tool(request: dict[str, Any], **kwargs) -> dict[str, Any] | None:
    """Require a native tool call for explicit financial requests.

    Some small local models emit a JSON-looking tool call as plain text when
    the OpenAI-compatible request leaves ``tool_choice`` on ``auto``. This
    middleware only changes the initial request for a financial utterance;
    once a tool result is present, the model must be allowed to produce its
    short final answer.
    """
    del kwargs
    if not isinstance(request, dict):
        return None
    messages = request.get("messages") or request.get("input")
    if not isinstance(messages, list) or any(
        isinstance(message, dict) and message.get("role") == "tool"
        for message in messages
    ):
        return None
    if request.get("tool_choice") not in (None, "auto"):
        return None
    text = _normalize_text(_latest_user_text(messages))
    if not text or not any(marker in text for marker in _FINANCIAL_INTENT_MARKERS):
        return None
    next_request = dict(request)
    next_request["tool_choice"] = "required"
    return {"request": next_request, "reason": "financial_tool_required"}


def _remember_tool_result(**kwargs) -> None:
    session_id = str(kwargs.get("session_id") or "")
    tool_name = str(kwargs.get("tool_name") or "")
    result = kwargs.get("result")
    if not session_id or not tool_name or result in (None, ""):
        return
    if isinstance(result, str):
        serialized = result
    else:
        serialized = json.dumps(result, ensure_ascii=False, default=str)
    with _RESULT_LOCK:
        _LAST_TOOL_RESULTS[session_id] = (tool_name, serialized)
        _LAST_TOOL_RESULTS.move_to_end(session_id)
        while len(_LAST_TOOL_RESULTS) > _MAX_TOOL_RESULTS:
            _LAST_TOOL_RESULTS.popitem(last=False)


def _safe_error(result: dict[str, Any]) -> str | None:
    error = result.get("error")
    if not error:
        return None
    if isinstance(error, dict):
        detail = error.get("detail", error.get("message"))
        if isinstance(detail, dict):
            detail = detail.get("message") or detail.get("code")
        return str(detail or "Não foi possível concluir a operação.")
    return str(error)


def _format_result(tool_name: str, serialized: str) -> str | None:
    try:
        result = json.loads(serialized)
    except json.JSONDecodeError:
        return None
    if not isinstance(result, (dict, list)):
        return None
    if isinstance(result, dict):
        error = _safe_error(result)
        if error:
            return f"Não consegui concluir a operação: {error}"

    if tool_name == "get_balance" and isinstance(result, dict):
        accounts = result.get("accounts") or []
        lines = [f"Seu saldo total é {_brl(result.get('total'))}."]
        if accounts:
            lines.append("Por conta:")
            lines.extend(
                f"- {item.get('account')}: {_brl(item.get('balance'))}"
                for item in accounts
                if isinstance(item, dict)
            )
        return "\n".join(lines)
    if tool_name == "get_month_summary" and isinstance(result, dict):
        return (
            f"Neste mês: receitas de {_brl(result.get('income'))}, despesas de "
            f"{_brl(result.get('expense'))} e economia de {_brl(result.get('savings'))}."
        )
    if tool_name == "get_category_summary" and isinstance(result, dict):
        return (
            f"Em {result.get('category', 'essa categoria')}, você gastou "
            f"{_brl(result.get('expense'))} no mês."
        )
    if tool_name == "create_transaction" and isinstance(result, dict):
        prefix = (
            "Movimento já registrado"
            if result.get("replayed")
            else "Movimento registrado"
        )
        return (
            f"{prefix}: {_brl(result.get('amount'))} em "
            f"{result.get('category') or 'Outros'} ({result.get('description') or 'movimento'})."
        )
    if tool_name == "create_transfer" and isinstance(result, dict):
        prefix = (
            "Transferência já registrada"
            if result.get("replayed")
            else "Transferência registrada"
        )
        return (
            f"{prefix}: {_brl(result.get('amount'))} de {result.get('from')} "
            f"para {result.get('to')}."
        )
    if tool_name == "update_transaction" and isinstance(result, dict):
        return f"Movimento atualizado: {_brl(result.get('amount'))} em {result.get('description') or 'movimento'}."
    if tool_name == "delete_transaction" and isinstance(result, dict):
        if result.get("confirmation_required"):
            return (
                f"Encontrei o movimento de {_brl(result.get('amount'))} "
                f"({result.get('description') or 'movimento'}). Você confirma a exclusão?"
            )
        return "Movimento excluído."
    if tool_name == "verify_whatsapp" and isinstance(result, dict):
        return (
            "WhatsApp verificado. Agora você pode registrar e consultar seus movimentos."
            if result.get("verified")
            else "Não foi possível verificar o WhatsApp."
        )
    if tool_name == "get_accounts" and isinstance(result, list):
        if not result:
            return "Você ainda não tem contas cadastradas."
        return "Suas contas:\n" + "\n".join(
            f"- {item.get('name')}: {_brl(item.get('balance'))}"
            for item in result
            if isinstance(item, dict)
        )
    if tool_name == "get_transactions" and isinstance(result, list):
        if not result:
            return "Não encontrei movimentos para essa consulta."
        return "Movimentos encontrados:\n" + "\n".join(
            f"- {item.get('date')}: {_brl(item.get('amount'))} — "
            f"{item.get('description') or 'movimento'}"
            for item in result[:10]
            if isinstance(item, dict)
        )
    if tool_name == "get_budget_status" and isinstance(result, list):
        if not result:
            return "Você ainda não tem orçamentos cadastrados."
        return "Orçamentos:\n" + "\n".join(
            f"- {item.get('category_name')}: usado {_brl(item.get('spent_amount'))} "
            f"de {_brl(item.get('limit_amount'))}"
            for item in result
            if isinstance(item, dict)
        )
    if tool_name == "create_budget" and isinstance(result, dict):
        return (
            f"Orçamento de {result.get('category_name', 'categoria')} definido em "
            f"{_brl(result.get('limit_amount'))}."
        )
    if tool_name == "create_goal" and isinstance(result, dict):
        return (
            f"Meta “{result.get('name', 'sem nome')}” criada com alvo de "
            f"{_brl(result.get('target_amount'))}."
        )
    return None


def transform_llm_output(
    response_text: str = "", session_id: str = "", **kwargs
) -> str | None:
    del kwargs
    with _RESULT_LOCK:
        recorded = _LAST_TOOL_RESULTS.pop(session_id, None)
    if not recorded:
        return None
    tool_name, serialized = recorded
    return _format_result(tool_name, serialized) or response_text


def register(ctx) -> None:
    register_tools(ctx)
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    ctx.register_system_prompt_section(
        "personal-finance.rules", prompt, position="after_memory", max_chars=4000
    )

    def record_tool_call(tool_name: str = "", result: str = "", **kwargs) -> None:
        _remember_tool_result(tool_name=tool_name, result=result, **kwargs)
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
    ctx.register_hook("transform_llm_output", transform_llm_output)
    ctx.register_middleware("llm_request", require_financial_tool)
