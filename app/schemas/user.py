from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class AllowedRegisterRole(str, Enum):
    customer = "customer"
    service_provider = "service_provider"


class UserRegisterSchema(BaseModel):
    full_name: str
    phone_number: str
    email: Optional[EmailStr] = None
    password: str
    role: AllowedRegisterRole

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters")
        return v.strip()

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not cleaned.startswith(("01", "+880")):
            raise ValueError("Phone number must be a valid Bangladeshi number")
        if cleaned.startswith("+880"):
            cleaned = "0" + cleaned[4:]
        if len(cleaned) != 11:
            raise ValueError("Phone number must be 11 digits")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLoginSchema(BaseModel):
    phone_number: str
    password: str


class UserResponseSchema(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    email: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    is_approved: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenDataSchema(BaseModel):
    user_id: Optional[str] = None
