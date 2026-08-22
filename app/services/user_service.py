from postgrest.exceptions import APIError
from app.services.db import get_db


async def create_user(
    first_name: str,
    last_name: str | None,
    email_id: str,
    phone_number: int,
    password: str,
) -> dict:
    db = get_db()
    try:
        res = db.table("users").insert({
            "first_name": first_name,
            "last_name": last_name,
            "email_id": email_id,
            "phone_number": phone_number,
            "password": password,
        }).execute()
        return res.data[0]
    except APIError as e:
        raise ValueError(str(e))


async def create_profile(user_id: str) -> None:
    db = get_db()
    db.table("profile").insert({"user_id": user_id}).execute()


async def get_user_by_email(email_id: str) -> dict | None:
    db = get_db()
    try:
        res = db.table("users").select("*").eq("email_id", email_id).single().execute()
        return res.data
    except Exception:
        return None


async def get_user_by_id(uuid: str) -> dict | None:
    db = get_db()
    try:
        res = db.table("users").select("*").eq("uuid", uuid).single().execute()
        return res.data
    except Exception:
        return None


async def mark_user_verified(user_id: str) -> None:
    db = get_db()
    db.table("users").update({"is_verified": True}).eq("uuid", user_id).execute()


async def upsert_profile(user_id: str, data: dict) -> dict:
    db = get_db()
    res = db.table("profile").upsert(
        {"user_id": user_id, **data},
        on_conflict="user_id",
    ).execute()
    return res.data[0]


async def get_profile_by_user(user_id: str) -> dict | None:
    db = get_db()
    try:
        res = db.table("profile").select("*").eq("user_id", user_id).single().execute()
        return res.data
    except Exception:
        return None


async def delete_user(uuid: str) -> None:
    db = get_db()
    db.table("users").delete().eq("uuid", uuid).execute()