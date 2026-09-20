from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import normalize_phone
from app.db.session import get_db
from app.models import User, WhatsAppIdentity
from app.schemas.agent import AgentLinkRequest

router = APIRouter(prefix="/integrations/whatsapp", tags=["integrations"])


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
        identity.is_active = True
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
    db.commit()
    db.refresh(identity)
    return {"linked": True, "phone_e164": identity.phone_e164, "verified": False}


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
    db.commit()
    return {"linked": False}
