from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.services.user_service import get_user_by_id

bearer = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = await get_user_by_id(payload["sub"])

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    return user


def require_roles(allowed_roles: list[str]):
    async def role_checker(user=Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: User role '{user.get('role')}' is not authorized."
            )
        return user
    return role_checker


require_staff_or_admin = require_roles(["staff", "admin"])
require_admin = require_roles(["admin"])


from app.services.rbac_service import get_permissions_for_role

def require_permission(required_permission: str):
    async def permission_checker(user=Depends(get_current_user)):
        user_role = user.get("role", "buyer")
        permissions = await get_permissions_for_role(user_role)
        if required_permission not in permissions and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Required permission '{required_permission}' missing for role '{user_role}'."
            )
        return user
    return permission_checker