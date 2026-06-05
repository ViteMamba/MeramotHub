from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.service_provider import VerificationStatus

class ProfileCreateSchema(BaseModel):
    nid_number: str
    nid_image_url: Optional[str] = None
    skill_category: str
    experience_years: int
    bio: Optional[str] = None
    area: Optional[str] = None

class ProfileUpdateSchema(BaseModel):
    nid_image_url: Optional[str] = None
    skill_category: Optional[str] = None
    experience_years: Optional[int] = None
    bio: Optional[str] = None

class ProfileResponseSchema(BaseModel):
    id: int
    user_id: UUID
    nid_image_url: Optional[str] = None
    skill_category: str
    experience_years: int
    bio: Optional[str] = None
    is_available: bool = False
    last_seen_at: Optional[datetime] = None
    rating_avg: Optional[Decimal] = None
    rating_count: Optional[int] = None
    verification_status: VerificationStatus
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class LocationUpdateSchema(BaseModel):
    latitude: Decimal
    longitude: Decimal
    is_available: bool = True

class VerificationActionSchema(BaseModel):
    action: VerificationStatus # verified or rejected
    note: Optional[str] = None

