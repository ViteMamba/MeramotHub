from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class MessageSendSchema(BaseModel):
    receiver_id: UUID
    text: str


class MessageResponseSchema(BaseModel):
    id: UUID
    sender_id: UUID
    receiver_id: UUID
    text: str
    read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConversationUserSchema(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    role: str
    skill_category: Optional[str] = None


class ConversationResponseSchema(BaseModel):
    user: ConversationUserSchema
    last_message: Optional[MessageResponseSchema] = None
    unread_count: int = 0
