from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.diagnostic import (
    DiagnosticDraftRequest,
    DiagnosticResponse,
    DiagnosticSubmitRequest,
)
from app.services.diagnostic import get_diagnostic, save_draft, submit_diagnostic

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


@router.get("", response_model=DiagnosticResponse)
def read_diagnostic(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DiagnosticResponse:
    return get_diagnostic(db, user)


@router.put("/draft", response_model=DiagnosticResponse)
def update_diagnostic_draft(
    payload: DiagnosticDraftRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiagnosticResponse:
    return save_draft(db, user, payload)


@router.post(
    "/submit",
    response_model=DiagnosticResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_diagnostic_form(
    payload: DiagnosticSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiagnosticResponse:
    try:
        return submit_diagnostic(db, user, payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
