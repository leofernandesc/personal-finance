"""Harden financial integrity and agent auditing.

Revision ID: 0002_harden_financial_integrity
Revises: 0001_initial_financial_domain
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_harden_financial_integrity"
down_revision: Union[str, None] = "0001_initial_financial_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def uuid_type() -> sa.Uuid:
    return sa.Uuid(as_uuid=True)


def upgrade() -> None:
    # Earlier local linking marked numbers as verified without a channel
    # challenge. Preserve the link, but do not overstate ownership assurance.
    op.execute("UPDATE whatsapp_identities SET verified_at = NULL")

    op.drop_constraint("transactions_idempotency_key_key", "transactions", type_="unique")
    op.drop_constraint("transfers_idempotency_key_key", "transfers", type_="unique")
    op.create_unique_constraint(
        "uq_transactions_user_idempotency",
        "transactions",
        ["user_id", "idempotency_key"],
    )
    op.create_unique_constraint(
        "uq_transfers_user_idempotency",
        "transfers",
        ["user_id", "idempotency_key"],
    )

    op.add_column("transfers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_check_constraint(
        "ck_accounts_type",
        "accounts",
        "account_type IN ('checking', 'savings', 'cash', 'investment', 'other')",
    )
    op.create_check_constraint(
        "ck_categories_kind", "categories", "kind IN ('expense', 'income', 'both')"
    )
    op.create_check_constraint("ck_transactions_positive_amount", "transactions", "amount > 0")
    op.create_check_constraint(
        "ck_transactions_source",
        "transactions",
        "source IN ('web', 'whatsapp', 'import', 'automatic')",
    )
    op.create_check_constraint(
        "ck_transactions_shape",
        "transactions",
        "(type = 'transfer' AND transfer_id IS NOT NULL "
        "AND transfer_leg IN ('in', 'out') AND category_id IS NULL) OR "
        "(type IN ('income', 'expense') AND transfer_id IS NULL AND transfer_leg IS NULL)",
    )
    op.create_check_constraint("ck_transfers_positive_amount", "transfers", "amount > 0")
    op.create_check_constraint(
        "ck_transfers_distinct_accounts",
        "transfers",
        "source_account_id <> destination_account_id",
    )
    op.create_check_constraint(
        "ck_transfers_source",
        "transfers",
        "source IN ('web', 'whatsapp', 'import', 'automatic')",
    )
    op.create_check_constraint("ck_budgets_positive_limit", "budgets", "limit_amount > 0")
    op.create_check_constraint(
        "ck_budgets_month_start", "budgets", "EXTRACT(DAY FROM month) = 1"
    )
    op.create_check_constraint("ck_goals_positive_target", "goals", "target_amount > 0")
    op.create_check_constraint("ck_goals_nonnegative_current", "goals", "current_amount >= 0")
    op.create_check_constraint(
        "ck_goals_status", "goals", "status IN ('active', 'completed', 'archived')"
    )

    op.drop_constraint(
        "uq_agent_messages_provider_external", "agent_messages", type_="unique"
    )
    op.create_unique_constraint(
        "uq_agent_messages_provider_sender_external",
        "agent_messages",
        ["provider", "sender_id", "external_message_id"],
    )
    op.create_check_constraint(
        "ck_agent_messages_status",
        "agent_messages",
        "status IN ('received', 'processing', 'success', 'error')",
    )

    op.create_table(
        "agent_tool_calls",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("agent_message_id", uuid_type(), nullable=False),
        sa.Column("user_id", uuid_type(), nullable=True),
        sa.Column("intent", sa.String(length=80), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("transaction_id", uuid_type(), nullable=True),
        sa.Column("transfer_id", uuid_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('processing', 'success', 'error')",
            name="ck_agent_tool_calls_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_message_id"], ["agent_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["transfer_id"], ["transfers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_tool_calls_agent_message_id",
        "agent_tool_calls",
        ["agent_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_tool_calls_user_id", "agent_tool_calls", ["user_id"], unique=False
    )
    op.create_index(
        "ix_agent_tool_calls_user_created",
        "agent_tool_calls",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_tool_calls_user_created", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_user_id", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_agent_message_id", table_name="agent_tool_calls")
    op.drop_table("agent_tool_calls")

    op.drop_constraint("ck_agent_messages_status", "agent_messages", type_="check")
    op.drop_constraint(
        "uq_agent_messages_provider_sender_external", "agent_messages", type_="unique"
    )
    op.create_unique_constraint(
        "uq_agent_messages_provider_external",
        "agent_messages",
        ["provider", "external_message_id"],
    )

    op.drop_constraint("ck_goals_status", "goals", type_="check")
    op.drop_constraint("ck_goals_nonnegative_current", "goals", type_="check")
    op.drop_constraint("ck_goals_positive_target", "goals", type_="check")
    op.drop_constraint("ck_budgets_month_start", "budgets", type_="check")
    op.drop_constraint("ck_budgets_positive_limit", "budgets", type_="check")
    op.drop_constraint("ck_transfers_source", "transfers", type_="check")
    op.drop_constraint("ck_transfers_distinct_accounts", "transfers", type_="check")
    op.drop_constraint("ck_transfers_positive_amount", "transfers", type_="check")
    op.drop_constraint("ck_transactions_shape", "transactions", type_="check")
    op.drop_constraint("ck_transactions_source", "transactions", type_="check")
    op.drop_constraint("ck_transactions_positive_amount", "transactions", type_="check")
    op.drop_constraint("ck_categories_kind", "categories", type_="check")
    op.drop_constraint("ck_accounts_type", "accounts", type_="check")

    op.drop_column("transfers", "deleted_at")
    op.drop_constraint("uq_transfers_user_idempotency", "transfers", type_="unique")
    op.drop_constraint("uq_transactions_user_idempotency", "transactions", type_="unique")
    op.create_unique_constraint(
        "transfers_idempotency_key_key", "transfers", ["idempotency_key"]
    )
    op.create_unique_constraint(
        "transactions_idempotency_key_key", "transactions", ["idempotency_key"]
    )
