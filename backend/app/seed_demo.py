from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Budget, Category, Goal, User
from app.schemas.finance import AccountCreate, TransactionCreate
from app.services.finance import create_account, create_transaction, month_start, user_today
from app.services.seed import seed_categories

DEMO_EMAIL = "demo@personal-finance.local"


def run() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user:
            print(f"Demo user already exists: {user.email}")
            return

        user = User(
            email=DEMO_EMAIL,
            full_name="Ana Demo",
            password_hash=hash_password("demo1234"),
            timezone=settings.default_timezone,
        )
        db.add(user)
        db.flush()
        seed_categories(db, user)

        nubank = create_account(
            db,
            user,
            AccountCreate(
                name="Nubank", account_type="checking", opening_balance=Decimal("1200.00")
            ),
        )
        _inter = create_account(
            db,
            user,
            AccountCreate(name="Inter", account_type="savings", opening_balance=Decimal("850.00")),
        )
        cash = create_account(
            db,
            user,
            AccountCreate(name="Dinheiro", account_type="cash", opening_balance=Decimal("120.00")),
        )

        food = db.scalar(
            select(Category).where(
                Category.user_id == user.id,
                Category.name == "Alimentação",
                Category.parent_id.is_(None),
            )
        )
        transport = db.scalar(
            select(Category).where(
                Category.user_id == user.id,
                Category.name == "Transporte",
                Category.parent_id.is_(None),
            )
        )
        salary = db.scalar(
            select(Category).where(
                Category.user_id == user.id,
                Category.name == "Salário",
                Category.parent_id.is_(None),
            )
        )
        today = user_today(user)
        create_transaction(
            db,
            user,
            TransactionCreate(
                account_id=nubank.id,
                category_id=salary.id,
                type="income",
                amount=Decimal("4500.00"),
                description="Salário",
                transaction_date=today - timedelta(days=4),
            ),
        )
        create_transaction(
            db,
            user,
            TransactionCreate(
                account_id=nubank.id,
                category_id=food.id,
                type="expense",
                amount=Decimal("42.00"),
                description="Almoço",
                transaction_date=today - timedelta(days=2),
            ),
        )
        create_transaction(
            db,
            user,
            TransactionCreate(
                account_id=nubank.id,
                category_id=transport.id,
                type="expense",
                amount=Decimal("28.00"),
                description="Uber",
                transaction_date=today - timedelta(days=1),
                source="whatsapp",
            ),
        )
        create_transaction(
            db,
            user,
            TransactionCreate(
                account_id=cash.id,
                category_id=food.id,
                type="expense",
                amount=Decimal("35.50"),
                description="Mercado",
                transaction_date=today,
            ),
        )

        db.add(
            Budget(
                user_id=user.id,
                category_id=food.id,
                month=month_start(today),
                limit_amount=Decimal("800.00"),
            )
        )
        db.add(
            Budget(
                user_id=user.id,
                category_id=transport.id,
                month=month_start(today),
                limit_amount=Decimal("350.00"),
            )
        )
        db.add(
            Goal(
                user_id=user.id,
                name="Reserva de emergência",
                target_amount=Decimal("10000.00"),
                current_amount=Decimal("1850.00"),
                deadline=today.replace(year=today.year + 1),
                status="active",
            )
        )
        db.commit()
        print(f"Created demo user: {DEMO_EMAIL} / demo1234")


if __name__ == "__main__":
    run()
