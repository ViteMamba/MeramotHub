from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.booking import BookingType, BookingStatus

class BookingCreateSchema(BaseModel):
    service_item_id: int
    booking_type: BookingType = BookingType.standard
    scheduled_at: Optional[datetime] = None
    address: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notes: Optional[str] = None
    provider_id: Optional[UUID] = None # Optional, can be auto-assigned later

class BookingStatusUpdateSchema(BaseModel):
    status: BookingStatus

class BookingResponseSchema(BaseModel):
    id: UUID
    customer_id: UUID
    provider_id: Optional[UUID] = None
    service_item_id: int
    booking_type: BookingType
    scheduled_at: Optional[datetime] = None
    status: BookingStatus
    address: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notes: Optional[str] = None
    total_price: Decimal
    created_at: datetime
    updated_at: datetime
    provider_name: Optional[str] = None

    model_config = {"from_attributes": True}
