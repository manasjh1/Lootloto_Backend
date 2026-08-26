from pydantic import BaseModel, EmailStr, field_validator
import re


class StaffCreateIn(BaseModel):
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
            raise ValueError("Enter a valid 10-digit mobile number")
        return v

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class PermissionResponse(BaseModel):
    code: str
    name: str
    description: str | None = None


class RoleResponse(BaseModel):
    name: str
    description: str
    permissions: list[PermissionResponse] = []
