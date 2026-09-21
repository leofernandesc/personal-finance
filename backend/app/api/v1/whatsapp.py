import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import normalize_phone
from app.db.session import get_db
from app.models import User, WhatsAppIdentity
from app.schemas.agent import AgentLinkRequest

router = APIRouter(prefix="/integrations/whatsapp", tags=["integrations"])
settings = get_settings()
VERIFICATION_TTL = timedelta(minutes=10)


def _verification_digest(phone_e164: str, code: str) -> str:
    value = f"{phone_e164}:{code}".encode()
    return hmac.new(settings.agent_shared_secret.encode(), value, hashlib.sha256).hexdigest()


def _clear_verification(identity: WhatsAppIdentity) -> None:
    identity.verification_code_hash = None
    identity.verification_expires_at = None
    identity.verification_attempts = 0


@router.get("/identity")
def whatsapp_identity(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    identity = db.scalar(
        select(WhatsAppIdentity).where(
            WhatsAppIdentity.user_id == user.id,
            WhatsAppIdentity.is_active.is_(True),
        )
    )
    return {
        "linked": identity is not None,
        "phone_e164": identity.phone_e164 if identity else None,
        "verified": bool(identity and identity.verified_at),
    }


@router.post("/link", status_code=status.HTTP_201_CREATED)
def link_whatsapp(
    payload: AgentLinkRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    phone_e164 = normalize_phone(payload.phone_e164)
    if not phone_e164:
        raise HTTPException(status_code=422, detail="Número WhatsApp inválido")
    identity = db.scalar(select(WhatsAppIdentity).where(WhatsAppIdentity.phone_e164 == phone_e164))
    if identity and identity.user_id != user.id:
        raise HTTPException(status_code=409, detail="Esse número já está vinculado a outro usuário")
    if identity:
        was_active = identity.is_active
        identity.is_active = True
        if not was_active:
            identity.verified_at = None
            _clear_verification(identity)
        elif identity.verified_at is None:
            _clear_verification(identity)
    else:
        identity = WhatsAppIdentity(
            user_id=user.id,
            phone_e164=phone_e164,
            verified_at=None,
            is_active=True,
        )
        db.add(identity)
    for previous in db.scalars(
        select(WhatsAppIdentity).where(
            WhatsAppIdentity.user_id == user.id,
            WhatsAppIdentity.phone_e164 != phone_e164,
            WhatsAppIdentity.is_active.is_(True),
        )
    ):
        previous.is_active = False
        previous.verified_at = None
        _clear_verification(previous)
    db.commit()
    db.refresh(identity)
    return {
        "linked": True,
        "phone_e164": identity.phone_e164,
        "verified": bool(identity.verified_at),
    }


@router.post("/verification/start")
def start_whatsapp_verification(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    identity = db.scalar(
        select(WhatsAppIdentity).where(
            WhatsAppIdentity.user_id == user.id,
            WhatsAppIdentity.is_active.is_(True),
        )
    )
    if not identity:
        raise HTTPException(
            status_code=404,
            detail="Vincule um número WhatsApp antes de verificá-lo",
        )
    if identity.verified_at is not None:
        raise HTTPException(status_code=409, detail="Número WhatsApp já verificado")

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(UTC) + VERIFICATION_TTL
    identity.verification_code_hash = _verification_digest(identity.phone_e164, code)
    identity.verification_expires_at = expires_at
    identity.verification_attempts = 0
    db.commit()
    return {
        "verified": False,
        "code": code,
        "expires_at": expires_at,
        "instructions": (
            "Envie este código pelo WhatsApp vinculado para confirmar a posse do número."
        ),
    }


@router.delete("/link")
def unlink_whatsapp(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    identities = list(
        db.scalars(
            select(WhatsAppIdentity).where(
                WhatsAppIdentity.user_id == user.id,
                WhatsAppIdentity.is_active.is_(True),
            )
        )
    )
    for identity in identities:
        identity.is_active = False
        identity.verified_at = None
        _clear_verification(identity)
    db.commit()
    return {"linked": False}
