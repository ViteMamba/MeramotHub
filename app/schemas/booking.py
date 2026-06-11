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

class PayAndBookSchema(BaseModel):
    service_item_id: int
    address: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None
    payment_method: str
    mfs_transaction_id: str

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
    provider_phone: Optional[str] = None
    provider_area: Optional[str] = None
    provider_latitude: Optional[Decimal] = None
    provider_longitude: Optional[Decimal] = None
    service_name: Optional[str] = None
    customer_name: Optional[str] = None

    model_config = {"from_attributes": True}

class PayAndBookResponseSchema(BaseModel):
    booking: BookingResponseSchema
    payment_id: Optional[int] = None
    payment_status: Optional[str] = None
    amount_paid: Optional[Decimal] = None
    mfs_transaction_id: Optional[str] = None

    model_config = {"from_attributes": True}
