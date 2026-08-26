import pytest
from app.services.rbac_service import get_permissions_for_role


@pytest.mark.asyncio
async def test_role_permissions():
    buyer_perms = await get_permissions_for_role("buyer")
    assert "catalog:read" in buyer_perms
    assert "catalog:write" not in buyer_perms

    staff_perms = await get_permissions_for_role("staff")
    assert "catalog:read" in staff_perms
    assert "catalog:write" in staff_perms
    assert "users:create_staff" not in staff_perms

    admin_perms = await get_permissions_for_role("admin")
    assert "catalog:read" in admin_perms
    assert "catalog:write" in admin_perms
    assert "inventory:view_cost" in admin_perms
    assert "users:create_staff" in admin_perms
