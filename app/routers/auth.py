from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.core.security import create_access_token, generate_raw_token, hash_password, verify_password
from app.services import brevo_service, token_service, user_service
from app.services.token_service import generate_otp

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────

class RegisterIn(BaseModel):
    first_name: str
    last_name: str | None = None
    email_id: EmailStr
    phone_number: int
    password: str

class VerifyOtpIn(BaseModel):
    email_id: EmailStr
    otp: str

class LoginIn(BaseModel):
    email_id: EmailStr
    password: str

class ProfileIn(BaseModel):
    address: str
    city: str
    pincode: str
    country: str = "India"


# ── Register ──────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def register(request: Request, body: RegisterIn):

    existing = await user_service.get_user_by_email(body.email_id)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered. Please sign in.")

    try:
        user = await user_service.create_user(
            first_name=body.first_name,
            last_name=body.last_name,
            email_id=body.email_id,
            phone_number=body.phone_number,
            password=hash_password(body.password),
            role="buyer",
            is_verified=True,
        )
    except Exception as e:
        print(f"[register error] {e}")
        raise HTTPException(status_code=400, detail="Phone number or email already registered.")

    await user_service.create_profile(user["uuid"])

    return {"message": "Account created successfully! You can now log in immediately.", "user": {"uuid": user["uuid"], "email_id": user["email_id"], "role": user["role"]}}


from app.core.deps import require_admin
from app.models.rbac import StaffCreateIn

VALID_ROLES = {"buyer", "staff", "admin"}

@router.post("/admin/create-staff", status_code=status.HTTP_201_CREATED)
async def create_staff(body: StaffCreateIn, admin=Depends(require_admin)):
    existing = await user_service.get_user_by_email(body.email_id)
    if existing:
        raise HTTPException(status_code=400, detail="User email already exists.")

    try:
        staff_user = await user_service.create_user(
            first_name=body.first_name,
            last_name=body.last_name,
            email_id=body.email_id,
            phone_number=body.phone_number,
            password=hash_password(body.password),
            role="staff",
            is_verified=True,
        )
        await user_service.create_profile(staff_user["uuid"])
        return {
            "message": f"Staff user '{staff_user['email_id']}' created successfully!",
            "user": {
                "uuid": staff_user["uuid"],
                "first_name": staff_user["first_name"],
                "email_id": staff_user["email_id"],
                "role": staff_user["role"],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create staff user: {str(e)}")


# ── Admin: user management ───────────────────────────────────

class RoleUpdateIn(BaseModel):
    role: str  # "buyer" | "staff" | "admin"

class StatusUpdateIn(BaseModel):
    is_active: bool


@router.get("/admin/users")
async def list_users(admin=Depends(require_admin)):
    """List all user accounts (Admin only)."""
    return await user_service.list_all_users()


@router.patch("/admin/users/{uuid}/role")
async def change_user_role(uuid: str, body: RoleUpdateIn, admin=Depends(require_admin)):
    """Change a user's role (Admin only)."""
    if body.role not in user_service.ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Role must be one of: buyer, staff, admin")
    if uuid == admin["uuid"]:
        raise HTTPException(status_code=400, detail="You cannot change your own role")

    updated = await user_service.update_user_role(uuid, body.role)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"Role updated to {body.role}", "user": {"uuid": updated["uuid"], "role": updated["role"]}}


@router.patch("/admin/users/{uuid}/status")
async def change_user_status(uuid: str, body: StatusUpdateIn, admin=Depends(require_admin)):
    """Activate or deactivate a user account (Admin only)."""
    if uuid == admin["uuid"]:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    updated = await user_service.set_user_active_status(uuid, body.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Status updated", "user": {"uuid": updated["uuid"], "is_active": updated["is_active"]}}



# ── Verify OTP ────────────────────────────────────────────

@router.post("/verify-otp")
@limiter.limit("10/hour")
async def verify_otp(request: Request, body: VerifyOtpIn):
    user = await user_service.get_user_by_email(body.email_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid OTP or email.")

    row = await token_service.validate_verify_token(body.otp, user["uuid"])
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP. Request a new one.")

    await user_service.mark_user_verified(user["uuid"])
    await token_service.mark_token_used(row["uuid"])
    await brevo_service.send_welcome_email(user["email_id"], user["first_name"])

    return {"message": "Email verified. You can now log in."}


# ── Resend OTP ────────────────────────────────────────────

@router.post("/resend-verification")
@limiter.limit("3/hour")
async def resend_verification(request: Request, email_id: EmailStr):
    user = await user_service.get_user_by_email(email_id)
    if not user or user["is_verified"]:
        return {"message": "If that email exists and is unverified, we sent a new OTP."}

    otp, hashed = generate_otp()
    await token_service.store_verify_token(user["uuid"], hashed)
    await brevo_service.send_verification_email(user["email_id"], user["first_name"], otp)
    return {"message": "New OTP sent."}


# ── Login ─────────────────────────────────────────────────

@router.post("/login")
@limiter.limit("10/hour")
async def login(request: Request, body: LoginIn, response: Response):
    user = await user_service.get_user_by_email(body.email_id)

    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user["is_verified"]:
        raise HTTPException(status_code=403, detail="Please verify your email first")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account disabled")

    access_token = create_access_token(user["uuid"], user["role"])
    raw, hashed = generate_raw_token()
    await token_service.store_refresh_token(
        user_id=user["uuid"], hashed=hashed,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host,
    )
    response.set_cookie(
        "refresh_token", raw,
        httponly=True, secure=settings.COOKIE_SECURE, samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"uuid": user["uuid"], "first_name": user["first_name"], "role": user["role"]},
    }


# ── Logout ────────────────────────────────────────────────

@router.post("/logout")
async def logout(request: Request, response: Response, user=Depends(get_current_user)):
    raw = request.cookies.get("refresh_token")
    if raw:
        await token_service.revoke_refresh_token(raw)
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


# ── Logout all ────────────────────────────────────────────

@router.post("/logout-all")
async def logout_all(response: Response, user=Depends(get_current_user)):
    await token_service.revoke_all_refresh_tokens(user["uuid"])
    response.delete_cookie("refresh_token")
    return {"message": "All sessions revoked"}


# ── Refresh ───────────────────────────────────────────────

@router.post("/refresh")
async def refresh(request: Request, response: Response):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise HTTPException(status_code=401, detail="No refresh token")

    row = await token_service.validate_refresh_token(raw)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = await user_service.get_user_by_id(row["user_id"])
    if not user or not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account disabled")

    new_raw, new_hashed = generate_raw_token()
    await token_service.revoke_refresh_token(raw)
    await token_service.store_refresh_token(
        user_id=user["uuid"], hashed=new_hashed,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host,
    )
    response.set_cookie(
        "refresh_token", new_raw,
        httponly=True, secure=settings.COOKIE_SECURE, samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {"access_token": create_access_token(user["uuid"], user["role"]), "token_type": "bearer"}


# ── Me ────────────────────────────────────────────────────

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "uuid": user["uuid"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "email_id": user["email_id"],
        "phone_number": user["phone_number"],
        "role": user["role"],
        "is_verified": user["is_verified"],
    }


# ── Profile ───────────────────────────────────────────────

@router.post("/profile")
async def update_profile(body: ProfileIn, user=Depends(get_current_user)):
    profile = await user_service.upsert_profile(user["uuid"], body.model_dump())
    return profile