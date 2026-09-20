from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app


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

    history = first.get("/api/v1/transactions").json()
    transfer_rows = [item for item in history if item["type"] == "transfer"]
    assert len(transfer_rows) == 1
    assert transfer_rows[0]["transfer_source_account_name"] == "Nubank"
    assert transfer_rows[0]["transfer_destination_account_name"] == "Inter"

    register(second, "bruno@example.com")
    assert second.get("/api/v1/accounts").json() == []
    assert second.get("/api/v1/transactions").json() == []


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
