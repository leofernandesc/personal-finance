from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.models import AgentMessage, AgentToolCall, AuthSession, PendingAgentAction


@dataclass(frozen=True, slots=True)
class MaintenanceResult:
    """Counts returned by the explicit maintenance command."""

    expired_sessions: int
    expired_pending_actions: int
    pruned_agent_tool_calls: int
    pruned_agent_messages: int


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _count(db: Session, model, condition) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(condition)) or 0)


def cleanup_expired_data(
    db: Session,
    *,
    now: datetime | None = None,
    agent_log_retention_days: int = 180,
    dry_run: bool = False,
) -> MaintenanceResult:
    """Remove ephemeral data without touching financial source-of-truth rows.

    Expired sessions and confirmation challenges are safe to remove because
    they are short-lived credentials. Agent logs without a financial link are
    retained for the configured period. Messages and tool calls linked to a
    transaction or transfer remain forever as the idempotency and audit
    ledger, preventing an old WhatsApp delivery from creating a duplicate.
    """

    if agent_log_retention_days < 1:
        raise ValueError("agent_log_retention_days must be positive")

    current_time = _as_utc(now)
    log_cutoff = current_time - timedelta(days=agent_log_retention_days)

    expired_sessions = or_(
        AuthSession.expires_at <= current_time,
        and_(AuthSession.revoked_at.is_not(None), AuthSession.revoked_at <= current_time),
    )
    expired_pending_actions = PendingAgentAction.expires_at <= current_time
    old_agent_tool_calls = and_(
        AgentToolCall.created_at < log_cutoff,
        AgentToolCall.processed_at.is_not(None),
        AgentToolCall.status.in_(["success", "error"]),
        AgentToolCall.transaction_id.is_(None),
        AgentToolCall.transfer_id.is_(None),
    )
    financial_tool_message_ids = select(AgentToolCall.agent_message_id).where(
        or_(
            AgentToolCall.transaction_id.is_not(None),
            AgentToolCall.transfer_id.is_not(None),
        )
    )
    old_agent_messages = and_(
        AgentMessage.created_at < log_cutoff,
        AgentMessage.processed_at.is_not(None),
        AgentMessage.status.in_(["success", "error"]),
        AgentMessage.transaction_id.is_(None),
        AgentMessage.transfer_id.is_(None),
        ~AgentMessage.id.in_(financial_tool_message_ids),
    )

    result = MaintenanceResult(
        expired_sessions=_count(db, AuthSession, expired_sessions),
        expired_pending_actions=_count(db, PendingAgentAction, expired_pending_actions),
        pruned_agent_tool_calls=_count(db, AgentToolCall, old_agent_tool_calls),
        pruned_agent_messages=_count(db, AgentMessage, old_agent_messages),
    )

    if dry_run:
        return result

    # Tool calls must be removed before their parent messages. Financially
    # linked rows are excluded from both predicates above.
    db.execute(
        delete(AgentToolCall)
        .where(old_agent_tool_calls)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        delete(AgentMessage).where(old_agent_messages).execution_options(synchronize_session=False)
    )
    db.execute(
        delete(PendingAgentAction)
        .where(expired_pending_actions)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        delete(AuthSession).where(expired_sessions).execution_options(synchronize_session=False)
    )
    db.commit()
    return result
