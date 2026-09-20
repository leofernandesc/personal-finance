from agent.tools.http_tools import TOOLS


def test_expected_finance_tools_are_exposed():
    assert {tool.name for tool in TOOLS} == {
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
