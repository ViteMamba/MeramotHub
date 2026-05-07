from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.service_provider import SkillCategory, VerificationStatus

class ProfileCreateSchema(BaseModel):
    nid_number: str
    nid_image_url: Optional[str] = None
    skill_category: SkillCategory
    experience_years: int
    bio: Optional[str] = None
    area: Optional[str] = None

class ProfileUpdateSchema(BaseModel):
    nid_image_url: Optional[str] = None
    skill_category: Optional[SkillCategory] = None
    experience_years: Optional[int] = None
    bio: Optional[str] = None
    area: Optional[str] = None

class ProfileResponseSchema(BaseModel):
    id: int
    user_id: UUID
    nid_number: str
    nid_image_url: Optional[str] = None
    skill_category: SkillCategory
    experience_years: int
    bio: Optional[str] = None
    area: Optional[str] = None
    current_latitude: Optional[Decimal] = None
    current_longitude: Optional[Decimal] = None
    is_available: bool = False
    last_seen_at: Optional[datetime] = None
    rating_avg: Decimal = 0.0
    rating_count: int = 0
    verification_status: VerificationStatus
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VerificationActionSchema(BaseModel):
    action: VerificationStatus # verified or rejected
    note: Optional[str] = None
