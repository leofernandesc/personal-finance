import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def new_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def secure_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def session_expiry(ttl_hours: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=ttl_hours)


def normalize_phone(value: str) -> str:
    """Normalize Baileys/Twilio-style WhatsApp IDs to a comparable E.164 value."""
    raw = (value or "").strip()
    raw = re.sub(r"^(whatsapp:|waid:)", "", raw, flags=re.IGNORECASE)
    raw = raw.split("@", 1)[0]
    digits = re.sub(r"\D", "", raw)
    if not 8 <= len(digits) <= 15:
        return ""
    return f"+{digits}"
