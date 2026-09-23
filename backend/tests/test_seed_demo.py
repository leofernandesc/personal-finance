from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import seed_demo
from app.db.base import Base
from app.models import Account, Budget, Goal, Transaction, User


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_demo_seed_refuses_shared_environments_before_opening_database(monkeypatch, environment):
    monkeypatch.setattr(
        seed_demo,
        "get_settings",
        lambda: SimpleNamespace(environment=environment),
    )

    def database_must_not_be_opened():
        pytest.fail("o seed tentou abrir o banco antes de validar o ambiente")

    monkeypatch.setattr(seed_demo, "SessionLocal", database_must_not_be_opened)

    with pytest.raises(RuntimeError, match="development ou test"):
        seed_demo.run()


def test_demo_seed_environment_guard_allows_local_environments():
    seed_demo._ensure_demo_seed_is_allowed("development")
    seed_demo._ensure_demo_seed_is_allowed("test")


def test_demo_seed_is_idempotent_in_development(monkeypatch, capsys):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(
        seed_demo,
        "get_settings",
        lambda: SimpleNamespace(environment="development", default_timezone="America/Manaus"),
    )
    monkeypatch.setattr(seed_demo, "SessionLocal", test_sessions)

    seed_demo.run()
    seed_demo.run()

    with test_sessions() as db:
        user = db.scalar(select(User).where(User.email == seed_demo.DEMO_EMAIL))
        assert user is not None
        for model, expected_count in (
            (Account, 3),
            (Transaction, 4),
            (Budget, 2),
            (Goal, 1),
        ):
            actual_count = db.scalar(
                select(func.count()).select_from(model).where(model.user_id == user.id)
            )
            assert actual_count == expected_count

    assert "Demo user already exists" in capsys.readouterr().out
    Base.metadata.drop_all(engine)
    engine.dispose()
