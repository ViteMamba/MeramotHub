from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from app.models.service_provider import SkillCategory

class CategoryCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    skill_required: SkillCategory

class CategoryResponseSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    skill_required: SkillCategory

    model_config = {"from_attributes": True}

class ServiceItemCreateSchema(BaseModel):
    category_id: int
    name: str
    base_price: Decimal
    unit: str = "per unit"
    description: Optional[str] = None

class ServiceItemResponseSchema(BaseModel):
    id: int
    category_id: int
    provider_id: Optional[UUID] = None
    name: str
    base_price: Decimal
    unit: str
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    category_name: Optional[str] = None
    provider_area: Optional[str] = None
    provider_latitude: Optional[Decimal] = None
    provider_longitude: Optional[Decimal] = None

    class Config:
        from_attributes = True

class ServiceItemUpdateSchema(BaseModel):
    name: Optional[str] = None
    base_price: Optional[Decimal] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
