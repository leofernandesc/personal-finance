from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Account, User
from app.schemas.finance import AccountCreate, AccountResponse, AccountUpdate
from app.services.finance import balance_for_account, create_account, update_account

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _serialize(account: Account, db: Session) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        name=account.name,
        account_type=account.account_type,
        opening_balance=account.opening_balance,
        is_active=account.is_active,
        balance=balance_for_account(db, account),
    )


@router.get("", response_model=list[AccountResponse])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = list(
        db.scalars(select(Account).where(Account.user_id == user.id).order_by(Account.name))
    )
    return [_serialize(account, db) for account in accounts]


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def add_account(
    payload: AccountCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    account = create_account(db, user, payload)
    db.commit()
    db.refresh(account)
    return _serialize(account, db)


@router.patch("/{account_id}", response_model=AccountResponse)
def edit_account(
    account_id: UUID,
    payload: AccountUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = update_account(db, user, account_id, payload)
    db.commit()
    db.refresh(account)
    return _serialize(account, db)
