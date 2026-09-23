from agent.tools.http_tools import TOOLS, register_tools


def test_expected_finance_tools_are_exposed():
    assert {tool.name for tool in TOOLS} == {
        "verify_whatsapp",
        "create_transaction",
        "update_transaction",
        "delete_transaction",
        "get_transactions",
        "get_balance",
        "get_accounts",
        "get_categories",
        "get_month_summary",
        "get_category_summary",
        "get_budget_status",
        "create_budget",
        "create_goal",
        "create_transfer",
    }


def test_read_only_registration_blocks_mutations_before_backend_request(monkeypatch):
    registered_tools = []

    class ToolRecorder:
        def register_tool(self, **tool):
            registered_tools.append(tool)

    register_tools(ToolRecorder(), read_only=True)

    def unexpected_backend_call():
        raise AssertionError("uma tool mutável tentou acessar o backend")

    monkeypatch.setattr(
        "agent.tools.http_tools.BackendFinanceClient", unexpected_backend_call
    )
    tools_by_name = {tool["name"]: tool for tool in registered_tools}

    assert set(tools_by_name) == {tool.name for tool in TOOLS}
    write_tools = [tool for tool in TOOLS if tool.method != "GET"]
    assert {tool.method for tool in write_tools} == {"POST", "PATCH", "DELETE"}
    for tool in write_tools:
        result = tools_by_name[tool.name]["handler"]({})
        assert result == "Execução somente de leitura: operação financeira bloqueada."


def test_read_only_registration_allows_get_tools(monkeypatch):
    registered_tools = []
    backend_calls = []

    class ToolRecorder:
        def register_tool(self, **tool):
            registered_tools.append(tool)

    class BackendClient:
        def call(self, method, path, body=None):
            backend_calls.append((method, path, body))
            return '{"total":"0.00"}'

    monkeypatch.setattr("agent.tools.http_tools.BackendFinanceClient", BackendClient)
    register_tools(ToolRecorder(), read_only=True)
    tools_by_name = {tool["name"]: tool for tool in registered_tools}

    result = tools_by_name["get_balance"]["handler"]({})

    assert result == '{"total":"0.00"}'
    assert backend_calls == [("GET", "balance", None)]
