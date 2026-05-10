import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SAEnum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class ComplaintStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    resolved = "resolved"
    dismissed = "dismissed"


class ComplaintResolution(str, enum.Enum):
    refunded = "refunded"
    warning_issued = "warning_issued"
    no_action = "no_action"
    provider_banned = "provider_banned"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    filed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Area Manager

    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(ComplaintStatus, native_enum=False), default=ComplaintStatus.open)
    resolution = Column(SAEnum(ComplaintResolution, native_enum=False), nullable=True)
    resolution_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    booking = relationship("Booking")
    filer = relationship("User", foreign_keys=[filed_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
