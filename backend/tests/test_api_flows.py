from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.config import get_settings
from app.db.base import Base
from app.main import REQUIRED_SCHEMA_TABLES, app


@pytest.fixture
def clients() -> Iterator[tuple[TestClient, TestClient]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db() -> Iterator[Session]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as first, TestClient(app) as second:
        yield first, second
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "senha-segura",
            "full_name": "Pessoa de Teste",
            "timezone": "America/Manaus",
        },
    )
    assert response.status_code == 201, response.text


def test_readiness_requires_the_financial_schema(clients):
    first, _second = clients

    response = first.get("/ready")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "ready",
        "service": "personal-finance-api",
    }
    assert "financial_diagnostics" in REQUIRED_SCHEMA_TABLES


def create_account(client: TestClient, name: str) -> dict:
    response = client.post(
        "/api/v1/accounts",
        json={"name": name, "account_type": "checking", "opening_balance": "1000.00"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_web_flow_forces_source_creates_transfer_and_isolates_users(clients):
    first, second = clients
    register(first, "ana@example.com")
    nubank = create_account(first, "Nubank")
    inter = create_account(first, "Inter")
    categories = first.get("/api/v1/categories").json()
    food = next(category for category in categories if category["name"] == "Alimentação")

    transaction = first.post(
        "/api/v1/transactions",
        json={
            "account_id": nubank["id"],
            "category_id": food["id"],
            "type": "expense",
            "amount": "42.50",
            "description": "Almoço",
            "source": "whatsapp",
        },
    )
    assert transaction.status_code == 201, transaction.text
    assert transaction.json()["source"] == "web"

    transfer = first.post(
        "/api/v1/transfers",
        json={
            "source_account_id": nubank["id"],
            "destination_account_id": inter["id"],
            "amount": "100.00",
            "description": "Reserva",
            "source": "whatsapp",
        },
    )
    assert transfer.status_code == 201, transfer.text
    assert transfer.json()["source"] == "web"
    transfer_edit = first.patch(
        f"/api/v1/transfers/{transfer.json()['id']}",
        json={
            "amount": "125.00",
            "description": "Reserva ajustada",
            "transaction_date": "2026-09-21",
        },
    )
    assert transfer_edit.status_code == 200, transfer_edit.text
    assert transfer_edit.json()["amount"] == "125.00"
    assert transfer_edit.json()["description"] == "Reserva ajustada"

    history = first.get("/api/v1/transactions").json()
    transfer_rows = [item for item in history if item["type"] == "transfer"]
    assert len(transfer_rows) == 1
    assert transfer_rows[0]["transfer_source_account_name"] == "Nubank"
    assert transfer_rows[0]["transfer_destination_account_name"] == "Inter"

    register(second, "bruno@example.com")
    assert second.get("/api/v1/accounts").json() == []
    assert second.get("/api/v1/transactions").json() == []
    foreign_transfer_edit = second.patch(
        f"/api/v1/transfers/{transfer.json()['id']}",
        json={"amount": "999.00"},
    )
    assert foreign_transfer_edit.status_code == 404


def test_invalid_date_range_is_rejected(clients):
    first, _second = clients
    register(first, "range@example.com")

    response = first.get("/api/v1/transactions?start=2026-09-20&end=2026-09-01")

    assert response.status_code == 422
    assert response.json()["detail"] == "A data inicial deve ser anterior à final"


def test_request_models_reject_identity_fields_from_clients(clients):
    first, _second = clients
    register(first, "identity-fields@example.com")

    response = first.post(
        "/api/v1/accounts",
        json={
            "name": "Conta indevida",
            "account_type": "checking",
            "opening_balance": "0.00",
            "user_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 422
    assert first.get("/api/v1/accounts").json() == []


def test_goal_progress_completes_and_archive_route_works(clients):
    first, _second = clients
    register(first, "goals@example.com")

    created = first.post(
        "/api/v1/goals",
        json={
            "name": "Reserva de emergência",
            "target_amount": "1000.00",
            "current_amount": "100.00",
        },
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]
    assert created.json()["status"] == "active"

    completed = first.patch(
        f"/api/v1/goals/{goal_id}",
        json={"current_amount": "1000.00"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"

    archived = first.delete(f"/api/v1/goals/{goal_id}")
    assert archived.status_code == 200, archived.text
    assert archived.json() == {"message": "Meta arquivada"}

    goals = first.get("/api/v1/goals")
    assert goals.status_code == 200
    assert goals.json()[0]["status"] == "archived"


def test_linking_a_new_whatsapp_number_replaces_the_previous_active_link(clients):
    first, _second = clients
    register(first, "whatsapp-link@example.com")

    first_link = first.post(
        "/api/v1/integrations/whatsapp/link",
        json={"phone_e164": "+55 92 99999-0001"},
    )
    second_link = first.post(
        "/api/v1/integrations/whatsapp/link",
        json={"phone_e164": "+55 92 99999-0002"},
    )
    identity = first.get("/api/v1/integrations/whatsapp/identity")

    assert first_link.status_code == 201
    assert second_link.status_code == 201
    assert identity.status_code == 200
    assert identity.json() == {
        "linked": True,
        "phone_e164": "+5592999990002",
        "verified": False,
    }


def test_whatsapp_agent_requires_possession_verification(clients):
    first, _second = clients
    register(first, "whatsapp-verification@example.com")
    phone = "+5592999990003"
    linked = first.post(
        "/api/v1/integrations/whatsapp/link",
        json={"phone_e164": phone},
    )
    assert linked.status_code == 201

    headers = {
        "X-Agent-Token": get_settings().agent_shared_secret,
        "X-Agent-Provider": "whatsapp",
        "X-Agent-Sender-Id": phone,
        "X-Agent-Message-Id": "verification-before-1",
    }
    blocked = first.get("/api/v1/integrations/agent/balance", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Número WhatsApp ainda não verificado"

    challenge = first.post("/api/v1/integrations/whatsapp/verification/start")
    assert challenge.status_code == 200, challenge.text
    code = challenge.json()["code"]

    verified = first.post(
        "/api/v1/integrations/agent/verify-whatsapp",
        headers={**headers, "X-Agent-Message-Id": "verification-code-1"},
        json={"code": code},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json() == {"verified": True, "phone_e164": phone}

    allowed = first.get(
        "/api/v1/integrations/agent/balance",
        headers={**headers, "X-Agent-Message-Id": "balance-after-verification-1"},
    )
    assert allowed.status_code == 200, allowed.text

    unlinked = first.delete("/api/v1/integrations/whatsapp/link")
    assert unlinked.status_code == 200
    relinked = first.post(
        "/api/v1/integrations/whatsapp/link",
        json={"phone_e164": phone},
    )
    assert relinked.status_code == 201
    assert relinked.json()["verified"] is False


def diagnostic_answers(**overrides) -> dict:
    answers = {
        "full_name": "Pessoa de Diagnóstico",
        "birth_date": "1990-05-10",
        "contact_email": "diagnostico@example.com",
        "phone": "+55 92 99999-0000",
        "city_state": "Manaus - AM",
        "occupation": "Profissional autônomo",
        "financial_dependents": 0,
        "main_difficulties": ["dont_know"],
        "financial_priority": "organize",
        "expected_result": "Saber para onde meu dinheiro está indo.",
        "financial_organization_score": 2,
        "organization_barriers": ["lack_of_planning"],
        "monthly_net_income": "5000.00",
        "family_monthly_net_income": "5000.00",
        "income_sources": ["salary"],
        "income_sufficiency": "break_even",
        "tracks_expenses": "some",
        "monthly_expenses": "4200.00",
        "largest_expense_categories": ["housing", "food"],
        "credit_card_count": 1,
        "has_debts": "no",
        "has_reserve": "no",
        "financial_goals": ["emergency_fund"],
        "most_important_goal": "Criar uma reserva de emergência",
        "willing_to_track_expenses": "with_guidance",
    }
    answers.update(overrides)
    return answers


def test_diagnostic_draft_submission_edit_and_user_isolation(clients):
    first, second = clients
    register(first, "diagnostic@example.com")

    initial = first.get("/api/v1/diagnostic")
    assert initial.status_code == 200
    assert initial.json()["status"] == "not_started"

    draft = first.put(
        "/api/v1/diagnostic/draft",
        json={"current_section": 2, "answers": {"full_name": "Pessoa de Diagnóstico"}},
    )
    assert draft.status_code == 200, draft.text
    assert draft.json()["status"] == "draft"
    assert draft.json()["answers"]["full_name"] == "Pessoa de Diagnóstico"

    without_consent = first.post(
        "/api/v1/diagnostic/submit",
        json={
            "answers": diagnostic_answers(),
            "consent_data_processing": True,
            "consent_service_disclaimer": False,
        },
    )
    assert without_consent.status_code == 422
    assert "consentimentos" in without_consent.json()["detail"]

    submitted = first.post(
        "/api/v1/diagnostic/submit",
        json={
            "answers": diagnostic_answers(),
            "consent_data_processing": True,
            "consent_service_disclaimer": True,
        },
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["status"] == "completed"
    assert submitted.json()["completion_percent"] == 100

    edited = first.post(
        "/api/v1/diagnostic/submit",
        json={
            "answers": diagnostic_answers(expected_result="Ter uma rotina financeira mais leve."),
            "consent_data_processing": True,
            "consent_service_disclaimer": True,
        },
    )
    assert edited.status_code == 201, edited.text
    assert edited.json()["answers"]["expected_result"] == "Ter uma rotina financeira mais leve."

    register(second, "other-diagnostic@example.com")
    other = second.get("/api/v1/diagnostic")
    assert other.status_code == 200
    assert other.json()["status"] == "not_started"
    assert other.json()["answers"] == {}


def test_diagnostic_requires_debt_details_when_user_has_debts(clients):
    first, _second = clients
    register(first, "debts-diagnostic@example.com")
    response = first.post(
        "/api/v1/diagnostic/submit",
        json={
            "answers": diagnostic_answers(has_debts="yes"),
            "consent_data_processing": True,
            "consent_service_disclaimer": True,
        },
    )

    assert response.status_code == 422
    assert "debt_types" in response.json()["detail"]


def test_diagnostic_summary_uses_saved_answers_and_profile_is_editable(clients):
    first, second = clients
    register(first, "summary@example.com")

    not_ready = first.get("/api/v1/diagnostic/summary")
    assert not_ready.status_code == 200
    assert not_ready.json()["status"] == "not_ready"

    submitted = first.post(
        "/api/v1/diagnostic/submit",
        json={
            "answers": diagnostic_answers(
                has_reserve="no",
                tracks_expenses="none",
                monthly_net_income="5000.00",
                family_monthly_net_income="5000.00",
                monthly_expenses="4200.00",
            ),
            "consent_data_processing": True,
            "consent_service_disclaimer": True,
        },
    )
    assert submitted.status_code == 201, submitted.text

    summary = first.get("/api/v1/diagnostic/summary")
    assert summary.status_code == 200, summary.text
    assert summary.json()["status"] == "completed"
    assert summary.json()["metrics"]["monthly_margin"] == "800.00"
    assert summary.json()["basis"] == "self_reported_diagnostic"
    assert summary.json()["next_steps"]

    updated = first.patch(
        "/api/v1/auth/me",
        json={"full_name": "Pessoa Atualizada", "timezone": "America/Sao_Paulo"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Pessoa Atualizada"
    assert updated.json()["timezone"] == "America/Sao_Paulo"

    register(second, "other-summary@example.com")
    assert second.get("/api/v1/diagnostic/summary").json()["status"] == "not_ready"


def test_diagnostic_clears_conditional_answers_and_validates_other_priority(clients):
    first, _second = clients
    register(first, "conditional-diagnostic@example.com")

    invalid_other = first.post(
        "/api/v1/diagnostic/submit",
        json={
            "answers": diagnostic_answers(financial_priority="other"),
            "consent_data_processing": True,
            "consent_service_disclaimer": True,
        },
    )
    assert invalid_other.status_code == 422
    assert "financial_priority_other" in invalid_other.json()["detail"]

    submitted = first.post(
        "/api/v1/diagnostic/submit",
        json={
            "answers": diagnostic_answers(
                total_debt_amount="900.00",
                debt_types=["personal_loan"],
                extra_income="no",
                extra_income_details="Renda antiga",
                has_debts="no",
            ),
            "consent_data_processing": True,
            "consent_service_disclaimer": True,
        },
    )
    assert submitted.status_code == 201, submitted.text
    assert "total_debt_amount" not in submitted.json()["answers"]
    assert "extra_income_details" not in submitted.json()["answers"]
