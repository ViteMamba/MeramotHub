from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User, UserRole
from app.models.service_provider import ServiceProviderProfile
from app.models.message import Message
from app.utils.auth import get_current_user
from app.utils.rate_limiter import chatbot_limiter
from app.utils.whatsapp import generate_whatsapp_url
from app.services.chatbot_service import get_chatbot_response
from app.schemas.chat import (
    MessageCreateSchema,
    MessageResponseSchema,
    ChatUserResponseSchema,
    ConversationResponseSchema,
)

router = APIRouter(prefix="/chat", tags=["AI Chatbot & Communication"])


class ChatMessageSchema(BaseModel):
    message: str


class ChatResponseSchema(BaseModel):
    reply: str


class WhatsAppRequestSchema(BaseModel):
    phone_number: str
    message: Optional[str] = ""


class WhatsAppResponseSchema(BaseModel):
    whatsapp_url: str


@router.post("/bot", response_model=ChatResponseSchema)
async def chat_with_bot(
    chat_data: ChatMessageSchema,
    current_user: User = Depends(get_current_user)
):
    """Send a message to the AI chatbot. Rate-limited to 10 requests/minute per user."""
    # Apply rate limiting
    chatbot_limiter.check(str(current_user.id))

    reply = await get_chatbot_response(
        user_message=chat_data.message,
        user_name=current_user.full_name,
    )
    return ChatResponseSchema(reply=reply)


@router.post("/whatsapp", response_model=WhatsAppResponseSchema)
def get_whatsapp_link(
    wa_data: WhatsAppRequestSchema,
    current_user: User = Depends(get_current_user)
):
    """Generate a WhatsApp click-to-chat URL for contacting a provider."""
    url = generate_whatsapp_url(
        phone_number=wa_data.phone_number,
        message=wa_data.message or f"Hi, I'm {current_user.full_name} from MeramotHub."
    )
    return WhatsAppResponseSchema(whatsapp_url=url)


# ──── In-platform Messaging Endpoints ────

@router.post("/messages", response_model=MessageResponseSchema)
def send_message(
    data: MessageCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a chat message to another user."""
    # Verify receiver exists
    receiver = db.query(User).filter(User.id == data.receiver_id).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )

    new_msg = Message(
        sender_id=current_user.id,
        receiver_id=data.receiver_id,
        text=data.text,
        read=False,
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg


@router.get("/conversations", response_model=List[ConversationResponseSchema])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all active conversations for the current user."""
    # Query all messages sent to/from the current user ordered by creation date desc
    messages = (
        db.query(Message)
        .filter(or_(Message.sender_id == current_user.id, Message.receiver_id == current_user.id))
        .order_by(Message.created_at.desc())
        .all()
    )

    conversations_dict = {}
    for msg in messages:
        other_user_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        if other_user_id not in conversations_dict:
            conversations_dict[other_user_id] = msg

    result = []
    for other_user_id, last_msg in conversations_dict.items():
        other_user = db.query(User).filter(User.id == other_user_id).first()
        if not other_user:
            continue

        skill_category = None
        if other_user.role == UserRole.service_provider:
            profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == other_user.id).first()
            if profile:
                skill_category = profile.skill_category.value if hasattr(profile.skill_category, 'value') else str(profile.skill_category)

        # Unread count (messages sent by other user to current user that are unread)
        unread_count = (
            db.query(func.count(Message.id))
            .filter(
                and_(
                    Message.sender_id == other_user_id,
                    Message.receiver_id == current_user.id,
                    Message.read == False
                )
            )
            .scalar() or 0
        )

        result.append({
            "user": {
                "id": other_user.id,
                "full_name": other_user.full_name,
                "role": other_user.role.value,
                "skill_category": skill_category,
            },
            "last_message": last_msg,
            "unread_count": unread_count,
        })

    return result


@router.get("/conversations/{user_id}/messages", response_model=List[MessageResponseSchema])
def get_conversation_messages(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve message log between current user and specified user."""
    messages = (
        db.query(Message)
        .filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
                and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    # Mark all unread incoming messages as read
    unread_incoming = [m for m in messages if m.sender_id == user_id and not m.read]
    if unread_incoming:
        for m in unread_incoming:
            m.read = True
        db.commit()

    return messages


@router.get("/users/{user_id}", response_model=ChatUserResponseSchema)
def get_chat_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve chat participant's details."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    skill_category = None
    if user.role == UserRole.service_provider:
        profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == user.id).first()
        if profile:
            skill_category = profile.skill_category.value if hasattr(profile.skill_category, 'value') else str(profile.skill_category)

    return {
        "id": user.id,
        "full_name": user.full_name,
        "role": user.role.value,
        "skill_category": skill_category,
    }

