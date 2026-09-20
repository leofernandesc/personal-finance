from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Account, Budget, Category, Transaction, Transfer, User
from app.schemas.finance import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryUpdate,
    TransactionCreate,
    TransactionUpdate,
    TransferCreate,
)

CENT = Decimal("0.01")


def money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def user_today(user: User) -> date:
    try:
        return datetime.now(ZoneInfo(user.timezone)).date()
    except ZoneInfoNotFoundError:
        return datetime.now(UTC).date()


def month_start(value: date) -> date:
    return value.replace(day=1)


def next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def ensure_account(
    db: Session, user_id: UUID, account_id: UUID, *, active: bool = False
) -> Account:
    account = db.scalar(select(Account).where(Account.id == account_id, Account.user_id == user_id))
    if not account or (active and not account.is_active):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    return account


def ensure_category(
    db: Session, user_id: UUID, category_id: UUID | None, *, kind: str | None = None
) -> Category | None:
    if category_id is None:
        return None
    category = db.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    if not category or not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada"
        )
    if kind and category.kind not in (kind, "both"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Categoria incompatível com o tipo",
        )
    return category


def create_account(db: Session, user: User, payload: AccountCreate) -> Account:
    duplicate = db.scalar(
        select(Account).where(
            Account.user_id == user.id, func.lower(Account.name) == payload.name.lower()
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com esse nome"
        )
    account = Account(user_id=user.id, **payload.model_dump())
    db.add(account)
    db.flush()
    return account


def update_account(db: Session, user: User, account_id: UUID, payload: AccountUpdate) -> Account:
    account = ensure_account(db, user.id, account_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        duplicate = db.scalar(
            select(Account).where(
                Account.user_id == user.id,
                Account.id != account_id,
                func.lower(Account.name) == data["name"].lower(),
            )
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com esse nome"
            )
    for key, value in data.items():
        setattr(account, key, value)
    db.flush()
    return account


def create_category(db: Session, user: User, payload: CategoryCreate) -> Category:
    if payload.parent_id:
        parent = ensure_category(db, user.id, payload.parent_id)
        if parent and parent.parent_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Apenas dois níveis de categoria são permitidos",
            )
    duplicate = db.scalar(
        select(Category).where(
            Category.user_id == user.id,
            Category.parent_id == payload.parent_id,
            func.lower(Category.name) == payload.name.lower(),
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Já existe uma categoria com esse nome"
        )
    category = Category(user_id=user.id, **payload.model_dump())
    db.add(category)
    db.flush()
    return category


def update_category(
    db: Session, user: User, category_id: UUID, payload: CategoryUpdate
) -> Category:
    category = ensure_category(db, user.id, category_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("parent_id") == category_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Categoria não pode ser pai de si mesma",
        )
    if data.get("parent_id"):
        parent = ensure_category(db, user.id, data["parent_id"])
        if parent and (parent.id == category_id or parent.parent_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Apenas dois níveis de categoria são permitidos",
            )
    for key, value in data.items():
        setattr(category, key, value)
    db.flush()
    return category


def _validate_transaction_category(
    db: Session, user: User, payload: TransactionCreate | TransactionUpdate, transaction_type: str
) -> Category | None:
    return ensure_category(
        db,
        user.id,
        payload.category_id,
        kind="expense" if transaction_type == "expense" else "income",
    )


def create_transaction(
    db: Session, user: User, payload: TransactionCreate, *, forced_source: str | None = None
) -> Transaction:
    if payload.idempotency_key:
        previous = db.scalar(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.idempotency_key == payload.idempotency_key,
            )
        )
        if previous:
            return previous
    account = ensure_account(db, user.id, payload.account_id, active=True)
    category = _validate_transaction_category(db, user, payload, payload.type)
    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id if category else None,
        type=payload.type,
        amount=money(payload.amount),
        description=payload.description or ("Receita" if payload.type == "income" else "Despesa"),
        transaction_date=payload.transaction_date or user_today(user),
        source=forced_source or payload.source,
        idempotency_key=payload.idempotency_key,
    )
    db.add(transaction)
    db.flush()
    return transaction


def create_transfer(
    db: Session, user: User, payload: TransferCreate, *, forced_source: str | None = None
) -> Transfer:
    if payload.idempotency_key:
        previous = db.scalar(
            select(Transfer).where(
                Transfer.user_id == user.id,
                Transfer.idempotency_key == payload.idempotency_key,
            )
        )
        if previous:
            return previous
    source = ensure_account(db, user.id, payload.source_account_id, active=True)
    destination = ensure_account(db, user.id, payload.destination_account_id, active=True)
    if source.id == destination.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="As contas devem ser diferentes",
        )
    transfer = Transfer(
        user_id=user.id,
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount=money(payload.amount),
        description=payload.description,
        transaction_date=payload.transaction_date or user_today(user),
        source=forced_source or payload.source,
        idempotency_key=payload.idempotency_key,
    )
    db.add(transfer)
    db.flush()
    db.add_all(
        [
            Transaction(
                user_id=user.id,
                account_id=source.id,
                transfer_id=transfer.id,
                type="transfer",
                transfer_leg="out",
                amount=money(payload.amount),
                description=payload.description,
                transaction_date=transfer.transaction_date,
                source=transfer.source,
            ),
            Transaction(
                user_id=user.id,
                account_id=destination.id,
                transfer_id=transfer.id,
                type="transfer",
                transfer_leg="in",
                amount=money(payload.amount),
                description=payload.description,
                transaction_date=transfer.transaction_date,
                source=transfer.source,
            ),
        ]
    )
    db.flush()
    return transfer


def transaction_query(user_id: UUID) -> Select:
    return (
        select(Transaction)
        .options(selectinload(Transaction.account), selectinload(Transaction.category))
        .where(Transaction.user_id == user_id, Transaction.deleted_at.is_(None))
    )


def list_transactions(
    db: Session,
    user: User,
    *,
    start: date | None = None,
    end: date | None = None,
    transaction_type: str | None = None,
    account_id: UUID | None = None,
    category_id: UUID | None = None,
    source: str | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[Transaction]:
    query = transaction_query(user.id)
    if start:
        query = query.where(Transaction.transaction_date >= start)
    if end:
        query = query.where(Transaction.transaction_date <= end)
    if transaction_type:
        query = query.where(Transaction.type == transaction_type)
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if category_id:
        query = query.where(Transaction.category_id == category_id)
    if source:
        query = query.where(Transaction.source == source)
    if search:
        query = query.where(Transaction.description.ilike(f"%{search}%"))
    return list(
        db.scalars(
            query.order_by(
                Transaction.transaction_date.desc(), Transaction.created_at.desc()
            ).limit(limit)
        )
    )


def update_transaction(
    db: Session, user: User, transaction_id: UUID, payload: TransactionUpdate
) -> Transaction:
    transaction = db.scalar(transaction_query(user.id).where(Transaction.id == transaction_id))
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada"
        )
    if transaction.type == "transfer":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Edite a transferência pelo recurso de transferências",
        )
    data = payload.model_dump(exclude_unset=True)
    if "account_id" in data:
        ensure_account(db, user.id, data["account_id"], active=True)
    if "category_id" in data:
        category_payload = TransactionUpdate.model_validate({"category_id": data["category_id"]})
        _validate_transaction_category(db, user, category_payload, transaction.type)
    for key, value in data.items():
        setattr(transaction, key, money(value) if key == "amount" else value)
    db.flush()
    return transaction


def delete_transaction(db: Session, user: User, transaction_id: UUID) -> None:
    transaction = db.scalar(transaction_query(user.id).where(Transaction.id == transaction_id))
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada"
        )
    now = datetime.now(UTC)
    if transaction.transfer_id:
        for leg in db.scalars(
            select(Transaction).where(Transaction.transfer_id == transaction.transfer_id)
        ):
            leg.deleted_at = now
    else:
        transaction.deleted_at = now


def balance_for_account(db: Session, account: Account) -> Decimal:
    rows = db.execute(
        select(Transaction.type, Transaction.transfer_leg, func.sum(Transaction.amount))
        .where(Transaction.account_id == account.id, Transaction.deleted_at.is_(None))
        .group_by(Transaction.type, Transaction.transfer_leg)
    )
    balance = money(account.opening_balance)
    for transaction_type, transfer_leg, total in rows:
        total = money(total)
        if transaction_type == "income" or (
            transaction_type == "transfer" and transfer_leg == "in"
        ):
            balance += total
        elif transaction_type == "expense" or (
            transaction_type == "transfer" and transfer_leg == "out"
        ):
            balance -= total
    return money(balance)


def totals_for_period(
    db: Session, user_id: UUID, start: date, end: date
) -> tuple[Decimal, Decimal]:
    rows = db.execute(
        select(Transaction.type, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            Transaction.deleted_at.is_(None),
            Transaction.type.in_(["income", "expense"]),
        )
        .group_by(Transaction.type)
    )
    totals = {transaction_type: money(total) for transaction_type, total in rows}
    return totals.get("income", money(0)), totals.get("expense", money(0))


def budget_status(db: Session, user: User, month: date) -> list[dict]:
    month = month_start(month)
    end = next_month(month)
    budgets = list(
        db.scalars(
            select(Budget)
            .options(selectinload(Budget.category))
            .where(Budget.user_id == user.id, Budget.month == month)
            .order_by(Budget.created_at)
        )
    )
    spent_rows = db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user.id,
            Transaction.type == "expense",
            Transaction.transaction_date >= month,
            Transaction.transaction_date < end,
            Transaction.deleted_at.is_(None),
        )
        .group_by(Transaction.category_id)
    )
    spent = {category_id: money(total) for category_id, total in spent_rows}
    result = []
    for budget in budgets:
        limit = money(budget.limit_amount)
        used = spent.get(budget.category_id, money(0))
        remaining = money(limit - used)
        result.append(
            {
                "id": budget.id,
                "category_id": budget.category_id,
                "category_name": budget.category.name,
                "month": budget.month,
                "limit_amount": limit,
                "spent_amount": used,
                "remaining_amount": remaining,
                "utilization_percent": money((used / limit * 100) if limit else 0),
                "exceeded_amount": money(used - limit) if used > limit else money(0),
            }
        )
    return result


def dashboard_data(db: Session, user: User, start: date, end: date) -> dict:
    income, expense = totals_for_period(db, user.id, start, end)
    accounts = list(
        db.scalars(
            select(Account)
            .where(Account.user_id == user.id, Account.is_active.is_(True))
            .order_by(Account.name)
        )
    )
    account_items = [
        {
            "id": a.id,
            "name": a.name,
            "account_type": a.account_type,
            "balance": balance_for_account(db, a),
        }
        for a in accounts
    ]
    category_rows = db.execute(
        select(Category.id, Category.name, func.sum(Transaction.amount))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user.id,
            Transaction.type == "expense",
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            Transaction.deleted_at.is_(None),
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
    )
    by_category = [
        {"category_id": cid, "category_name": name, "amount": money(total)}
        for cid, name, total in category_rows
    ]
    flow_rows = db.execute(
        select(Transaction.transaction_date, Transaction.type, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user.id,
            Transaction.type.in_(["income", "expense"]),
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            Transaction.deleted_at.is_(None),
        )
        .group_by(Transaction.transaction_date, Transaction.type)
        .order_by(Transaction.transaction_date)
    )
    flow: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {"income": money(0), "expense": money(0)}
    )
    for day, transaction_type, total in flow_rows:
        flow[day][transaction_type] = money(total)
    recent = list_transactions(db, user, start=start, end=end, limit=10)
    return {
        "period": {"start": start, "end": end},
        "totals": {"income": income, "expense": expense, "savings": money(income - expense)},
        "total_balance": money(sum((item["balance"] for item in account_items), money(0))),
        "accounts": account_items,
        "by_category": by_category,
        "flow": [{"date": day, **values} for day, values in sorted(flow.items())],
        "budgets": budget_status(db, user, start),
        "recent_transactions": recent,
    }
