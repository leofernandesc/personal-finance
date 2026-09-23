from types import SimpleNamespace

import agent.hermes_plugin as hermes_plugin
from agent.hermes_plugin import (
    _format_result,
    _remember_tool_result,
    require_financial_tool,
    transform_llm_output,
)


def test_read_only_environment_is_passed_to_tool_registration(monkeypatch):
    registered_modes = []
    monkeypatch.setenv("PERSONAL_FINANCE_READ_ONLY", "true")
    monkeypatch.setattr(
        hermes_plugin,
        "register_tools",
        lambda _ctx, *, read_only: registered_modes.append(read_only),
    )

    context = SimpleNamespace(
        register_system_prompt_section=lambda *args, **kwargs: None,
        register_hook=lambda *args, **kwargs: None,
        register_middleware=lambda *args, **kwargs: None,
    )
    hermes_plugin.register(context)

    assert registered_modes == [True]


def test_balance_response_is_rendered_from_backend_values():
    response = _format_result(
        "get_balance",
        '{"total":"6464.50","accounts":[{"account":"Nubank","balance":"5230.00"}]}',
    )

    assert (
        response == "Seu saldo total é R$ 6.464,50.\nPor conta:\n- Nubank: R$ 5.230,00"
    )


def test_transform_replaces_an_untrusted_final_answer():
    session_id = "test-hermes-grounding"
    _remember_tool_result(
        session_id=session_id,
        tool_name="get_month_summary",
        result='{"income":"4500.00","expense":"205.50","savings":"4294.50"}',
    )

    response = transform_llm_output(
        response_text="Aqui está uma explicação genérica.", session_id=session_id
    )

    assert response == (
        "Neste mês: receitas de R$ 4.500,00, despesas de R$ 205,50 "
        "e economia de R$ 4.294,50."
    )


def test_delete_confirmation_never_exposes_backend_token():
    response = _format_result(
        "delete_transaction",
        '{"confirmation_required":true,"confirmation_token":"secret-token",'
        '"amount":"20.00","description":"Uber"}',
    )

    assert (
        response
        == "Encontrei o movimento de R$ 20,00 (Uber). Você confirma a exclusão?"
    )
    assert "secret-token" not in response


def test_financial_request_requires_native_tool_call():
    result = require_financial_tool(
        {
            "model": "llama3.2:3b",
            "messages": [
                {"role": "user", "content": "Quanto dinheiro tenho atualmente?"}
            ],
            "tools": [{"type": "function"}],
        }
    )

    assert result == {
        "request": {
            "model": "llama3.2:3b",
            "messages": [
                {"role": "user", "content": "Quanto dinheiro tenho atualmente?"}
            ],
            "tools": [{"type": "function"}],
            "tool_choice": "required",
        },
        "reason": "financial_tool_required",
    }


def test_financial_tool_requirement_does_not_repeat_after_tool_result():
    request = {
        "messages": [
            {"role": "user", "content": "Quanto dinheiro tenho?"},
            {"role": "tool", "content": '{"total":"10.00"}'},
        ],
        "tool_choice": "auto",
    }

    assert require_financial_tool(request) is None


def test_nonfinancial_request_is_not_forced_into_finance_tool():
    assert (
        require_financial_tool(
            {"messages": [{"role": "user", "content": "Olá, tudo bem?"}]}
        )
        is None
    )
