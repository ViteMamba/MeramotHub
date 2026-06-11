from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class MessageCreateSchema(BaseModel):
    receiver_id: UUID
    text: str


class MessageResponseSchema(BaseModel):
    id: int
    sender_id: UUID
    receiver_id: UUID
    text: str
    created_at: datetime
    read: bool

    model_config = {"from_attributes": True}


class ChatUserResponseSchema(BaseModel):
    id: UUID
    full_name: str
    role: str
    skill_category: Optional[str] = None

    model_config = {"from_attributes": True}


class ConversationResponseSchema(BaseModel):
    user: ChatUserResponseSchema
    last_message: MessageResponseSchema
    unread_count: int

    model_config = {"from_attributes": True}
