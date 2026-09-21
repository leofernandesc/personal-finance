from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_token, normalize_phone, secure_equals
from app.db.session import get_db
from app.models import AuthSession, User, WhatsAppIdentity

settings = get_settings()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> User:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária"
        )
    auth_session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(session_token))
    )
    now = datetime.now(UTC)
    if (
        not auth_session
        or auth_session.revoked_at is not None
        or _as_utc(auth_session.expires_at) <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada"
        )
    user = db.get(User, auth_session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo")
    return user


@dataclass(frozen=True)
class AgentPrincipal:
    user: User
    provider: str
    sender_id: str
    message_id: str


def _resolve_agent_principal(
    db: Session = Depends(get_db),
    agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    provider: str = Header(default="whatsapp", alias="X-Agent-Provider"),
    sender_id: str | None = Header(default=None, alias="X-Agent-Sender-Id"),
    message_id: str | None = Header(default=None, alias="X-Agent-Message-Id"),
    *,
    require_verified: bool,
) -> AgentPrincipal:
    if not agent_token or not secure_equals(agent_token, settings.agent_shared_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Agente não autorizado"
        )
    provider = provider.strip().lower()
    message_id = (message_id or "").strip()
    if not message_id or len(message_id) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador externo da mensagem ausente ou inválido",
        )
    normalized = normalize_phone(sender_id or "")
    if provider != "whatsapp" or not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Identidade WhatsApp inválida"
        )
    identity = db.scalar(
        select(WhatsAppIdentity).where(
            WhatsAppIdentity.phone_e164 == normalized,
            WhatsAppIdentity.is_active.is_(True),
        )
    )
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Número WhatsApp não vinculado"
        )
    user = db.get(User, identity.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if require_verified and identity.verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Número WhatsApp ainda não verificado",
        )
    return AgentPrincipal(
        user=user,
        provider=provider,
        sender_id=normalized,
        message_id=message_id,
    )


def get_agent_principal(
    db: Session = Depends(get_db),
    agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    provider: str = Header(default="whatsapp", alias="X-Agent-Provider"),
    sender_id: str | None = Header(default=None, alias="X-Agent-Sender-Id"),
    message_id: str | None = Header(default=None, alias="X-Agent-Message-Id"),
) -> AgentPrincipal:
    return _resolve_agent_principal(
        db,
        agent_token,
        provider,
        sender_id,
        message_id,
        require_verified=True,
    )


def get_agent_verification_principal(
    db: Session = Depends(get_db),
    agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    provider: str = Header(default="whatsapp", alias="X-Agent-Provider"),
    sender_id: str | None = Header(default=None, alias="X-Agent-Sender-Id"),
    message_id: str | None = Header(default=None, alias="X-Agent-Message-Id"),
) -> AgentPrincipal:
    """Resolve a linked identity before verification for the code-only tool.

    The only route using this dependency is the verification endpoint. It must
    never be reused by financial tools because an unverified identity has not
    proved possession of the number yet.
    """

    return _resolve_agent_principal(
        db,
        agent_token,
        provider,
        sender_id,
        message_id,
        require_verified=False,
    )
