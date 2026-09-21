from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FinancialDiagnostic, User
from app.schemas.diagnostic import (
    DiagnosticAnswers,
    DiagnosticDraftRequest,
    DiagnosticResponse,
    DiagnosticSubmitRequest,
)

DIAGNOSTIC_VERSION = 1
DIAGNOSTIC_CONSENT_VERSION = "diagnostic-v1"
DIAGNOSTIC_SECTIONS = 13


def _now() -> datetime:
    return datetime.now(UTC)


def _answer_payload(answers: DiagnosticAnswers) -> dict[str, Any]:
    return answers.model_dump(mode="json", exclude_unset=True)


def _merge_answers(existing: dict[str, Any], incoming: DiagnosticAnswers) -> dict[str, Any]:
    merged = dict(existing)
    merged.update(_answer_payload(incoming))
    return merged


def _clear_debt_answers_if_needed(answers: dict[str, Any]) -> None:
    if answers.get("has_debts") != "no":
        return
    for field in (
        "debt_types",
        "debt_types_other",
        "total_debt_amount",
        "monthly_debt_installments",
        "has_overdue_debt",
        "has_negative_record",
        "main_debts_details",
        "tried_debt_negotiation",
    ):
        answers.pop(field, None)


def _completion_percent(diagnostic: FinancialDiagnostic | None) -> int:
    if not diagnostic:
        return 0
    if diagnostic.status == "completed":
        return 100
    return min(99, round(max(diagnostic.current_section - 1, 0) * 100 / DIAGNOSTIC_SECTIONS))


def _response(diagnostic: FinancialDiagnostic | None) -> DiagnosticResponse:
    if not diagnostic:
        return DiagnosticResponse(
            status="not_started",
            current_section=1,
            completion_percent=0,
            version=DIAGNOSTIC_VERSION,
            answers={},
            consent_data_processing=False,
            consent_service_disclaimer=False,
            consent_version=DIAGNOSTIC_CONSENT_VERSION,
            consented_at=None,
            completed_at=None,
            updated_at=None,
        )
    return DiagnosticResponse(
        status=diagnostic.status,
        current_section=diagnostic.current_section,
        completion_percent=_completion_percent(diagnostic),
        version=diagnostic.version,
        answers=diagnostic.answers or {},
        consent_data_processing=diagnostic.consent_data_processing,
        consent_service_disclaimer=diagnostic.consent_service_disclaimer,
        consent_version=diagnostic.consent_version,
        consented_at=diagnostic.consented_at,
        completed_at=diagnostic.completed_at,
        updated_at=diagnostic.updated_at,
    )


def get_diagnostic(db: Session, user: User) -> DiagnosticResponse:
    diagnostic = db.scalar(
        select(FinancialDiagnostic).where(FinancialDiagnostic.user_id == user.id)
    )
    return _response(diagnostic)


def save_draft(
    db: Session, user: User, payload: DiagnosticDraftRequest
) -> DiagnosticResponse:
    diagnostic = db.scalar(
        select(FinancialDiagnostic).where(FinancialDiagnostic.user_id == user.id)
    )
    incoming = _merge_answers(diagnostic.answers if diagnostic else {}, payload.answers)
    _clear_debt_answers_if_needed(incoming)
    if diagnostic is None:
        diagnostic = FinancialDiagnostic(
            user_id=user.id,
            status="draft",
            current_section=payload.current_section,
            version=DIAGNOSTIC_VERSION,
            answers=incoming,
            consent_version=DIAGNOSTIC_CONSENT_VERSION,
        )
        db.add(diagnostic)
    else:
        diagnostic.status = "draft"
        diagnostic.current_section = payload.current_section
        diagnostic.version = DIAGNOSTIC_VERSION
        diagnostic.answers = incoming
        diagnostic.completed_at = None
    db.commit()
    db.refresh(diagnostic)
    return _response(diagnostic)


def submit_diagnostic(
    db: Session, user: User, payload: DiagnosticSubmitRequest
) -> DiagnosticResponse:
    diagnostic = db.scalar(
        select(FinancialDiagnostic).where(FinancialDiagnostic.user_id == user.id)
    )
    incoming = _merge_answers(diagnostic.answers if diagnostic else {}, payload.answers)
    answers = DiagnosticAnswers.model_validate(incoming)
    answers.validate_submission()
    if not payload.consent_data_processing or not payload.consent_service_disclaimer:
        raise ValueError("Os dois consentimentos são obrigatórios para enviar o diagnóstico")
    _clear_debt_answers_if_needed(incoming)
    timestamp = _now()
    if diagnostic is None:
        diagnostic = FinancialDiagnostic(
            user_id=user.id,
            version=DIAGNOSTIC_VERSION,
            consent_version=DIAGNOSTIC_CONSENT_VERSION,
            created_at=timestamp,
        )
        db.add(diagnostic)
    diagnostic.status = "completed"
    diagnostic.current_section = DIAGNOSTIC_SECTIONS
    diagnostic.version = DIAGNOSTIC_VERSION
    diagnostic.answers = answers.model_dump(mode="json", exclude_none=True)
    diagnostic.consent_data_processing = True
    diagnostic.consent_service_disclaimer = True
    diagnostic.consent_version = DIAGNOSTIC_CONSENT_VERSION
    diagnostic.consented_at = timestamp
    diagnostic.completed_at = timestamp
    db.commit()
    db.refresh(diagnostic)
    return _response(diagnostic)
