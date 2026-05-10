import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    provider_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    plan_name = Column(String(50), nullable=False, default="priyo_basic")  # priyo_basic, priyo_premium
    is_active = Column(Boolean, default=True)
    monthly_fee = Column(Numeric(10, 2), default=500.00)  # BDT per month

    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    provider = relationship("User", foreign_keys=[provider_user_id])
