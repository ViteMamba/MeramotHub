from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.complaint import ComplaintStatus, ComplaintResolution


class ComplaintCreateSchema(BaseModel):
    booking_id: UUID
    subject: str
    description: str


class ComplaintAssignSchema(BaseModel):
    assigned_to: UUID  # Area Manager user ID


class ComplaintResolveSchema(BaseModel):
    resolution: ComplaintResolution
    resolution_note: Optional[str] = None


class ComplaintResponseSchema(BaseModel):
    id: int
    booking_id: UUID
    filed_by: UUID
    assigned_to: Optional[UUID] = None
    subject: str
    description: str
    status: ComplaintStatus
    resolution: Optional[ComplaintResolution] = None
    resolution_note: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
