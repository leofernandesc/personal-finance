from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email"),
        Index("ix_users_email", "email"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Manaus")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    accounts: Mapped[list["Account"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    goals: Mapped[list["Goal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    financial_diagnostic: Mapped["FinancialDiagnostic | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class FinancialDiagnostic(Base):
    __tablename__ = "financial_diagnostics"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_financial_diagnostics_user"),
        CheckConstraint(
            "status IN ('draft', 'completed')", name="ck_financial_diagnostics_status"
        ),
        CheckConstraint(
            "current_section BETWEEN 1 AND 13", name="ck_financial_diagnostics_section"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft")
    current_section: Mapped[int] = mapped_column(default=1)
    version: Mapped[int] = mapped_column(default=1)
    answers: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=dict)
    consent_data_processing: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_service_disclaimer: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_version: Mapped[str] = mapped_column(String(40), default="diagnostic-v1")
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="financial_diagnostic")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash"),
        Index("ix_auth_sessions_token_hash", "token_hash"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship(back_populates="sessions")


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_accounts_user_name"),
        CheckConstraint(
            "account_type IN ('checking', 'savings', 'cash', 'investment', 'other')",
            name="ck_accounts_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    account_type: Mapped[str] = mapped_column(String(20), default="checking")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_user_active", "user_id", "is_active"),
        CheckConstraint("kind IN ('expense', 'income', 'both')", name="ck_categories_kind"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20), default="expense")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship(back_populates="categories")
    parent: Mapped["Category | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category")


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_transfers_user_idempotency"),
        CheckConstraint("amount > 0", name="ck_transfers_positive_amount"),
        CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_transfers_distinct_accounts",
        ),
        CheckConstraint(
            "source IN ('web', 'whatsapp', 'import', 'automatic')",
            name="ck_transfers_source",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    destination_account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[str] = mapped_column(String(255), default="Transferência")
    transaction_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20), default="web")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan"
    )
    source_account: Mapped[Account] = relationship(foreign_keys=[source_account_id])
    destination_account: Mapped[Account] = relationship(foreign_keys=[destination_account_id])


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_user_type", "user_id", "type"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_transactions_user_idempotency"),
        CheckConstraint("amount > 0", name="ck_transactions_positive_amount"),
        CheckConstraint(
            "source IN ('web', 'whatsapp', 'import', 'automatic')",
            name="ck_transactions_source",
        ),
        CheckConstraint(
            "(type = 'transfer' AND transfer_id IS NOT NULL "
            "AND transfer_leg IN ('in', 'out') AND category_id IS NULL) OR "
            "(type IN ('income', 'expense') AND transfer_id IS NULL AND transfer_leg IS NULL)",
            name="ck_transactions_shape",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    transfer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transfers.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(20))
    transfer_leg: Mapped[str | None] = mapped_column(String(10), nullable=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    transaction_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20), default="web")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="transactions")
    account: Mapped[Account] = relationship(back_populates="transactions")
    category: Mapped[Category | None] = relationship(back_populates="transactions")
    transfer: Mapped[Transfer | None] = relationship(back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", name="uq_budgets_user_category_month"),
        CheckConstraint("limit_amount > 0", name="ck_budgets_positive_limit"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    month: Mapped[date] = mapped_column(Date)
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="budgets")
    category: Mapped[Category] = relationship()


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_goals_positive_target"),
        CheckConstraint("current_amount >= 0", name="ck_goals_nonnegative_current"),
        CheckConstraint("status IN ('active', 'completed', 'archived')", name="ck_goals_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="goals")


class WhatsAppIdentity(Base):
    __tablename__ = "whatsapp_identities"
    __table_args__ = (
        UniqueConstraint("phone_e164"),
        Index("ix_whatsapp_identities_phone_e164", "phone_e164"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    phone_e164: Mapped[str] = mapped_column(String(32))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AgentMessage(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "sender_id",
            "external_message_id",
            name="uq_agent_messages_provider_sender_external",
        ),
        CheckConstraint(
            "status IN ('received', 'processing', 'success', 'error')",
            name="ck_agent_messages_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(30))
    external_message_id: Mapped[str] = mapped_column(String(255))
    sender_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    text_hash: Mapped[str] = mapped_column(String(64))
    intent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="received")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    transfer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tool_calls: Mapped[list["AgentToolCall"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class AgentToolCall(Base):
    __tablename__ = "agent_tool_calls"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'success', 'error')", name="ck_agent_tool_calls_status"
        ),
        Index("ix_agent_tool_calls_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    agent_message_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_messages.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    intent: Mapped[str] = mapped_column(String(80))
    tool_name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="processing")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    transfer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    message: Mapped[AgentMessage] = relationship(back_populates="tool_calls")


class PendingAgentAction(Base):
    __tablename__ = "pending_agent_actions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(30))
    sender_id: Mapped[str] = mapped_column(String(64))
    action_type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    confirmation_token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
