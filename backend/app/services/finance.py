import unicodedata
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Account, Budget, Category, Transaction, Transfer, User
from app.schemas.finance import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryUpdate,
    TransactionCreate,
    TransactionSort,
    TransactionUpdate,
    TransferCreate,
    TransferUpdate,
)

CENT = Decimal("0.01")


def normalized_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip()).casefold()
    return "".join(character for character in normalized if not unicodedata.combining(character))


def money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def user_today(user: User) -> date:
    try:
        return datetime.now(ZoneInfo(user.timezone)).date()
    except ZoneInfoNotFoundError:
        return datetime.now(UTC).date()


def resolve_agent_date(
    user: User,
    transaction_date: date | None,
    relative_date: str | None,
) -> date:
    if transaction_date is not None:
        return transaction_date
    today = user_today(user)
    offsets = {"today": 0, "yesterday": -1, "tomorrow": 1}
    return today + timedelta(days=offsets.get(relative_date or "today", 0))


def month_start(value: date) -> date:
    return value.replace(day=1)


def next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def shift_month(value: date, offset: int) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    return date(year, zero_based_month + 1, 1)


def ensure_account(
    db: Session, user_id: UUID, account_id: UUID, *, active: bool = False
) -> Account:
    account = db.scalar(select(Account).where(Account.id == account_id, Account.user_id == user_id))
    if not account or (active and not account.is_active):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    return account


def ensure_category(
    db: Session,
    user_id: UUID,
    category_id: UUID | None,
    *,
    kind: str | None = None,
    active: bool = True,
) -> Category | None:
    if category_id is None:
        return None
    category = db.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    if not category or (active and not category.is_active):
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
    duplicate = next(
        (
            account
            for account in db.scalars(select(Account).where(Account.user_id == user.id))
            if normalized_name(account.name) == normalized_name(payload.name)
        ),
        None,
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
    if data.get("is_active") is False and account.is_active:
        if balance_for_account(db, account) != money(0):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transfira ou ajuste o saldo antes de desativar a conta",
            )
    if "name" in data:
        duplicate = next(
            (
                candidate
                for candidate in db.scalars(
                    select(Account).where(
                        Account.user_id == user.id,
                        Account.id != account_id,
                    )
                )
                if normalized_name(candidate.name) == normalized_name(data["name"])
            ),
            None,
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
        if parent and parent.kind != "both" and parent.kind != payload.kind:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A subcategoria deve ter a mesma natureza da categoria principal",
            )
    duplicate = next(
        (
            category
            for category in db.scalars(
                select(Category).where(
                    Category.user_id == user.id,
                    Category.parent_id == payload.parent_id,
                )
            )
            if normalized_name(category.name) == normalized_name(payload.name)
        ),
        None,
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
    category = ensure_category(db, user.id, category_id, active=False)
    data = payload.model_dump(exclude_unset=True)
    if data.get("parent_id") == category_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Categoria não pode ser pai de si mesma",
        )
    effective_parent_id = data.get("parent_id", category.parent_id)
    effective_kind = data.get("kind", category.kind)
    if effective_parent_id:
        parent = ensure_category(db, user.id, effective_parent_id)
        if parent and (parent.id == category_id or parent.parent_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Apenas dois níveis de categoria são permitidos",
            )
        if db.scalar(select(Category.id).where(Category.parent_id == category.id)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uma categoria com subcategorias não pode se tornar subcategoria",
            )
        if parent and parent.kind != "both" and parent.kind != effective_kind:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A subcategoria deve ter a mesma natureza da categoria principal",
            )
    if "name" in data:
        duplicate = next(
            (
                candidate
                for candidate in db.scalars(
                    select(Category).where(
                        Category.user_id == user.id,
                        Category.parent_id == effective_parent_id,
                        Category.id != category_id,
                    )
                )
                if normalized_name(candidate.name) == normalized_name(data["name"])
            ),
            None,
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma categoria com esse nome",
            )
    if "kind" in data:
        incompatible_transaction = None
        incompatible_child = None
        if effective_kind != "both":
            incompatible_transaction = db.scalar(
                select(Transaction.id).where(
                    Transaction.category_id == category.id,
                    Transaction.deleted_at.is_(None),
                    Transaction.type != effective_kind,
                )
            )
            if category.parent_id is None:
                incompatible_child = db.scalar(
                    select(Category.id).where(
                        Category.parent_id == category.id,
                        Category.kind != effective_kind,
                    )
                )
        if incompatible_transaction or incompatible_child:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A natureza não pode ser alterada enquanto houver movimentos "
                    "ou subcategorias incompatíveis"
                ),
            )
    for key, value in data.items():
        setattr(category, key, value)
    if data.get("is_active") is False and category.parent_id is None:
        for child in db.scalars(
            select(Category).where(Category.user_id == user.id, Category.parent_id == category.id)
        ):
            child.is_active = False
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
    if payload.idempotency_key:
        try:
            with db.begin_nested():
                db.add(transaction)
                db.flush()
        except IntegrityError:
            previous = db.scalar(
                select(Transaction).where(
                    Transaction.user_id == user.id,
                    Transaction.idempotency_key == payload.idempotency_key,
                )
            )
            if previous:
                return previous
            raise
    else:
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
    legs = [
        Transaction(
            user_id=user.id,
            account_id=source.id,
            transfer=transfer,
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
            transfer=transfer,
            type="transfer",
            transfer_leg="in",
            amount=money(payload.amount),
            description=payload.description,
            transaction_date=transfer.transaction_date,
            source=transfer.source,
        ),
    ]
    if payload.idempotency_key:
        try:
            with db.begin_nested():
                db.add(transfer)
                db.flush()
                db.add_all(legs)
                db.flush()
        except IntegrityError:
            previous = db.scalar(
                select(Transfer).where(
                    Transfer.user_id == user.id,
                    Transfer.idempotency_key == payload.idempotency_key,
                )
            )
            if previous:
                return previous
            raise
    else:
        db.add(transfer)
        db.flush()
        db.add_all(legs)
        db.flush()
    return transfer


def update_transfer(
    db: Session, user: User, transfer_id: UUID, payload: TransferUpdate
) -> Transfer:
    transfer = db.scalar(
        select(Transfer).where(
            Transfer.id == transfer_id,
            Transfer.user_id == user.id,
            Transfer.deleted_at.is_(None),
        )
    )
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transferência não encontrada"
        )

    legs = list(
        db.scalars(
            select(Transaction).where(
                Transaction.transfer_id == transfer.id,
                Transaction.user_id == user.id,
                Transaction.deleted_at.is_(None),
            )
        )
    )
    legs_by_side = {leg.transfer_leg: leg for leg in legs}
    if len(legs) != 2 or set(legs_by_side) != {"in", "out"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="As duas movimentações da transferência não estão íntegras",
        )

    data = payload.model_dump(exclude_unset=True)
    source_account_id = data.get("source_account_id") or transfer.source_account_id
    destination_account_id = data.get("destination_account_id") or transfer.destination_account_id
    source = ensure_account(
        db,
        user.id,
        source_account_id,
        active=source_account_id != transfer.source_account_id,
    )
    destination = ensure_account(
        db,
        user.id,
        destination_account_id,
        active=destination_account_id != transfer.destination_account_id,
    )
    if source.id == destination.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="As contas devem ser diferentes",
        )

    amount = money(data.get("amount") or transfer.amount)
    description = data.get("description") or transfer.description
    transaction_date = data.get("transaction_date") or transfer.transaction_date

    transfer.source_account_id = source.id
    transfer.destination_account_id = destination.id
    transfer.amount = amount
    transfer.description = description
    transfer.transaction_date = transaction_date
    legs_by_side["out"].account_id = source.id
    legs_by_side["in"].account_id = destination.id
    for leg in legs:
        leg.amount = amount
        leg.description = description
        leg.transaction_date = transaction_date
    db.flush()
    return transfer


def transaction_query(user_id: UUID) -> Select:
    return (
        select(Transaction)
        .options(
            selectinload(Transaction.account),
            selectinload(Transaction.category),
            selectinload(Transaction.transfer).selectinload(Transfer.source_account),
            selectinload(Transaction.transfer).selectinload(Transfer.destination_account),
        )
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
    sort: TransactionSort = "date_desc",
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
    else:
        query = query.where(or_(Transaction.type != "transfer", Transaction.transfer_leg == "out"))
    if category_id:
        query = query.where(Transaction.category_id == category_id)
    if source:
        query = query.where(Transaction.source == source)
    if search:
        query = query.where(Transaction.description.ilike(f"%{search}%"))
    ordering = {
        "date_desc": (Transaction.transaction_date.desc(), Transaction.created_at.desc()),
        "date_asc": (Transaction.transaction_date.asc(), Transaction.created_at.asc()),
        "amount_desc": (Transaction.amount.desc(), Transaction.transaction_date.desc()),
        "amount_asc": (Transaction.amount.asc(), Transaction.transaction_date.desc()),
    }[sort]
    return list(db.scalars(query.order_by(*ordering).limit(limit)))


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
        transfer = db.scalar(
            select(Transfer).where(
                Transfer.id == transaction.transfer_id,
                Transfer.user_id == user.id,
            )
        )
        if transfer:
            transfer.deleted_at = now
        for leg in db.scalars(
            select(Transaction).where(
                Transaction.transfer_id == transaction.transfer_id,
                Transaction.user_id == user.id,
            )
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


def monthly_evolution(db: Session, user: User, selected_month: date, months: int) -> list[dict]:
    selected_month = month_start(selected_month)
    result = []
    for offset in range(-(months - 1), 1):
        start = shift_month(selected_month, offset)
        end = next_month(start) - timedelta(days=1)
        income, expense = totals_for_period(db, user.id, start, end)
        result.append(
            {
                "month": start,
                "income": income,
                "expense": expense,
                "savings": money(income - expense),
            }
        )
    return result


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
    children: dict[UUID, list[UUID]] = defaultdict(list)
    for category_id, parent_id in db.execute(
        select(Category.id, Category.parent_id).where(Category.user_id == user.id)
    ):
        if parent_id:
            children[parent_id].append(category_id)
    result = []
    for budget in budgets:
        limit = money(budget.limit_amount)
        category_ids = [budget.category_id, *children.get(budget.category_id, [])]
        used = money(
            sum((spent.get(category_id, money(0)) for category_id in category_ids), money(0))
        )
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
        select(Category.id, Category.parent_id, Category.name, func.sum(Transaction.amount))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user.id,
            Transaction.type == "expense",
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            Transaction.deleted_at.is_(None),
        )
        .group_by(Category.id, Category.parent_id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
    )
    category_lookup = {
        category.id: category
        for category in db.scalars(select(Category).where(Category.user_id == user.id))
    }
    category_totals: dict[UUID | None, Decimal] = defaultdict(lambda: money(0))
    category_names: dict[UUID | None, str] = {}
    for category_id, parent_id, name, total in category_rows:
        root = category_lookup.get(parent_id) if parent_id else None
        aggregate_id = root.id if root else category_id
        category_names[aggregate_id] = root.name if root else name
        category_totals[aggregate_id] += money(total)
    uncategorized_total = money(
        db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user.id,
                Transaction.type == "expense",
                Transaction.category_id.is_(None),
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
                Transaction.deleted_at.is_(None),
            )
        )
    )
    if uncategorized_total:
        category_names[None] = "Sem categoria"
        category_totals[None] = uncategorized_total
    by_category = [
        {
            "category_id": category_id,
            "category_name": category_names[category_id],
            "amount": money(total),
        }
        for category_id, total in sorted(
            category_totals.items(), key=lambda item: item[1], reverse=True
        )
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
