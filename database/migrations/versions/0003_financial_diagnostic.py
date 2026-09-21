"""Add the editable financial diagnostic.

Revision ID: 0003_financial_diagnostic
Revises: 0002_harden_financial_integrity
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0003_financial_diagnostic"
down_revision: Union[str, None] = "0002_harden_financial_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def uuid_type() -> sa.Uuid:
    return sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "financial_diagnostics",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("user_id", uuid_type(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("current_section", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "answers",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("consent_data_processing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_service_disclaimer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "consent_version",
            sa.String(length=40),
            nullable=False,
            server_default="diagnostic-v1",
        ),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'completed')", name="ck_financial_diagnostics_status"
        ),
        sa.CheckConstraint(
            "current_section BETWEEN 1 AND 13", name="ck_financial_diagnostics_section"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_financial_diagnostics_user"),
    )
    op.create_index(
        "ix_financial_diagnostics_user_id", "financial_diagnostics", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_financial_diagnostics_user_id", table_name="financial_diagnostics")
    op.drop_table("financial_diagnostics")
