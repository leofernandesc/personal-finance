import pytest
from agent.runner import _normalize_intent


def test_normalize_intent_prefers_relative_date_marker():
    intent = _normalize_intent(
        {
            "tool": "create_transaction",
            "type": "expense",
            "amount": 25,
            "transaction_date": "today",
            "relative_date": "today",
        }
    )

    assert "transaction_date" not in intent
    assert intent["relative_date"] == "today"


def test_normalize_intent_requires_category_summary_for_category_question():
    with pytest.raises(RuntimeError):
        _normalize_intent(
            {"tool": "get_month_summary"},
            "Quanto gastei com transporte este mês?",
        )


def test_normalize_intent_accepts_only_six_digit_whatsapp_code():
    assert (
        _normalize_intent(
            {"tool": "verify_whatsapp", "verification_code": "123456"},
            "123456",
        )["verification_code"]
        == "123456"
    )


@pytest.mark.parametrize(
    "intent",
    [
        {"tool": "create_transaction", "amount": 25},
        {"tool": "create_transaction", "type": "expense", "amount": -25},
        {"tool": "create_transfer", "amount": 300, "source_account_name": "Nubank"},
        {"tool": "get_category_summary"},
    ],
)
def test_normalize_intent_rejects_incomplete_or_invalid_operations(intent):
    with pytest.raises(RuntimeError):
        _normalize_intent(intent)
