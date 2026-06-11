from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.payment import PaymentStatus

class PaymentInitSchema(BaseModel):
    booking_id: UUID
    mfs_transaction_id: str

class PaymentResponseSchema(BaseModel):
    id: int
    booking_id: UUID
    customer_id: UUID
    provider_id: UUID
    amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    provider_amount: Decimal
    status: PaymentStatus
    payment_method: Optional[str]
    mfs_transaction_id: Optional[str]
    paid_at: Optional[datetime]
    released_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
