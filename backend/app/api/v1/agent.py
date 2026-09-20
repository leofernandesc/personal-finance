import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AgentPrincipal, get_agent_principal
from app.core.security import normalize_phone
from app.db.session import get_db
from app.models import Account, AgentMessage, Budget, Category, Goal, Transaction, Transfer, User
from app.schemas.agent import (
    AgentBudgetRequest,
    AgentGoalRequest,
    AgentInboundRequest,
    AgentTransactionRequest,
    AgentTransactionUpdateRequest,
    AgentTransferRequest,
)
from app.schemas.finance import TransactionCreate, TransactionUpdate, TransferCreate
from app.services.finance import (
    balance_for_account,
    budget_status,
    create_transaction,
    create_transfer,
    delete_transaction,
    list_transactions,
    month_start,
    next_month,
    totals_for_period,
    update_transaction,
    user_today,
)

router = APIRouter(prefix="/integrations/agent", tags=["agent"])


def _agent_message(
    db: Session, principal: AgentPrincipal, *, intent: str, tool_name: str
) -> AgentMessage | None:
    if not principal.message_id:
        return None
    message = db.scalar(
        select(AgentMessage).where(
            AgentMessage.provider == principal.provider,
            AgentMessage.external_message_id == principal.message_id,
        )
    )
    if not message:
        message = AgentMessage(
            provider=principal.provider,
            external_message_id=principal.message_id,
            sender_id=principal.sender_id,
            user_id=principal.user.id,
            text_hash=hashlib.sha256(principal.message_id.encode()).hexdigest(),
            status="processing",
        )
        db.add(message)
        db.flush()
    message.user_id = principal.user.id
    message.intent = intent
    message.tool_name = tool_name
    return message


def _account_by_name(db: Session, user: User, name: str | None) -> Account:
    accounts = list(
        db.scalars(
            select(Account)
            .where(Account.user_id == user.id, Account.is_active.is_(True))
            .order_by(Account.name)
        )
    )
    if name:
        for account in accounts:
            if account.name.casefold() == name.casefold():
                return account
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
        for category in categories:
            if category.name.casefold() == name.casefold():
                return category
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CATEGORY_NOT_FOUND",
                "message": "Categoria não encontrada",
                "available": [c.name for c in categories],
            },
        )
    for category in categories:
        if category.name.casefold() == "outros" and category.parent_id is None:
            return category
    raise HTTPException(
        status_code=404,
        detail={"code": "CATEGORY_NOT_FOUND", "message": "Nenhuma categoria padrão disponível"},
    )


def _complete_message(
    db: Session,
    message: AgentMessage | None,
    *,
    status_value: str = "success",
    transaction_id=None,
    transfer_id=None,
    error_code=None,
) -> None:
    if not message:
        return
    message.status = status_value
    message.transaction_id = transaction_id
    message.transfer_id = transfer_id
    message.error_code = error_code
    message.processed_at = datetime.now(UTC)


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
    existing = db.scalar(
        select(AgentMessage).where(
            AgentMessage.provider == principal.provider,
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
        text_hash=hashlib.sha256(payload.text.encode()).hexdigest(),
        status="received",
    )
    db.add(message)
    db.commit()
    return {"duplicate": False, "message_id": message.id}


@router.post("/transactions")
def agent_transaction(
    payload: AgentTransactionRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    message = _agent_message(db, principal, intent=payload.type, tool_name="create_transaction")
    category = _category_by_name(db, principal.user, payload.category_name, payload.type)
    account = _account_by_name(db, principal.user, payload.account_name)
    key = (
        f"{principal.provider}:{principal.message_id}:transaction" if principal.message_id else None
    )
    replayed = False
    if key:
        replayed = (
            db.scalar(
                select(Transaction).where(
                    Transaction.user_id == principal.user.id,
                    Transaction.idempotency_key == key,
                )
            )
            is not None
        )
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
            transaction_date=payload.transaction_date,
            source="whatsapp",
            idempotency_key=key,
        ),
        forced_source="whatsapp",
    )
    _complete_message(db, message, transaction_id=transaction.id)
    db.commit()
    return {
        "id": transaction.id,
        "type": transaction.type,
        "amount": str(transaction.amount),
        "description": transaction.description,
        "category": category.name,
        "account": account.name,
        "transaction_date": transaction.transaction_date,
        "source": transaction.source,
        "replayed": replayed,
    }


@router.post("/transfers")
def agent_transfer(
    payload: AgentTransferRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    message = _agent_message(db, principal, intent="transfer", tool_name="create_transfer")
    source = _account_by_name(db, principal.user, payload.source_account_name)
    destination = _account_by_name(db, principal.user, payload.destination_account_name)
    key = f"{principal.provider}:{principal.message_id}:transfer" if principal.message_id else None
    replayed = False
    if key:
        replayed = (
            db.scalar(
                select(Transfer).where(
                    Transfer.user_id == principal.user.id,
                    Transfer.idempotency_key == key,
                )
            )
            is not None
        )
    transfer = create_transfer(
        db,
        principal.user,
        TransferCreate(
            source_account_id=source.id,
            destination_account_id=destination.id,
            amount=payload.amount,
            description=payload.description,
            transaction_date=payload.transaction_date,
            source="whatsapp",
            idempotency_key=key,
        ),
        forced_source="whatsapp",
    )
    _complete_message(db, message, transfer_id=transfer.id)
    db.commit()
    return {
        "id": transfer.id,
        "amount": str(transfer.amount),
        "from": source.name,
        "to": destination.name,
        "transaction_date": transfer.transaction_date,
        "replayed": replayed,
    }


@router.patch("/transactions/{transaction_id}")
def agent_update_transaction(
    transaction_id: UUID,
    payload: AgentTransactionUpdateRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
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
    if payload.transaction_date is not None:
        update_data["transaction_date"] = payload.transaction_date
    if payload.category_name:
        category = _category_by_name(db, principal.user, payload.category_name, transaction.type)
        update_data["category_id"] = category.id
    updated = update_transaction(
        db,
        principal.user,
        payload.transaction_id,
        TransactionUpdate.model_validate(update_data),
    )
    message = _agent_message(
        db, principal, intent="update_transaction", tool_name="update_transaction"
    )
    _complete_message(db, message, transaction_id=updated.id)
    db.commit()
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
    message = _agent_message(
        db, principal, intent="delete_transaction", tool_name="delete_transaction"
    )
    _complete_message(db, message, transaction_id=transaction_id)
    db.commit()
    return {"deleted": True, "transaction_id": transaction_id}


@router.get("/accounts")
def agent_accounts(
    principal: AgentPrincipal = Depends(get_agent_principal), db: Session = Depends(get_db)
):
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
    category = _category_by_name(db, principal.user, category_name, "expense")
    start = month_start(user_today(principal.user))
    end = next_month(start)
    amount = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == principal.user.id,
            Transaction.category_id == category.id,
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
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
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
        }
        for transaction in list_transactions(db, principal.user, limit=max(1, min(limit, 50)))
    ]


@router.get("/budget-status")
def agent_budget_status(
    principal: AgentPrincipal = Depends(get_agent_principal), db: Session = Depends(get_db)
):
    return budget_status(db, principal.user, user_today(principal.user))


@router.post("/budgets")
def agent_budget(
    payload: AgentBudgetRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
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
    db.commit()
    return next(
        item for item in budget_status(db, principal.user, month) if item["id"] == budget.id
    )


@router.post("/goals")
def agent_goal(
    payload: AgentGoalRequest,
    principal: AgentPrincipal = Depends(get_agent_principal),
    db: Session = Depends(get_db),
):
    goal = Goal(user_id=principal.user.id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": str(goal.target_amount),
        "current_amount": str(goal.current_amount),
        "deadline": goal.deadline,
        "status": goal.status,
    }
