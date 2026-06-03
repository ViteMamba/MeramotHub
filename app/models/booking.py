import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SAEnum, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class BookingType(str, enum.Enum):
    standard = "standard"
    emergency = "emergency"
    instant = "instant"

class BookingStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    started = "started"
    pending_completion = "pending_completion"
    completed = "completed"
    cancelled = "cancelled"
    disputed = "disputed"

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True) # Null for emergency/pending assignment
    service_item_id = Column(Integer, ForeignKey("service_items.id"), nullable=False)
    
    booking_type = Column(SAEnum(BookingType, native_enum=False), nullable=False, default=BookingType.standard)
    scheduled_at = Column(DateTime(timezone=True), nullable=True) # Null for emergency/instant
    status = Column(SAEnum(BookingStatus, native_enum=False), nullable=False, default=BookingStatus.pending)
    
    address = Column(String(255), nullable=False)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    notes = Column(Text, nullable=True)
    
    total_price = Column(Numeric(10, 2), nullable=False) # Copied from ServiceItem at booking time
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id])
    provider = relationship("User", foreign_keys=[provider_id])
    service_item = relationship("ServiceItem")
