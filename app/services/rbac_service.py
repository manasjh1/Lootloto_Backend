from app.services.db import get_db

DEFAULT_ROLE_PERMISSIONS = {
    "buyer": ["catalog:read"],
    "staff": ["catalog:read", "catalog:write"],
    "admin": ["catalog:read", "catalog:write", "inventory:view_cost", "users:create_staff", "users:manage_all"]
}


async def get_permissions_for_role(role_name: str) -> list[str]:
    """Fetch permission codes assigned to a given role."""
    db = get_db()
    try:
        res = db.table("role_permissions").select("permission_code").eq("role_name", role_name).execute()
        if res.data:
            return [row["permission_code"] for row in res.data]
    except Exception as e:
        print(f"[RBAC Service Warning] Could not fetch role permissions from DB: {e}")

    # Fallback to default in-memory permission mapping if table doesn't exist yet
    return DEFAULT_ROLE_PERMISSIONS.get(role_name, ["catalog:read"])


async def list_roles_and_permissions() -> list[dict]:
    db = get_db()
    try:
        roles_res = db.table("roles").select("*").execute()
        perms_res = db.table("role_permissions").select("*, permissions(*)").execute()
        
        roles = roles_res.data or []
        rp_data = perms_res.data or []

        for role in roles:
            role["permissions"] = [
                rp["permissions"] for rp in rp_data if rp.get("role_name") == role["name"] and rp.get("permissions")
            ]
        return roles
    except Exception:
        # Fallback response
        return [
            {"name": k, "description": f"{k.capitalize()} role", "permissions": v}
            for k, v in DEFAULT_ROLE_PERMISSIONS.items()
        ]
