from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Numeric, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.service_provider import SkillCategory

class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    skill_required = Column(SAEnum(SkillCategory, native_enum=False), nullable=False)
    
    items = relationship("ServiceItem", back_populates="category")

class ServiceItem(Base):
    __tablename__ = "service_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String(100), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(50), default="per unit") # e.g. "per hour", "per unit"
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    category = relationship("ServiceCategory", back_populates="items")
