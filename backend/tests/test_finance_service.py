from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from app.api.deps import AgentPrincipal
from app.api.v1.agent import agent_transaction
from app.core.security import hash_password
from app.models import AgentToolCall, Budget, User
from app.schemas.agent import AgentTransactionRequest
from app.schemas.finance import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryUpdate,
    TransactionCreate,
    TransferCreate,
)
from app.services.finance import (
    balance_for_account,
    budget_status,
    create_account,
    create_category,
    create_transaction,
    create_transfer,
    dashboard_data,
    ensure_account,
    list_transactions,
    monthly_evolution,
    totals_for_period,
    update_account,
    update_category,
    user_today,
)
from app.services.seed import seed_categories


def make_user(email: str = "ana@example.com", timezone: str = "America/Manaus") -> User:
    return User(
        email=email,
        full_name="Ana",
        password_hash=hash_password("senha-segura"),
        timezone=timezone,
    )


def setup_finances(db):
    user = make_user()
    db.add(user)
    db.flush()
    account = create_account(
        db, user, AccountCreate(name="Nubank", opening_balance=Decimal("1000.00"))
    )
    destination = create_account(
        db, user, AccountCreate(name="Inter", opening_balance=Decimal("100.00"))
    )
    food = create_category(db, user, CategoryCreate(name="Alimentação", kind="expense"))
    salary = create_category(db, user, CategoryCreate(name="Salário", kind="income"))
    db.flush()
    return user, account, destination, food, salary


def test_income_expense_and_transfer_preserve_balances(db):
    user, nubank, inter, food, salary = setup_finances(db)
    income = create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=nubank.id,
            category_id=salary.id,
            type="income",
            amount=Decimal("1000.00"),
            description="Salário",
            transaction_date=date(2026, 9, 10),
        ),
    )
    expense = create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=nubank.id,
            category_id=food.id,
            type="expense",
            amount=Decimal("250.00"),
            description="Mercado",
            transaction_date=date(2026, 9, 11),
        ),
    )
    transfer = create_transfer(
        db,
        user,
        TransferCreate(
            source_account_id=nubank.id,
            destination_account_id=inter.id,
            amount=Decimal("200.00"),
            transaction_date=date(2026, 9, 12),
        ),
    )
    db.commit()

    assert income.amount == Decimal("1000.00")
    assert expense.amount == Decimal("250.00")
    assert transfer.amount == Decimal("200.00")
    assert balance_for_account(db, nubank) == Decimal("1550.00")
    assert balance_for_account(db, inter) == Decimal("300.00")
    assert totals_for_period(db, user.id, date(2026, 9, 1), date(2026, 9, 30)) == (
        Decimal("1000.00"),
        Decimal("250.00"),
    )


def test_budget_reports_spend_remaining_and_excess(db):
    user, account, _destination, food, _salary = setup_finances(db)
    db.add(
        Budget(
            user_id=user.id,
            category_id=food.id,
            month=date(2026, 9, 1),
            limit_amount=Decimal("500.00"),
        )
    )
    create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=account.id,
            category_id=food.id,
            type="expense",
            amount=Decimal("125.00"),
            description="Restaurante",
            transaction_date=date(2026, 9, 20),
        ),
    )
    db.commit()

    item = budget_status(db, user, date(2026, 9, 20))[0]
    assert item["spent_amount"] == Decimal("125.00")
    assert item["remaining_amount"] == Decimal("375.00")
    assert item["utilization_percent"] == Decimal("25.00")
    assert item["exceeded_amount"] == Decimal("0.00")


def test_monthly_evolution_uses_backend_totals(db):
    user, account, _destination, food, salary = setup_finances(db)
    create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=account.id,
            category_id=salary.id,
            type="income",
            amount=Decimal("1000.00"),
            transaction_date=date(2026, 8, 10),
        ),
    )
    create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=account.id,
            category_id=food.id,
            type="expense",
            amount=Decimal("200.00"),
            transaction_date=date(2026, 9, 10),
        ),
    )

    result = monthly_evolution(db, user, date(2026, 9, 1), 2)

    assert result == [
        {
            "month": date(2026, 8, 1),
            "income": Decimal("1000.00"),
            "expense": Decimal("0.00"),
            "savings": Decimal("1000.00"),
        },
        {
            "month": date(2026, 9, 1),
            "income": Decimal("0.00"),
            "expense": Decimal("200.00"),
            "savings": Decimal("-200.00"),
        },
    ]


def test_dashboard_accounts_for_uncategorized_expenses(db):
    user, account, _destination, _food, _salary = setup_finances(db)
    create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=account.id,
            type="expense",
            amount=Decimal("17.50"),
            description="Despesa sem categoria",
            transaction_date=date(2026, 9, 15),
        ),
    )

    dashboard = dashboard_data(db, user, date(2026, 9, 1), date(2026, 9, 30))

    assert dashboard["totals"]["expense"] == Decimal("17.50")
    assert dashboard["by_category"] == [
        {
            "category_id": None,
            "category_name": "Sem categoria",
            "amount": Decimal("17.50"),
        }
    ]


def test_parent_budget_includes_subcategory_spend(db):
    user, account, _destination, food, _salary = setup_finances(db)
    market = create_category(
        db,
        user,
        CategoryCreate(name="Mercado", kind="expense", parent_id=food.id),
    )
    db.add(
        Budget(
            user_id=user.id,
            category_id=food.id,
            month=date(2026, 9, 1),
            limit_amount=Decimal("500.00"),
        )
    )
    create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=account.id,
            category_id=market.id,
            type="expense",
            amount=Decimal("90.00"),
            transaction_date=date(2026, 9, 20),
        ),
    )
    db.commit()

    item = budget_status(db, user, date(2026, 9, 20))[0]
    assert item["spent_amount"] == Decimal("90.00")
    assert item["remaining_amount"] == Decimal("410.00")


def test_idempotency_returns_same_transaction_and_transfer(db):
    user, nubank, inter, food, _salary = setup_finances(db)
    transaction_payload = TransactionCreate(
        account_id=nubank.id,
        category_id=food.id,
        type="expense",
        amount=Decimal("42.00"),
        description="Almoço",
        idempotency_key="whatsapp:message-1:transaction",
    )
    first = create_transaction(db, user, transaction_payload)
    second = create_transaction(db, user, transaction_payload)
    transfer_payload = TransferCreate(
        source_account_id=nubank.id,
        destination_account_id=inter.id,
        amount=Decimal("50.00"),
        idempotency_key="whatsapp:message-2:transfer",
    )
    first_transfer = create_transfer(db, user, transfer_payload)
    second_transfer = create_transfer(db, user, transfer_payload)

    assert first.id == second.id
    assert first_transfer.id == second_transfer.id


def test_same_idempotency_key_is_isolated_per_user(db):
    first_user, first_account, _destination, first_food, _salary = setup_finances(db)
    second_user = make_user("bruno@example.com")
    db.add(second_user)
    db.flush()
    second_account = create_account(db, second_user, AccountCreate(name="Nubank"))
    second_food = create_category(
        db, second_user, CategoryCreate(name="Alimentação", kind="expense")
    )

    for user, account, category in (
        (first_user, first_account, first_food),
        (second_user, second_account, second_food),
    ):
        create_transaction(
            db,
            user,
            TransactionCreate(
                account_id=account.id,
                category_id=category.id,
                type="expense",
                amount=Decimal("10.00"),
                idempotency_key="same-client-key",
            ),
        )
    db.commit()

    assert len(list_transactions(db, first_user)) == 1
    assert len(list_transactions(db, second_user)) == 1


def test_user_isolation_rejects_foreign_account(db):
    first_user = make_user()
    second_user = make_user("bruno@example.com")
    db.add_all([first_user, second_user])
    db.flush()
    account = create_account(db, first_user, AccountCreate(name="Privada"))

    with pytest.raises(HTTPException) as exc_info:
        ensure_account(db, second_user.id, account.id)

    assert exc_info.value.status_code == 404


def test_account_with_balance_cannot_be_hidden_by_deactivation(db):
    user, account, _destination, _food, _salary = setup_finances(db)

    with pytest.raises(HTTPException) as exc_info:
        update_account(
            db,
            user,
            account.id,
            AccountUpdate(is_active=False),
        )

    assert exc_info.value.status_code == 409
    assert account.is_active is True


def test_inactive_category_can_be_reactivated(db):
    user, _account, _destination, food, _salary = setup_finances(db)

    update_category(db, user, food.id, CategoryUpdate(is_active=False))
    assert food.is_active is False

    update_category(db, user, food.id, CategoryUpdate(is_active=True))
    assert food.is_active is True


def test_money_schema_rejects_more_than_two_decimal_places():
    with pytest.raises(ValueError):
        TransactionCreate(
            account_id="00000000-0000-0000-0000-000000000001",
            type="expense",
            amount=Decimal("10.001"),
        )
    with pytest.raises(ValueError):
        AccountCreate(name="Cheque especial", opening_balance=Decimal("-10.001"))


def test_user_today_uses_the_user_timezone():
    user = make_user(timezone="America/Manaus")
    expected = datetime.now(ZoneInfo("America/Manaus")).date()
    assert user_today(user) == expected


def test_agent_message_is_idempotent_and_keeps_whatsapp_source(db):
    user, account, _destination, food, _salary = setup_finances(db)
    principal = AgentPrincipal(
        user=user,
        provider="whatsapp",
        sender_id="+5592999999999",
        message_id="wamid-duplicate-1",
    )
    payload = AgentTransactionRequest(
        type="expense",
        amount=Decimal("25.00"),
        description="Almoço",
        account_name=account.name,
        category_name=food.name,
        transaction_date=date(2026, 9, 20),
    )

    first = agent_transaction(payload, principal=principal, db=db)
    second = agent_transaction(payload, principal=principal, db=db)

    assert first["source"] == "whatsapp"
    assert first["replayed"] is False
    assert second["replayed"] is True
    assert first["id"] == second["id"]
    calls = list(db.query(AgentToolCall).order_by(AgentToolCall.created_at))
    assert [call.status for call in calls] == ["success", "success"]
    assert all(call.tool_name == "create_transaction" for call in calls)


def test_agent_relative_date_is_resolved_in_user_timezone(db):
    user, account, _destination, food, _salary = setup_finances(db)
    principal = AgentPrincipal(
        user=user,
        provider="whatsapp",
        sender_id="+5592999999999",
        message_id="wamid-yesterday-1",
    )

    result = agent_transaction(
        AgentTransactionRequest(
            type="expense",
            amount=Decimal("12.00"),
            account_name=account.name,
            category_name=food.name,
            relative_date="yesterday",
        ),
        principal=principal,
        db=db,
    )

    assert result["transaction_date"] == user_today(user) - timedelta(days=1)


def test_agent_failure_is_audited_without_financial_write(db):
    user, account, _destination, _food, _salary = setup_finances(db)
    principal = AgentPrincipal(
        user=user,
        provider="whatsapp",
        sender_id="+5592999999999",
        message_id="wamid-invalid-category",
    )

    with pytest.raises(HTTPException):
        agent_transaction(
            AgentTransactionRequest(
                type="expense",
                amount=Decimal("25.00"),
                account_name=account.name,
                category_name="Categoria inexistente",
            ),
            principal=principal,
            db=db,
        )

    call = db.query(AgentToolCall).one()
    assert call.status == "error"
    assert call.error_code == "CATEGORY_NOT_FOUND"
    assert list_transactions(db, user) == []


def test_seeded_outros_category_accepts_ambiguous_income(db):
    user = make_user()
    db.add(user)
    db.flush()
    account = create_account(db, user, AccountCreate(name="Carteira"))
    seed_categories(db, user)
    db.flush()
    principal = AgentPrincipal(
        user=user,
        provider="whatsapp",
        sender_id="+5592999999999",
        message_id="wamid-income-default-1",
    )

    result = agent_transaction(
        AgentTransactionRequest(
            type="income",
            amount=Decimal("100.00"),
            account_name=account.name,
            transaction_date=date(2026, 9, 20),
        ),
        principal=principal,
        db=db,
    )

    assert result["category"] == "Outros"
