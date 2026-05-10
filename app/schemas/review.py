from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class ReviewCreateSchema(BaseModel):
    booking_id: UUID
    rating: int  # 1-5
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewResponseSchema(BaseModel):
    id: int
    booking_id: UUID
    customer_id: UUID
    provider_id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
