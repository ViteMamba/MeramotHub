import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SAEnum, DateTime, Text, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class SkillCategory(str, enum.Enum):
    electrician = "electrician"
    plumber = "plumber"
    ac_mechanic = "ac_mechanic"
    carpenter = "carpenter"
    painter = "painter"
    welder = "welder"
    mason = "mason"
    other = "other"

class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"

class ServiceProviderProfile(Base):
    __tablename__ = "service_provider_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    nid_number = Column(String(20), unique=True, nullable=False)
    nid_image_url = Column(String(255), nullable=True)
    skill_category = Column(SAEnum(SkillCategory, native_enum=False), nullable=False)
    experience_years = Column(Integer, default=0)
    bio = Column(Text, nullable=True)
    area = Column(String(100), nullable=True)
    
    # Feature 7 & 16: Location and Availability
    current_latitude = Column(Numeric(10, 7), nullable=True)
    current_longitude = Column(Numeric(10, 7), nullable=True)
    is_available = Column(Boolean, default=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    # Feature 8: Ratings (recalculated on every review)
    rating_avg = Column(Numeric(3, 2), default=0.0)
    rating_count = Column(Integer, default=0)
    
    verification_status = Column(SAEnum(VerificationStatus, native_enum=False), default=VerificationStatus.pending)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
