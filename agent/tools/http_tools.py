from __future__ import annotations

from dataclasses import dataclass

from ..backend_client import BackendFinanceClient


@dataclass(frozen=True)
class BackendTool:
    name: str
    schema: dict
    method: str
    path: str


def _query(params: dict) -> str:
    from urllib.parse import urlencode

    values = {key: value for key, value in params.items() if value not in (None, "")}
    return f"?{urlencode(values)}" if values else ""


def _schema(
    name: str, description: str, properties: dict, required: list[str] | None = None
) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


AMOUNT = {
    "type": "number",
    "description": "Valor positivo em reais, com no máximo duas casas.",
}
DATE = {
    "type": "string",
    "description": "Data absoluta ISO YYYY-MM-DD. Não combine com relative_date.",
}
RELATIVE_DATE = {
    "type": "string",
    "enum": ["today", "yesterday", "tomorrow"],
    "description": "Use somente quando a pessoa disser hoje, ontem ou amanhã.",
}

TOOLS = [
    BackendTool(
        "verify_whatsapp",
        _schema(
            "verify_whatsapp",
            "Confirma a posse de um número WhatsApp usando o código exibido na aplicação web.",
            {"code": {"type": "string", "pattern": "^[0-9]{6}$"}},
            ["code"],
        ),
        "POST",
        "verify-whatsapp",
    ),
    BackendTool(
        "create_transaction",
        _schema(
            "create_transaction",
            "Registra uma receita ou despesa real no backend. Não use para transferências.",
            {
                "type": {"type": "string", "enum": ["income", "expense"]},
                "amount": AMOUNT,
                "description": {"type": "string"},
                "account_name": {"type": "string"},
                "category_name": {"type": "string"},
                "transaction_date": DATE,
                "relative_date": RELATIVE_DATE,
            },
            ["type", "amount"],
        ),
        "POST",
        "transactions",
    ),
    BackendTool(
        "update_transaction",
        _schema(
            "update_transaction",
            (
                "Corrige uma única transação existente. Consulte get_transactions "
                "antes se o id não estiver claro."
            ),
            {
                "transaction_id": {"type": "string"},
                "amount": AMOUNT,
                "description": {"type": "string"},
                "category_name": {"type": "string"},
                "transaction_date": DATE,
                "relative_date": RELATIVE_DATE,
            },
            ["transaction_id"],
        ),
        "PATCH",
        "transactions/{transaction_id}",
    ),
    BackendTool(
        "delete_transaction",
        _schema(
            "delete_transaction",
            "Exclui uma única transação depois de confirmação explícita do usuário.",
            {
                "transaction_id": {"type": "string"},
                "confirmation_token": {
                    "type": "string",
                    "description": (
                        "Token retornado pela primeira tentativa; use somente após "
                        "um sim explícito."
                    ),
                },
            },
            ["transaction_id"],
        ),
        "DELETE",
        "transactions/{transaction_id}",
    ),
    BackendTool(
        "create_transfer",
        _schema(
            "create_transfer",
            "Move dinheiro entre duas contas sem alterar o patrimônio total.",
            {
                "amount": AMOUNT,
                "source_account_name": {"type": "string"},
                "destination_account_name": {"type": "string"},
                "description": {"type": "string"},
                "transaction_date": DATE,
                "relative_date": RELATIVE_DATE,
            },
            ["amount", "source_account_name", "destination_account_name"],
        ),
        "POST",
        "transfers",
    ),
    BackendTool(
        "get_accounts",
        _schema(
            "get_accounts",
            "Consulta contas ativas e saldo retornado pelo backend.",
            {},
            [],
        ),
        "GET",
        "accounts",
    ),
    BackendTool(
        "get_categories",
        _schema(
            "get_categories", "Consulta categorias disponíveis do usuário.", {}, []
        ),
        "GET",
        "categories",
    ),
    BackendTool(
        "get_transactions",
        _schema(
            "get_transactions",
            "Consulta transações reais para responder histórico e localizar um movimento.",
            {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "search": {"type": "string"},
            },
            [],
        ),
        "GET",
        "transactions",
    ),
    BackendTool(
        "get_balance",
        _schema("get_balance", "Consulta o saldo real de todas as contas.", {}, []),
        "GET",
        "balance",
    ),
    BackendTool(
        "get_month_summary",
        _schema(
            "get_month_summary",
            "Consulta receitas, despesas e economia do mês calculadas pelo backend.",
            {},
            [],
        ),
        "GET",
        "month-summary",
    ),
    BackendTool(
        "get_category_summary",
        _schema(
            "get_category_summary",
            "Consulta quanto foi gasto em uma categoria no mês atual.",
            {"category_name": {"type": "string"}},
            ["category_name"],
        ),
        "GET",
        "category-summary",
    ),
    BackendTool(
        "get_budget_status",
        _schema(
            "get_budget_status",
            "Consulta orçamento, utilizado, restante e excedente.",
            {},
            [],
        ),
        "GET",
        "budget-status",
    ),
    BackendTool(
        "create_budget",
        _schema(
            "create_budget",
            "Cria ou atualiza o limite mensal de uma categoria.",
            {
                "category_name": {"type": "string"},
                "limit_amount": AMOUNT,
                "month": DATE,
            },
            ["category_name", "limit_amount"],
        ),
        "POST",
        "budgets",
    ),
    BackendTool(
        "create_goal",
        _schema(
            "create_goal",
            "Cria uma meta financeira.",
            {
                "name": {"type": "string"},
                "target_amount": AMOUNT,
                "current_amount": AMOUNT,
                "deadline": DATE,
            },
            ["name", "target_amount"],
        ),
        "POST",
        "goals",
    ),
]


def register_tools(ctx) -> None:
    for tool in TOOLS:

        def handler(params: dict, *, _tool=tool, **kwargs) -> str:
            if _tool.method == "GET":
                if _tool.name == "get_transactions":
                    return BackendFinanceClient().call(
                        "GET", f"transactions{_query(params)}"
                    )
                if _tool.name == "get_category_summary":
                    return BackendFinanceClient().call(
                        "GET", f"category-summary{_query(params)}"
                    )
                return BackendFinanceClient().call("GET", _tool.path)
            path = _tool.path
            if "{transaction_id}" in path:
                path = path.format(transaction_id=params.get("transaction_id", ""))
                body = params
            else:
                body = params
            return BackendFinanceClient().call(_tool.method, path, body)

        ctx.register_tool(
            name=tool.name,
            toolset="personal_finance",
            schema=tool.schema,
            handler=handler,
            emoji="💰",
        )
