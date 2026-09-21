from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.deps import AgentPrincipal
from app.api.v1.agent import (
    _verification_digest,
    agent_delete_transaction,
    agent_transaction,
    verify_whatsapp,
)
from app.core.security import hash_password
from app.models import (
    AgentMessage,
    AgentToolCall,
    AuthSession,
    Budget,
    PendingAgentAction,
    Transaction,
    User,
    WhatsAppIdentity,
)
from app.schemas.agent import (
    AgentTransactionDeleteRequest,
    AgentTransactionRequest,
    AgentWhatsAppVerificationRequest,
)
from app.schemas.finance import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryUpdate,
    TransactionCreate,
    TransferCreate,
    TransferUpdate,
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
    update_transfer,
    user_today,
)
from app.services.maintenance import cleanup_expired_data
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


def test_update_transfer_changes_both_legs_atomically(db):
    user, nubank, inter, _food, _salary = setup_finances(db)
    transfer = create_transfer(
        db,
        user,
        TransferCreate(
            source_account_id=nubank.id,
            destination_account_id=inter.id,
            amount=Decimal("200.00"),
            description="Reserva",
            transaction_date=date(2026, 9, 12),
        ),
    )
    db.commit()

    updated = update_transfer(
        db,
        user,
        transfer.id,
        TransferUpdate(
            source_account_id=inter.id,
            destination_account_id=nubank.id,
            amount=Decimal("350.00"),
            description="Rebalanceamento",
            transaction_date=date(2026, 9, 15),
        ),
    )
    db.commit()

    legs = list(
        db.scalars(
            select(Transaction)
            .where(Transaction.transfer_id == updated.id)
            .order_by(Transaction.transfer_leg)
        )
    )
    assert updated.source_account_id == inter.id
    assert updated.destination_account_id == nubank.id
    assert updated.amount == Decimal("350.00")
    assert updated.description == "Rebalanceamento"
    assert [(leg.transfer_leg, leg.account_id, leg.amount) for leg in legs] == [
        ("in", nubank.id, Decimal("350.00")),
        ("out", inter.id, Decimal("350.00")),
    ]
    assert all(leg.description == "Rebalanceamento" for leg in legs)
    assert balance_for_account(db, nubank) == Decimal("1350.00")
    assert balance_for_account(db, inter) == Decimal("-250.00")


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


def test_agent_verification_result_is_audited_without_storing_the_code(db):
    user = make_user()
    db.add(user)
    db.flush()
    phone = "+5592999999999"
    db.add(
        WhatsAppIdentity(
            user_id=user.id,
            phone_e164=phone,
            verification_code_hash=_verification_digest(phone, "123456"),
            verification_expires_at=datetime.now(UTC) + timedelta(minutes=5),
            is_active=True,
        )
    )
    db.flush()
    principal = AgentPrincipal(
        user=user,
        provider="whatsapp",
        sender_id=phone,
        message_id="wamid-verification-audit",
    )

    result = verify_whatsapp(
        AgentWhatsAppVerificationRequest(code="123456"),
        principal=principal,
        db=db,
    )

    call = db.query(AgentToolCall).one()
    assert result["verified"] is True
    assert call.status == "success"
    assert call.tool_name == "verify_whatsapp"
    assert call.error_code is None


def test_agent_delete_requires_explicit_confirmation_token(db):
    user, account, _destination, food, _salary = setup_finances(db)
    transaction = create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=account.id,
            category_id=food.id,
            type="expense",
            amount=Decimal("25.00"),
            description="Almoço",
            transaction_date=date(2026, 9, 20),
        ),
    )
    db.commit()
    first_principal = AgentPrincipal(
        user=user,
        provider="whatsapp",
        sender_id="+5592999999999",
        message_id="wamid-delete-request",
    )

    pending = agent_delete_transaction(
        transaction.id,
        payload=AgentTransactionDeleteRequest(transaction_id=transaction.id),
        principal=first_principal,
        db=db,
    )

    assert pending["deleted"] is False
    assert pending["confirmation_required"] is True
    assert list_transactions(db, user)

    confirmation_principal = AgentPrincipal(
        user=user,
        provider="whatsapp",
        sender_id="+5592999999999",
        message_id="wamid-delete-confirm",
    )
    deleted = agent_delete_transaction(
        transaction.id,
        payload=AgentTransactionDeleteRequest(
            transaction_id=transaction.id,
            confirmation_token=pending["confirmation_token"],
        ),
        principal=confirmation_principal,
        db=db,
    )

    assert deleted["deleted"] is True
    assert list_transactions(db, user) == []
    calls = list(db.query(AgentToolCall).order_by(AgentToolCall.created_at))
    assert [call.tool_name for call in calls[-2:]] == [
        "delete_transaction",
        "delete_transaction",
    ]
    assert all(call.status == "success" for call in calls[-2:])


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


def test_maintenance_removes_expired_ephemeral_data_only_when_applied(db):
    user = make_user()
    db.add(user)
    db.flush()
    now = datetime(2026, 9, 21, 12, tzinfo=UTC)
    expired_session = AuthSession(
        user_id=user.id,
        token_hash="expired-session",
        expires_at=now - timedelta(minutes=1),
    )
    active_session = AuthSession(
        user_id=user.id,
        token_hash="active-session",
        expires_at=now + timedelta(days=1),
    )
    expired_action = PendingAgentAction(
        user_id=user.id,
        channel="whatsapp",
        sender_id="+5592999999999",
        action_type="delete_transaction",
        payload={"description": "Almoço"},
        confirmation_token_hash="expired-action",
        expires_at=now - timedelta(minutes=1),
    )
    active_action = PendingAgentAction(
        user_id=user.id,
        channel="whatsapp",
        sender_id="+5592999999999",
        action_type="delete_transaction",
        payload={"description": "Mercado"},
        confirmation_token_hash="active-action",
        expires_at=now + timedelta(minutes=5),
    )
    db.add_all([expired_session, active_session, expired_action, active_action])
    db.flush()
    expired_session_id = expired_session.id
    active_session_id = active_session.id
    expired_action_id = expired_action.id
    active_action_id = active_action.id
    db.commit()

    preview = cleanup_expired_data(db, now=now, dry_run=True)

    assert preview.expired_sessions == 1
    assert preview.expired_pending_actions == 1
    assert db.get(AuthSession, expired_session_id) is not None
    assert db.get(PendingAgentAction, expired_action_id) is not None

    applied = cleanup_expired_data(db, now=now)

    assert applied == preview
    assert db.get(AuthSession, expired_session_id) is None
    assert db.get(AuthSession, active_session_id) is not None
    assert db.get(PendingAgentAction, expired_action_id) is None
    assert db.get(PendingAgentAction, active_action_id) is not None


def test_maintenance_preserves_financial_idempotency_ledger(db):
    user, account, _destination, food, _salary = setup_finances(db)
    transaction = create_transaction(
        db,
        user,
        TransactionCreate(
            account_id=account.id,
            category_id=food.id,
            type="expense",
            amount=Decimal("25.00"),
            description="Almoço",
            transaction_date=date(2026, 9, 20),
        ),
    )
    db.flush()
    now = datetime(2026, 9, 21, 12, tzinfo=UTC)
    old = now - timedelta(days=181)
    technical_message = AgentMessage(
        provider="whatsapp",
        external_message_id="technical-old",
        sender_id="+5592999999999",
        user_id=user.id,
        text_hash="a" * 64,
        status="success",
        created_at=old,
        processed_at=old,
    )
    financial_message = AgentMessage(
        provider="whatsapp",
        external_message_id="financial-old",
        sender_id="+5592999999999",
        user_id=user.id,
        text_hash="b" * 64,
        status="success",
        transaction_id=transaction.id,
        created_at=old,
        processed_at=old,
    )
    recent_message = AgentMessage(
        provider="whatsapp",
        external_message_id="technical-recent",
        sender_id="+5592999999999",
        user_id=user.id,
        text_hash="c" * 64,
        status="error",
        created_at=now - timedelta(days=2),
        processed_at=now - timedelta(days=2),
    )
    db.add_all([technical_message, financial_message, recent_message])
    db.flush()
    technical_message_id = technical_message.id
    financial_message_id = financial_message.id
    recent_message_id = recent_message.id
    technical_call = AgentToolCall(
        agent_message_id=technical_message.id,
        user_id=user.id,
        intent="query",
        tool_name="get_balance",
        status="success",
        created_at=old,
        processed_at=old,
    )
    financial_call = AgentToolCall(
        agent_message_id=financial_message.id,
        user_id=user.id,
        intent="create_transaction",
        tool_name="create_transaction",
        status="success",
        transaction_id=transaction.id,
        created_at=old,
        processed_at=old,
    )
    db.add_all([technical_call, financial_call])
    db.flush()
    technical_call_id = technical_call.id
    financial_call_id = financial_call.id
    db.commit()

    result = cleanup_expired_data(db, now=now, agent_log_retention_days=180)

    assert result.pruned_agent_messages == 1
    assert result.pruned_agent_tool_calls == 1
    assert db.get(AgentMessage, technical_message_id) is None
    assert db.get(AgentToolCall, technical_call_id) is None
    assert db.get(AgentToolCall, financial_call_id) is not None
    assert db.get(AgentMessage, financial_message_id) is not None
    assert db.get(AgentMessage, recent_message_id) is not None
