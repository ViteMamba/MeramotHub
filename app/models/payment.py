import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SAEnum, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    held = "held"
    released = "released"
    refunded = "refunded"

class PaymentMethod(str, enum.Enum):
    bkash = "bkash"
    nagad = "nagad"
    card = "card"
    bank = "bank"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    amount = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(4, 2), default=0.10) # 10%
    commission_amount = Column(Numeric(10, 2), nullable=False)
    provider_amount = Column(Numeric(10, 2), nullable=False)
    
    status = Column(SAEnum(PaymentStatus, native_enum=False), default=PaymentStatus.pending)
    payment_method = Column(String(20), nullable=True)
    mfs_transaction_id = Column(String(100), nullable=True) # Transaction reference
    
    paid_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    booking = relationship("Booking")
    customer = relationship("User", foreign_keys=[customer_id])
    provider = relationship("User", foreign_keys=[provider_id])
