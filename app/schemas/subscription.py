from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class SubscriptionCreateSchema(BaseModel):
    plan_name: str = "priyo_basic"


class SubscriptionResponseSchema(BaseModel):
    id: int
    provider_user_id: UUID
    plan_name: str
    is_active: bool
    monthly_fee: Decimal
    started_at: datetime
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InstantBookingCreateSchema(BaseModel):
    service_item_id: int
    address: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notes: Optional[str] = None
