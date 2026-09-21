from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AgentMessage, AgentToolCall, User


class AgentIdentity(Protocol):
    user: User
    provider: str
    sender_id: str
    message_id: str


@dataclass
class AgentOperation:
    message: AgentMessage
    tool_call: AgentToolCall

    def link_transaction(self, transaction_id: UUID) -> None:
        self.message.transaction_id = transaction_id
        self.tool_call.transaction_id = transaction_id

    def link_transfer(self, transfer_id: UUID) -> None:
        self.message.transfer_id = transfer_id
        self.tool_call.transfer_id = transfer_id


def _message_hash(principal: AgentIdentity) -> str:
    envelope = f"{principal.provider}:{principal.sender_id}:{principal.message_id}"
    return hashlib.sha256(envelope.encode("utf-8")).hexdigest()


def _get_or_create_message(db: Session, principal: AgentIdentity) -> AgentMessage:
    message = db.scalar(
        select(AgentMessage).where(
            AgentMessage.provider == principal.provider,
            AgentMessage.sender_id == principal.sender_id,
            AgentMessage.external_message_id == principal.message_id,
        )
    )
    if message:
        return message
    message = AgentMessage(
        provider=principal.provider,
        external_message_id=principal.message_id,
        sender_id=principal.sender_id,
        user_id=principal.user.id,
        text_hash=_message_hash(principal),
        status="received",
    )
    try:
        with db.begin_nested():
            db.add(message)
            db.flush()
        return message
    except IntegrityError:
        concurrent = db.scalar(
            select(AgentMessage).where(
                AgentMessage.provider == principal.provider,
                AgentMessage.sender_id == principal.sender_id,
                AgentMessage.external_message_id == principal.message_id,
            )
        )
        if concurrent:
            return concurrent
        raise


def _error_code(error: Exception) -> str:
    if isinstance(error, HTTPException):
        if isinstance(error.detail, dict) and error.detail.get("code"):
            return str(error.detail["code"])[:80]
        return f"HTTP_{error.status_code}"
    return type(error).__name__[:80]


def _record_failed_call(
    db: Session,
    principal: AgentIdentity,
    *,
    intent: str,
    tool_name: str,
    error: Exception,
) -> None:
    record_agent_tool_result(
        db,
        principal,
        intent=intent,
        tool_name=tool_name,
        error=error,
    )


def record_agent_tool_result(
    db: Session,
    principal: AgentIdentity,
    *,
    intent: str,
    tool_name: str,
    error: Exception | None = None,
) -> None:
    """Persist an agent result without storing message text or tool payloads.

    This is used by non-financial agent operations, such as WhatsApp
    possession verification, that still need the same technical audit trail as
    financial tools but do not fit the financial-operation context manager.
    Any changes already made in the current request are committed together
    with the audit row.
    """
    message = _get_or_create_message(db, principal)
    now = datetime.now(UTC)
    status = "error" if error is not None else "success"
    code = _error_code(error) if error is not None else None
    message.user_id = principal.user.id
    message.intent = intent
    message.tool_name = tool_name
    message.status = status
    message.error_code = code
    message.transaction_id = None
    message.transfer_id = None
    message.processed_at = now
    db.add(
        AgentToolCall(
            agent_message_id=message.id,
            user_id=principal.user.id,
            intent=intent,
            tool_name=tool_name,
            status=status,
            error_code=code,
            processed_at=now,
        )
    )
    db.commit()


@contextmanager
def audited_agent_operation(
    db: Session,
    principal: AgentIdentity,
    *,
    intent: str,
    tool_name: str,
) -> Iterator[AgentOperation]:
    """Commit a financial operation and its technical audit row atomically.

    Failures roll back financial changes first and are then recorded in a fresh
    transaction. Payloads and message text are deliberately excluded.
    """

    message = _get_or_create_message(db, principal)
    message.user_id = principal.user.id
    message.intent = intent
    message.tool_name = tool_name
    message.status = "processing"
    message.error_code = None
    message.transaction_id = None
    message.transfer_id = None
    tool_call = AgentToolCall(
        agent_message_id=message.id,
        user_id=principal.user.id,
        intent=intent,
        tool_name=tool_name,
        status="processing",
    )
    db.add(tool_call)
    db.flush()
    operation = AgentOperation(message=message, tool_call=tool_call)
    try:
        yield operation
    except Exception as error:
        db.rollback()
        _record_failed_call(
            db,
            principal,
            intent=intent,
            tool_name=tool_name,
            error=error,
        )
        raise
    else:
        now = datetime.now(UTC)
        message.status = "success"
        message.error_code = None
        message.processed_at = now
        tool_call.status = "success"
        tool_call.processed_at = now
        db.commit()
