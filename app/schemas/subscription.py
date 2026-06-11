from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class SubscriptionCreateSchema(BaseModel):
    plan_name: str = "priyo_basic"
    mfs_transaction_id: Optional[str] = None


class SubscriptionResponseSchema(BaseModel):
    id: int
    user_id: UUID
    plan_name: str
    is_active: bool
    monthly_fee: Decimal
    mfs_transaction_id: Optional[str] = None
    started_at: datetime
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionCheckSchema(BaseModel):
    is_active: bool
    plan_name: Optional[str] = None
    expires_at: Optional[datetime] = None


class InstantBookingCreateSchema(BaseModel):
    service_item_id: int
    address: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notes: Optional[str] = None


class FavoriteProviderResponseSchema(BaseModel):
    id: int
    customer_id: UUID
    provider_id: UUID
    created_at: datetime
    provider_name: Optional[str] = None
    provider_area: Optional[str] = None
    provider_phone: Optional[str] = None
    customer_name: Optional[str] = None
    provider_skill: Optional[str] = None

    model_config = {"from_attributes": True}

