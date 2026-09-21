import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    AgentPrincipal,
    get_agent_principal,
    get_agent_verification_principal,
)
from app.core.config import get_settings
from app.core.security import normalize_phone
from app.db.session import get_db
from app.models import (
    Account,
    AgentMessage,
    Budget,
    Category,
    Transaction,
    Transfer,
    User,
    WhatsAppIdentity,
)
from app.schemas.agent import (
    AgentBudgetRequest,
    AgentGoalRequest,
    AgentInboundRequest,
    AgentTransactionRequest,
    AgentTransactionUpdateRequest,
    AgentTransferRequest,
    AgentWhatsAppVerificationRequest,
)
from app.schemas.finance import GoalCreate, TransactionCreate, TransactionUpdate, TransferCreate
from app.services.agent_audit import audited_agent_operation, record_agent_tool_result
from app.services.finance import (
    balance_for_account,
    budget_status,
    create_transaction,
    create_transfer,
    delete_transaction,
    list_transactions,
    month_start,
    next_month,
    normalized_name,
    resolve_agent_date,
    totals_for_period,
    update_transaction,
    user_today,
)
from app.services.goals import create_goal

router = APIRouter(prefix="/integrations/agent", tags=["agent"])
settings = get_settings()
MAX_VERIFICATION_ATTEMPTS = 5


def _verification_digest(phone_e164: str, code: str) -> str:
    value = f"{phone_e164}:{code}".encode()
    return hmac.new(settings.agent_shared_secret.encode(), value, hashlib.sha256).hexdigest()


def _verification_error(
    db: Session,
    principal: AgentPrincipal,
    status_code: int,
    detail: str,
) -> NoReturn:
    error = HTTPException(status_code=status_code, detail=detail)
    record_agent_tool_result(
        db,
        principal,
        intent="verify_whatsapp",
        tool_name="verify_whatsapp",
        error=error,
    )
    raise error


def _account_by_name(db: Session, user: User, name: str | None) -> Account:
    accounts = list(
        db.scalars(
            select(Account)
            .where(Account.user_id == user.id, Account.is_active.is_(True))
            .order_by(Account.name)
        )
    )
    if name:
        matches = [
            account
            for account in accounts
            if normalized_name(account.name) == normalized_name(name)
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ACCOUNT_AMBIGUOUS",
                    "message": "Mais de uma conta corresponde ao nome informado",
                    "available": [account.name for account in matches],
                },
            )
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ACCOUNT_NOT_FOUND",
                "message": "Conta não encontrada",
                "available": [a.name for a in accounts],
            },
        )
    if len(accounts) == 1:
        return accounts[0]
    if not accounts:
        raise HTTPException(
            status_code=404, detail={"code": "NO_ACCOUNTS", "message": "Nenhuma conta cadastrada"}
        )
    raise HTTPException(
        status_code=409,
        detail={
            "code": "ACCOUNT_REQUIRED",
            "message": "Informe a conta",
            "available": [a.name for a in accounts],
        },
    )


def _category_by_name(db: Session, user: User, name: str | None, kind: str) -> Category:
    categories = list(
        db.scalars(
            select(Category)
            .where(
                Category.user_id == user.id,
                Category.is_active.is_(True),
                Category.kind.in_([kind, "both"]),
            )
            .order_by(Category.name)
        )
    )
    if name:
        matches = [
            category
            for category in categories
            if normalized_name(category.name) == normalized_name(name)
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CATEGORY_AMBIGUOUS",
                    "message": "Mais de uma categoria corresponde ao nome informado",
                    "available": [category.name for category in matches],
                },
            )
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CATEGORY_NOT_FOUND",
                "message": "Categoria não encontrada",
                "available": [c.name for c in categories],
            },
        )
    for category in categories:
        if normalized_name(category.name) == "outros" and category.parent_id is None:
            return category
    raise HTTPException(
        status_code=404,
        detail={"code": "CATEGORY_NOT_FOUND", "message": "Nenhuma categoria padrão disponível"},
    )


def _transaction_result(db: Session, transaction: Transaction, *, replayed: bool) -> dict:
    account = db.get(Account, transaction.account_id)
    category = db.get(Category, transaction.category_id) if transaction.category_id else None
    return {
        "id": transaction.id,
        "type": transaction.type,
        "amount": str(transaction.amount),
        "description": transaction.description,
        "category": category.name if category else None,
        "account": account.name if account else None,
        "transaction_date": transaction.transaction_date,
        "source": transaction.source,
        "replayed": replayed,
    }


def _transfer_result(db: Session, transfer: Transfer, *, replayed: bool) -> dict:
    source = db.get(Account, transfer.source_account_id)
    destination = db.get(Account, transfer.destination_account_id)
    return {
        "id": transfer.id,
        "amount": str(transfer.amount),
        "from": source.name if source else None,
        "to": destination.name if destination else None,
        "transaction_date": transfer.transaction_date,
        "replayed": replayed,
    }


@router.post("/inbound")
def register_inbound(
    payload: AgentInboundRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    if normalize_phone(payload.sender_id) != principal.sender_id:
        raise HTTPException(
            status_code=400, detail="Remetente não corresponde à identidade autenticada"
        )
    if payload.external_message_id != principal.message_id:
        raise HTTPException(
            status_code=400, detail="ID externo não corresponde à mensagem autenticada"
        )
    existing = db.scalar(
        select(AgentMessage).where(
            AgentMessage.provider == principal.provider,
            AgentMessage.sender_id == principal.sender_id,
            AgentMessage.external_message_id == payload.external_message_id,
        )
    )
    if existing:
        db.commit()
        return {
            "duplicate": True,
            "status": existing.status,
            "transaction_id": existing.transaction_id,
            "transfer_id": existing.transfer_id,
        }
    message = AgentMessage(
        provider=principal.provider,
        external_message_id=payload.external_message_id,
        sender_id=principal.sender_id,
        user_id=principal.user.id,
        text_hash=hmac.new(
            settings.agent_shared_secret.encode("utf-8"),
            payload.text.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
        status="received",
    )
    db.add(message)
    db.commit()
    return {"duplicate": False, "message_id": message.id}


@router.post("/verify-whatsapp")
def verify_whatsapp(
    payload: AgentWhatsAppVerificationRequest,
    principal: AgentPrincipal = Depends(get_agent_verification_principal),
    db: Session = Depends(get_db),
):
    identity = db.scalar(
        select(WhatsAppIdentity).where(
            WhatsAppIdentity.user_id == principal.user.id,
            WhatsAppIdentity.phone_e164 == principal.sender_id,
            WhatsAppIdentity.is_active.is_(True),
        )
    )
    if not identity:
        _verification_error(db, principal, 404, "Número WhatsApp não vinculado")
    if identity.verified_at is not None:
        record_agent_tool_result(
            db,
            principal,
            intent="verify_whatsapp",
            tool_name="verify_whatsapp",
        )
        return {"verified": True, "phone_e164": identity.phone_e164}
    if not identity.verification_code_hash or not identity.verification_expires_at:
        _verification_error(
            db,
            principal,
            409,
            "Nenhum código de verificação ativo. Gere um novo código na aplicação.",
        )
    now = datetime.now(UTC)
    expires_at = identity.verification_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        identity.verification_code_hash = None
        identity.verification_expires_at = None
        identity.verification_attempts = 0
        _verification_error(db, principal, 410, "Código de verificação expirado")
    if identity.verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
        _verification_error(
            db,
            principal,
            429,
            "Limite de tentativas atingido. Gere um novo código na aplicação.",
        )

    identity.verification_attempts += 1
    expected = _verification_digest(identity.phone_e164, payload.code)
    if not hmac.compare_digest(identity.verification_code_hash, expected):
        _verification_error(db, principal, 400, "Código de verificação inválido")

    identity.verified_at = now
    identity.verification_code_hash = None
    identity.verification_expires_at = None
    identity.verification_attempts = 0
    record_agent_tool_result(
        db,
        principal,
        intent="verify_whatsapp",
        tool_name="verify_whatsapp",
    )
    return {"verified": True, "phone_e164": identity.phone_e164}


@router.post("/transactions")
def agent_transaction(
    payload: AgentTransactionRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    with audited_agent_operation(
        db,
        principal,
        intent=payload.type,
        tool_name="create_transaction",
    ) as operation:
        key = f"{principal.provider}:{principal.sender_id}:{principal.message_id}:transaction"
        legacy_key = f"{principal.provider}:{principal.message_id}:transaction"
        previous = db.scalar(
            select(Transaction).where(
                Transaction.user_id == principal.user.id,
                Transaction.idempotency_key.in_([key, legacy_key]),
            )
        )
        if previous:
            operation.link_transaction(previous.id)
            return _transaction_result(db, previous, replayed=True)

        category = _category_by_name(db, principal.user, payload.category_name, payload.type)
        account = _account_by_name(db, principal.user, payload.account_name)
        transaction = create_transaction(
            db,
            principal.user,
            TransactionCreate(
                account_id=account.id,
                category_id=category.id,
                type=payload.type,
                amount=payload.amount,
                description=payload.description
                or ("Receita" if payload.type == "income" else "Despesa"),
                transaction_date=resolve_agent_date(
                    principal.user,
                    payload.transaction_date,
                    payload.relative_date,
                ),
                source="whatsapp",
                idempotency_key=key,
            ),
            forced_source="whatsapp",
        )
        operation.link_transaction(transaction.id)
        return _transaction_result(db, transaction, replayed=False)


@router.post("/transfers")
def agent_transfer(
    payload: AgentTransferRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    with audited_agent_operation(
        db,
        principal,
        intent="transfer",
        tool_name="create_transfer",
    ) as operation:
        key = f"{principal.provider}:{principal.sender_id}:{principal.message_id}:transfer"
        legacy_key = f"{principal.provider}:{principal.message_id}:transfer"
        previous = db.scalar(
            select(Transfer).where(
                Transfer.user_id == principal.user.id,
                Transfer.idempotency_key.in_([key, legacy_key]),
            )
        )
        if previous:
            operation.link_transfer(previous.id)
            return _transfer_result(db, previous, replayed=True)

        source = _account_by_name(db, principal.user, payload.source_account_name)
        destination = _account_by_name(db, principal.user, payload.destination_account_name)
        transfer = create_transfer(
            db,
            principal.user,
            TransferCreate(
                source_account_id=source.id,
                destination_account_id=destination.id,
                amount=payload.amount,
                description=payload.description,
                transaction_date=resolve_agent_date(
                    principal.user,
                    payload.transaction_date,
                    payload.relative_date,
                ),
                source="whatsapp",
                idempotency_key=key,
            ),
            forced_source="whatsapp",
        )
        operation.link_transfer(transfer.id)
        return _transfer_result(db, transfer, replayed=False)


@router.patch("/transactions/{transaction_id}")
def agent_update_transaction(
    transaction_id: UUID,
    payload: AgentTransactionUpdateRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    with audited_agent_operation(
        db,
        principal,
        intent="update_transaction",
        tool_name="update_transaction",
    ) as operation:
        if payload.transaction_id != transaction_id:
            raise HTTPException(status_code=400, detail="ID da transação inconsistente")
        transaction = db.scalar(
            select(Transaction).where(
                Transaction.id == payload.transaction_id,
                Transaction.user_id == principal.user.id,
                Transaction.deleted_at.is_(None),
            )
        )
        if not transaction:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
        update_data = {}
        if payload.amount is not None:
            update_data["amount"] = payload.amount
        if payload.description is not None:
            update_data["description"] = payload.description
        if payload.transaction_date is not None or payload.relative_date is not None:
            update_data["transaction_date"] = resolve_agent_date(
                principal.user,
                payload.transaction_date,
                payload.relative_date,
            )
        if payload.category_name:
            category = _category_by_name(
                db, principal.user, payload.category_name, transaction.type
            )
            update_data["category_id"] = category.id
        updated = update_transaction(
            db,
            principal.user,
            payload.transaction_id,
            TransactionUpdate.model_validate(update_data),
        )
        operation.link_transaction(updated.id)
        return {
            "id": updated.id,
            "amount": str(updated.amount),
            "description": updated.description,
            "category": updated.category.name if updated.category else None,
            "transaction_date": updated.transaction_date,
            "source": updated.source,
        }


@router.delete("/transactions/{transaction_id}")
def agent_delete_transaction(
    transaction_id: UUID,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    with audited_agent_operation(
        db,
        principal,
        intent="delete_transaction",
        tool_name="delete_transaction",
    ) as operation:
        transaction = db.scalar(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == principal.user.id,
                Transaction.deleted_at.is_(None),
            )
        )
        if not transaction:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
        delete_transaction(db, principal.user, transaction_id)
        operation.link_transaction(transaction_id)
        return {"deleted": True, "transaction_id": transaction_id}


@router.get("/accounts")
def agent_accounts(
    principal: AgentPrincipal = Depends(get_agent_principal), db: Session = Depends(get_db)
):
    with audited_agent_operation(db, principal, intent="get_accounts", tool_name="get_accounts"):
        accounts = list(
            db.scalars(
                select(Account)
                .where(Account.user_id == principal.user.id, Account.is_active.is_(True))
                .order_by(Account.name)
            )
        )
        return [
            {
                "id": account.id,
                "name": account.name,
                "type": account.account_type,
                "balance": str(balance_for_account(db, account)),
            }
            for account in accounts
        ]


@router.get("/categories")
def agent_categories(
    principal: AgentPrincipal = Depends(get_agent_principal), db: Session = Depends(get_db)
):
    with audited_agent_operation(
        db, principal, intent="get_categories", tool_name="get_categories"
    ):
        categories = list(
            db.scalars(
                select(Category)
                .where(Category.user_id == principal.user.id, Category.is_active.is_(True))
                .order_by(Category.name)
            )
        )
        return [
            {
                "id": category.id,
                "name": category.name,
                "kind": category.kind,
                "parent_id": category.parent_id,
            }
            for category in categories
        ]


@router.get("/balance")
def agent_balance(
    principal: AgentPrincipal = Depends(get_agent_principal), db: Session = Depends(get_db)
):
    with audited_agent_operation(db, principal, intent="get_balance", tool_name="get_balance"):
        accounts = list(
            db.scalars(
                select(Account)
                .where(Account.user_id == principal.user.id, Account.is_active.is_(True))
                .order_by(Account.name)
            )
        )
        values = [
            {"account": account.name, "balance": str(balance_for_account(db, account))}
            for account in accounts
        ]
        return {
            "total": str(sum((Decimal(item["balance"]) for item in values), Decimal("0.00"))),
            "accounts": values,
        }


@router.get("/month-summary")
def agent_month_summary(
    principal: AgentPrincipal = Depends(get_agent_principal), db: Session = Depends(get_db)
):
    with audited_agent_operation(
        db, principal, intent="get_month_summary", tool_name="get_month_summary"
    ):
        start = month_start(user_today(principal.user))
        end = next_month(start) - timedelta(days=1)
        income, expense = totals_for_period(db, principal.user.id, start, end)
        return {
            "month": start,
            "income": str(income),
            "expense": str(expense),
            "savings": str(income - expense),
        }


@router.get("/category-summary")
def agent_category_summary(
    category_name: str,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    with audited_agent_operation(
        db,
        principal,
        intent="get_category_summary",
        tool_name="get_category_summary",
    ):
        category = _category_by_name(db, principal.user, category_name, "expense")
        start = month_start(user_today(principal.user))
        end = next_month(start)
        category_ids = [category.id]
        if category.parent_id is None:
            category_ids.extend(
                db.scalars(
                    select(Category.id).where(
                        Category.user_id == principal.user.id,
                        Category.parent_id == category.id,
                    )
                )
            )
        amount = db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == principal.user.id,
                Transaction.category_id.in_(category_ids),
                Transaction.type == "expense",
                Transaction.transaction_date >= start,
                Transaction.transaction_date < end,
                Transaction.deleted_at.is_(None),
            )
        ) or Decimal("0.00")
        return {
            "category": category.name,
            "month": start,
            "expense": str(Decimal(amount).quantize(Decimal("0.01"))),
        }


@router.get("/transactions")
def agent_transactions(
    limit: int = 10,
    search: str | None = None,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    with audited_agent_operation(
        db, principal, intent="get_transactions", tool_name="get_transactions"
    ):
        return [
            {
                "id": transaction.id,
                "type": transaction.type,
                "amount": str(transaction.amount),
                "description": transaction.description,
                "date": transaction.transaction_date,
                "category": transaction.category.name if transaction.category else None,
                "account": transaction.account.name if transaction.account else None,
                "source": transaction.source,
            }
            for transaction in list_transactions(
                db,
                principal.user,
                search=search,
                limit=max(1, min(limit, 50)),
            )
        ]


@router.get("/budget-status")
def agent_budget_status(
    principal: AgentPrincipal = Depends(get_agent_principal), db: Session = Depends(get_db)
):
    with audited_agent_operation(
        db, principal, intent="get_budget_status", tool_name="get_budget_status"
    ):
        return budget_status(db, principal.user, user_today(principal.user))


@router.post("/budgets")
def agent_budget(
    payload: AgentBudgetRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    with audited_agent_operation(db, principal, intent="create_budget", tool_name="create_budget"):
        category = _category_by_name(db, principal.user, payload.category_name, "expense")
        month = month_start(payload.month or user_today(principal.user))
        budget = db.scalar(
            select(Budget).where(
                Budget.user_id == principal.user.id,
                Budget.category_id == category.id,
                Budget.month == month,
            )
        )
        if budget:
            budget.limit_amount = payload.limit_amount
        else:
            budget = Budget(
                user_id=principal.user.id,
                category_id=category.id,
                month=month,
                limit_amount=payload.limit_amount,
            )
            db.add(budget)
            db.flush()
        return next(
            item for item in budget_status(db, principal.user, month) if item["id"] == budget.id
        )


@router.post("/goals")
def agent_goal(
    payload: AgentGoalRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    with audited_agent_operation(db, principal, intent="create_goal", tool_name="create_goal"):
        goal = create_goal(db, principal.user, GoalCreate(**payload.model_dump()))
        return {
            "id": goal.id,
            "name": goal.name,
            "target_amount": str(goal.target_amount),
            "current_amount": str(goal.current_amount),
            "deadline": goal.deadline,
            "status": goal.status,
        }
