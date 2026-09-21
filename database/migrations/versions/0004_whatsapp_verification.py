"""Add expiring WhatsApp verification challenges.

Revision ID: 0004_whatsapp_verification
Revises: 0003_financial_diagnostic
Create Date: 2026-09-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_whatsapp_verification"
down_revision: Union[str, None] = "0003_financial_diagnostic"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_identities",
        sa.Column("verification_code_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "whatsapp_identities",
        sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "whatsapp_identities",
        sa.Column(
            "verification_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("whatsapp_identities", "verification_attempts")
    op.drop_column("whatsapp_identities", "verification_expires_at")
    op.drop_column("whatsapp_identities", "verification_code_hash")
