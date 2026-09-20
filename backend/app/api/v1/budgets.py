from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Budget, User
from app.schemas.finance import BudgetCreate, BudgetResponse, BudgetUpdate
from app.services.finance import budget_status, ensure_category, month_start

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _find_budget(db: Session, user: User, budget_id: UUID) -> Budget:
    budget = db.scalar(select(Budget).where(Budget.id == budget_id, Budget.user_id == user.id))
    if not budget:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    return budget


def _status_item(db: Session, user: User, budget: Budget) -> dict:
    return next(item for item in budget_status(db, user, budget.month) if item["id"] == budget.id)


@router.get("", response_model=list[BudgetResponse])
def list_budgets(
    month: date | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return budget_status(db, user, month or date.today())


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def add_budget(
    payload: BudgetCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    ensure_category(db, user.id, payload.category_id, kind="expense")
    normalized_month = month_start(payload.month)
    if db.scalar(
        select(Budget).where(
            Budget.user_id == user.id,
            Budget.category_id == payload.category_id,
            Budget.month == normalized_month,
        )
    ):
        raise HTTPException(status_code=409, detail="Já existe orçamento para essa categoria e mês")
    budget = Budget(
        user_id=user.id,
        category_id=payload.category_id,
        month=normalized_month,
        limit_amount=payload.limit_amount,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return _status_item(db, user, budget)


@router.patch("/{budget_id}", response_model=BudgetResponse)
def edit_budget(
    budget_id: UUID,
    payload: BudgetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = _find_budget(db, user, budget_id)
    budget.limit_amount = payload.limit_amount
    db.commit()
    db.refresh(budget)
    return _status_item(db, user, budget)
