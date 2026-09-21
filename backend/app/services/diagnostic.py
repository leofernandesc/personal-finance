from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FinancialDiagnostic, User
from app.schemas.common import dump_decimal
from app.schemas.diagnostic import (
    DiagnosticAnswers,
    DiagnosticDraftRequest,
    DiagnosticResponse,
    DiagnosticSubmitRequest,
    DiagnosticSummaryMetrics,
    DiagnosticSummaryNextStep,
    DiagnosticSummaryResponse,
    DiagnosticSummarySignal,
)

DIAGNOSTIC_VERSION = 2
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


def _remove_answers(answers: dict[str, Any], *fields: str) -> None:
    for field in fields:
        answers.pop(field, None)


def _normalize_answer_dependencies(answers: dict[str, Any]) -> None:
    """Remove answers that no longer apply after a conditional response changes."""

    if answers.get("has_debts") == "no":
        _remove_answers(
            answers,
            "debt_types",
            "debt_types_other",
            "total_debt_amount",
            "monthly_debt_installments",
            "has_overdue_debt",
            "has_negative_record",
            "main_debts_details",
            "tried_debt_negotiation",
        )

    if answers.get("extra_income") == "no":
        _remove_answers(answers, "extra_income_details")

    try:
        card_count = int(answers["credit_card_count"])
    except (KeyError, TypeError, ValueError):
        card_count = None
    if card_count == 0:
        _remove_answers(
            answers,
            "total_card_limit",
            "average_card_bill",
            "pays_card_in_full",
            "knows_installments",
        )

    if answers.get("has_reserve") == "no":
        _remove_answers(answers, "reserve_amount", "reserve_months")

    if answers.get("can_save_monthly") == "no":
        _remove_answers(answers, "average_monthly_saving")

    if answers.get("has_goal_savings") == "no":
        _remove_answers(answers, "goal_saved_amount")

    # Kept in the schema only to read old drafts; the questionnaire has no
    # free-text "other" option for available documents.
    answers.pop("available_documents_other", None)

    other_dependencies = (
        ("main_difficulties", "main_difficulties_other", "other"),
        ("organization_barriers", "organization_barriers_other", "other"),
        ("financial_priority", "financial_priority_other", "other"),
        ("income_sources", "income_sources_other", "other"),
        ("current_tool", "current_tool_other", "other"),
        ("largest_expense_categories", "largest_expense_categories_other", "other"),
        ("seasonal_expenses", "seasonal_expenses_other", "other"),
        ("debt_types", "debt_types_other", "other"),
        ("assets", "assets_other", "other_assets"),
        ("financial_goals", "financial_goals_other", "other"),
        ("possible_changes", "possible_changes_other", "other"),
        ("unexpected_expense_strategy", "unexpected_expense_other", "other"),
        ("document_delivery_preference", "document_delivery_other", "other"),
        ("how_found_service", "how_found_service_other", "other"),
    )
    for source_field, detail_field, trigger in other_dependencies:
        value = answers.get(source_field)
        selected = trigger in value if isinstance(value, list) else value == trigger
        if not selected:
            answers.pop(detail_field, None)


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


def save_draft(db: Session, user: User, payload: DiagnosticDraftRequest) -> DiagnosticResponse:
    diagnostic = db.scalar(
        select(FinancialDiagnostic).where(FinancialDiagnostic.user_id == user.id)
    )
    incoming = _merge_answers(diagnostic.answers if diagnostic else {}, payload.answers)
    _normalize_answer_dependencies(incoming)
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
    _normalize_answer_dependencies(incoming)
    answers = DiagnosticAnswers.model_validate(incoming)
    answers.validate_submission()
    if not payload.consent_data_processing or not payload.consent_service_disclaimer:
        raise ValueError("Os dois consentimentos são obrigatórios para enviar o diagnóstico")
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


def _summary_response_not_ready() -> DiagnosticSummaryResponse:
    return DiagnosticSummaryResponse(
        status="not_ready",
        snapshot_date=None,
        metrics=DiagnosticSummaryMetrics(
            monthly_income=None,
            family_monthly_income=None,
            monthly_expenses=None,
            monthly_margin=None,
            total_debt=None,
            monthly_debt_installments=None,
            reserve_amount=None,
            financial_score=None,
        ),
        signals=[],
        next_steps=[],
        basis="not_ready",
    )


def diagnostic_summary(db: Session, user: User) -> DiagnosticSummaryResponse:
    diagnostic = db.scalar(
        select(FinancialDiagnostic).where(FinancialDiagnostic.user_id == user.id)
    )
    if not diagnostic or diagnostic.status != "completed":
        return _summary_response_not_ready()

    answers = DiagnosticAnswers.model_validate(diagnostic.answers or {})
    monthly_income = answers.monthly_net_income
    family_monthly_income = answers.family_monthly_net_income
    monthly_expenses = answers.monthly_expenses
    monthly_margin = (
        monthly_income - monthly_expenses
        if monthly_income is not None and monthly_expenses is not None
        else None
    )

    signals: list[DiagnosticSummarySignal] = []
    next_steps: list[DiagnosticSummaryNextStep] = []

    def add_signal(level: str, title: str, description: str) -> None:
        if len(signals) < 5:
            signals.append(
                DiagnosticSummarySignal(level=level, title=title, description=description)
            )

    def add_step(title: str, description: str) -> None:
        if len(next_steps) < 3:
            next_steps.append(
                DiagnosticSummaryNextStep(
                    priority=len(next_steps) + 1,
                    title=title,
                    description=description,
                )
            )

    if monthly_margin is not None:
        if monthly_margin < Decimal("0.00"):
            add_signal(
                "priority",
                "O mês informado fecha no vermelho",
                "As despesas declaradas estão acima da renda mensal média.",
            )
            add_step(
                "Mapear o mês real",
                "Registre as despesas por algumas semanas para identificar onde ajustar primeiro.",
            )
        elif monthly_margin == Decimal("0.00"):
            add_signal(
                "attention",
                "A renda fica comprometida no mês",
                "As despesas declaradas consomem toda a renda mensal média.",
            )
            add_step(
                "Criar uma margem",
                "Observe os gastos variáveis e escolha um pequeno limite para começar a "
                "abrir espaço no mês.",
            )
        else:
            add_signal(
                "positive",
                "Existe uma margem mensal",
                "As respostas indicam que a renda média supera as despesas médias informadas.",
            )

    debt_risk = answers.has_debts == "yes" and (
        answers.has_overdue_debt == "yes" or answers.has_negative_record == "yes"
    )
    if debt_risk:
        add_signal(
            "priority",
            "Há dívidas que merecem atenção",
            "Foram informadas dívidas atrasadas ou com registro de negativação.",
        )
        add_step(
            "Organizar as dívidas",
            "Reúna saldo, parcela e situação de cada dívida antes de decidir os próximos passos.",
        )
    elif answers.has_debts == "yes":
        add_signal(
            "attention",
            "Existem dívidas no retrato atual",
            "O detalhamento das dívidas ajudará a definir uma ordem de organização.",
        )
        add_step(
            "Listar compromissos",
            "Mantenha saldo, valor da parcela e quantidade restante registrados em um só lugar.",
        )

    if answers.has_reserve in {"no", "unorganized"}:
        add_signal(
            "attention",
            "A reserva ainda precisa de estrutura",
            "As respostas indicam ausência de reserva ou dinheiro guardado sem organização.",
        )
        add_step(
            "Construir uma reserva",
            "Depois de enxergar o mês, defina um valor possível para guardar com regularidade.",
        )
    elif answers.has_reserve == "yes":
        add_signal(
            "positive",
            "Você já possui uma reserva",
            "Esse recurso pode ajudar a atravessar imprevistos com mais tranquilidade.",
        )

    if answers.tracks_expenses in {"none", "tried"}:
        add_signal(
            "attention",
            "Registrar gastos pode trazer clareza",
            "Você informou que ainda não mantém um registro consistente das despesas.",
        )
        add_step(
            "Começar pelos registros simples",
            "Use o Organiza Finanças para registrar cada movimento sem buscar perfeição no início.",
        )

    return DiagnosticSummaryResponse(
        status="completed",
        snapshot_date=diagnostic.completed_at,
        metrics=DiagnosticSummaryMetrics(
            monthly_income=dump_decimal(monthly_income),
            family_monthly_income=dump_decimal(family_monthly_income),
            monthly_expenses=dump_decimal(monthly_expenses),
            monthly_margin=dump_decimal(monthly_margin),
            total_debt=dump_decimal(answers.total_debt_amount),
            monthly_debt_installments=dump_decimal(answers.monthly_debt_installments),
            reserve_amount=dump_decimal(answers.reserve_amount),
            financial_score=answers.financial_organization_score,
        ),
        signals=signals,
        next_steps=next_steps,
        basis="self_reported_diagnostic",
    )
