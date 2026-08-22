import random
import hashlib
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import hash_token
from app.services.db import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def generate_otp() -> tuple[str, str]:
    """Returns (raw_6digit, sha256_hash)."""
    raw = f"{random.randint(0, 999999):06d}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


async def store_verify_token(user_id: str, hashed: str) -> None:
    db = get_db()
    db.table("email_verifications").delete().eq("user_id", user_id).execute()
    db.table("email_verifications").insert({
        "user_id": user_id,
        "token": hashed,
        "expires_at": _iso(_now() + timedelta(minutes=10)),
        "used_at": None,
    }).execute()


async def validate_verify_token(raw: str, user_id: str) -> dict | None:
    db = get_db()
    try:
        res = (
            db.table("email_verifications")
            .select("*")
            .eq("token", hashlib.sha256(raw.encode()).hexdigest())
            .eq("user_id", user_id)
            .is_("used_at", "null")
            .single()
            .execute()
        )
    except Exception:
        return None
    row = res.data
    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) < _now():
        return None
    return row


async def mark_token_used(token_id: str) -> None:
    db = get_db()
    db.table("email_verifications").update(
        {"used_at": _iso(_now())}
    ).eq("uuid", token_id).execute()


async def store_refresh_token(user_id: str, hashed: str, user_agent: str, ip: str) -> None:
    db = get_db()
    db.table("refresh_tokens").insert({
        "user_id": user_id,
        "token": hashed,
        "expires_at": _iso(_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)),
        "user_agent": user_agent,
        "ip_address": ip,
    }).execute()


async def validate_refresh_token(raw: str) -> dict | None:
    db = get_db()
    try:
        res = (
            db.table("refresh_tokens")
            .select("*")
            .eq("token", hash_token(raw))
            .is_("revoked_at", "null")
            .single()
            .execute()
        )
    except Exception:
        return None
    row = res.data
    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) < _now():
        return None
    return row


async def revoke_refresh_token(raw: str) -> None:
    db = get_db()
    db.table("refresh_tokens").update(
        {"revoked_at": _iso(_now())}
    ).eq("token", hash_token(raw)).execute()


async def revoke_all_refresh_tokens(user_id: str) -> None:
    db = get_db()
    db.table("refresh_tokens").update(
        {"revoked_at": _iso(_now())}
    ).eq("user_id", user_id).is_("revoked_at", "null").execute()