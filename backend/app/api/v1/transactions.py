from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Transaction, Transfer, User
from app.schemas.common import MessageResponse
from app.schemas.finance import (
    SourceType,
    TransactionCreate,
    TransactionResponse,
    TransactionSort,
    TransactionType,
    TransactionUpdate,
    TransferCreate,
    TransferResponse,
    TransferUpdate,
)
from app.services.finance import (
    create_transaction,
    create_transfer,
    delete_transaction,
    list_transactions,
    update_transaction,
    update_transfer,
)

router = APIRouter(tags=["transactions"])


def serialize_transaction(transaction: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,
        account_id=transaction.account_id,
        category_id=transaction.category_id,
        transfer_id=transaction.transfer_id,
        type=transaction.type,
        transfer_leg=transaction.transfer_leg,
        description=transaction.description,
        amount=transaction.amount,
        transaction_date=transaction.transaction_date,
        source=transaction.source,
        created_at=transaction.created_at,
        account_name=transaction.account.name if transaction.account else None,
        category_name=transaction.category.name if transaction.category else None,
        transfer_source_account_name=(
            transaction.transfer.source_account.name if transaction.transfer else None
        ),
        transfer_destination_account_name=(
            transaction.transfer.destination_account.name if transaction.transfer else None
        ),
    )


@router.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(
    start: date | None = None,
    end: date | None = None,
    transaction_type: TransactionType | None = Query(default=None, alias="type"),
    account_id: UUID | None = None,
    category_id: UUID | None = None,
    source: SourceType | None = None,
    search: str | None = Query(default=None, max_length=80),
    sort: TransactionSort = "date_desc",
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="A data inicial deve ser anterior à final")
    return [
        serialize_transaction(t)
        for t in list_transactions(
            db,
            user,
            start=start,
            end=end,
            transaction_type=transaction_type,
            account_id=account_id,
            category_id=category_id,
            source=source,
            search=search,
            sort=sort,
            limit=limit,
        )
    ]


@router.post(
    "/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
def add_transaction(
    payload: TransactionCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    command = payload.model_copy(
        update={
            "source": "web",
            "idempotency_key": (
                f"web:{payload.idempotency_key}" if payload.idempotency_key else None
            ),
        }
    )
    replayed = False
    if command.idempotency_key:
        replayed = (
            db.scalar(
                select(Transaction).where(
                    Transaction.user_id == user.id,
                    Transaction.idempotency_key == command.idempotency_key,
                )
            )
            is not None
        )
    transaction = create_transaction(db, user, command, forced_source="web")
    response.headers["X-Idempotent-Replay"] = "true" if replayed else "false"
    db.commit()
    db.refresh(transaction)
    return serialize_transaction(transaction)


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
def edit_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = update_transaction(db, user, transaction_id, payload)
    db.commit()
    db.refresh(transaction)
    return serialize_transaction(transaction)


@router.delete("/transactions/{transaction_id}", response_model=MessageResponse)
def remove_transaction(
    transaction_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    delete_transaction(db, user, transaction_id)
    db.commit()
    return MessageResponse(message="Transação removida")


@router.get("/transfers", response_model=list[TransferResponse])
def get_transfers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(Transfer)
            .where(Transfer.user_id == user.id, Transfer.deleted_at.is_(None))
            .order_by(Transfer.transaction_date.desc())
        )
    )


@router.post("/transfers", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def add_transfer(
    payload: TransferCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    command = payload.model_copy(
        update={
            "source": "web",
            "idempotency_key": (
                f"web:{payload.idempotency_key}" if payload.idempotency_key else None
            ),
        }
    )
    transfer = create_transfer(db, user, command, forced_source="web")
    db.commit()
    db.refresh(transfer)
    return transfer


@router.patch("/transfers/{transfer_id}", response_model=TransferResponse)
def edit_transfer(
    transfer_id: UUID,
    payload: TransferUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = update_transfer(db, user, transfer_id, payload)
    db.commit()
    db.refresh(transfer)
    return transfer
