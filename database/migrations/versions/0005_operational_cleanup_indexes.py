"""Add indexes used by operational cleanup queries.

Revision ID: 0005_operational_cleanup_indexes
Revises: 0004_whatsapp_verification
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0005_operational_cleanup_indexes"
down_revision: Union[str, None] = "0004_whatsapp_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_agent_messages_created_at",
        "agent_messages",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_agent_tool_calls_created_at",
        "agent_tool_calls",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_pending_agent_actions_expires_at",
        "pending_agent_actions",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pending_agent_actions_expires_at", table_name="pending_agent_actions")
    op.drop_index("ix_agent_tool_calls_created_at", table_name="agent_tool_calls")
    op.drop_index("ix_agent_messages_created_at", table_name="agent_messages")
