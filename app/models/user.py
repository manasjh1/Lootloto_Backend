import re
from pydantic import BaseModel, EmailStr, field_validator


class UserResponse(BaseModel):
    uuid: str
    first_name: str
    last_name: str | None
    email_id: str
    phone_number: int
    role: str
    is_verified: bool
    is_active: bool


class ProfileResponse(BaseModel):
    uuid: str
    user_id: str
    address: str | None
    city: str | None
    pincode: str | None
    country: str


class MeResponse(BaseModel):
    user: UserResponse
    profile: ProfileResponse | None


class RegisterIn(BaseModel):
    first_name: str
    last_name: str | None = None
    email_id: EmailStr
    phone_number: int
    password: str

    @field_validator("first_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("First name cannot be empty")
        return v

    @field_validator("phone_number")
    @classmethod
    def valid_phone(cls, v: int) -> int:
        if not (1_000_000_000 <= v <= 9_999_999_999):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return v

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginIn(BaseModel):
    email_id: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileIn(BaseModel):
    address: str
    city: str
    pincode: str
    country: str = "India"

    @field_validator("pincode")
    @classmethod
    def valid_pincode(cls, v: str) -> str:
        if not re.fullmatch(r"[1-9][0-9]{5}", v):
            raise ValueError("Enter a valid 6-digit Indian pincode")
        return v


class MessageResponse(BaseModel):
    message: str