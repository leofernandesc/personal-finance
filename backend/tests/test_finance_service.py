from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from app.api.deps import AgentPrincipal
from app.api.v1.agent import agent_transaction
from app.core.security import hash_password
from app.models import Budget, User
from app.schemas.agent import AgentTransactionRequest
from app.schemas.finance import (
    AccountCreate,
    CategoryCreate,
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
    ensure_account,
    totals_for_period,
    user_today,
)


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


def test_user_isolation_rejects_foreign_account(db):
    first_user = make_user()
    second_user = make_user("bruno@example.com")
    db.add_all([first_user, second_user])
    db.flush()
    account = create_account(db, first_user, AccountCreate(name="Privada"))

    with pytest.raises(HTTPException) as exc_info:
        ensure_account(db, second_user.id, account.id)

    assert exc_info.value.status_code == 404


def test_money_schema_rejects_more_than_two_decimal_places():
    with pytest.raises(ValueError):
        TransactionCreate(
            account_id="00000000-0000-0000-0000-000000000001",
            type="expense",
            amount=Decimal("10.001"),
        )


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
