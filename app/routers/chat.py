from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.message import Message
from app.schemas.message import (
    MessageSendSchema,
    MessageResponseSchema,
    ConversationResponseSchema,
    ConversationUserSchema,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["Messaging"])


@router.get("/users/{user_id}", response_model=ConversationUserSchema)
def get_user_brief(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get basic info about a user (for starting a new conversation)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return ConversationUserSchema(
        id=user.id,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role.value,
    )


@router.post("/messages", response_model=MessageResponseSchema, status_code=status.HTTP_201_CREATED)
def send_message(
    msg_data: MessageSendSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a private message to another user."""
    if current_user.id == msg_data.receiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a message to yourself",
        )

    receiver = db.query(User).filter(User.id == msg_data.receiver_id).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found",
        )

    message = Message(
        sender_id=current_user.id,
        receiver_id=msg_data.receiver_id,
        text=msg_data.text,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("/conversations", response_model=List[ConversationResponseSchema])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all conversations for the current user, with last message and unread count."""
    # Find all distinct users the current user has exchanged messages with
    partner_ids = (
        db.query(Message.sender_id)
        .filter(Message.receiver_id == current_user.id)
        .union(
            db.query(Message.receiver_id).filter(Message.sender_id == current_user.id)
        )
        .distinct()
        .all()
    )

    conversations = []
    for (partner_id,) in partner_ids:
        partner = db.query(User).filter(User.id == partner_id).first()
        if not partner:
            continue

        last_message = (
            db.query(Message)
            .filter(
                or_(
                    and_(
                        Message.sender_id == current_user.id,
                        Message.receiver_id == partner_id,
                    ),
                    and_(
                        Message.sender_id == partner_id,
                        Message.receiver_id == current_user.id,
                    ),
                )
            )
            .order_by(Message.created_at.desc())
            .first()
        )

        unread_count = (
            db.query(Message)
            .filter(
                Message.sender_id == partner_id,
                Message.receiver_id == current_user.id,
                Message.read == False,
            )
            .count()
        )

        conversations.append(
            ConversationResponseSchema(
                user=ConversationUserSchema(
                    id=partner.id,
                    full_name=partner.full_name,
                    phone_number=partner.phone_number,
                    role=partner.role.value,
                ),
                last_message=last_message,
                unread_count=unread_count,
            )
        )

    # Sort by most recent message first
    conversations.sort(
        key=lambda c: c.last_message.created_at if c.last_message else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    return conversations


@router.get(
    "/conversations/{user_id}/messages",
    response_model=List[MessageResponseSchema],
)
def get_conversation_messages(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get messages between current user and another user, ordered by time."""
    messages = (
        db.query(Message)
        .filter(
            or_(
                and_(
                    Message.sender_id == current_user.id,
                    Message.receiver_id == user_id,
                ),
                and_(
                    Message.sender_id == user_id,
                    Message.receiver_id == current_user.id,
                ),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    # Mark unread messages from other user as read
    for msg in messages:
        if msg.sender_id == user_id and msg.receiver_id == current_user.id and not msg.read:
            msg.read = True
            msg.read_at = datetime.now(timezone.utc)
    db.commit()

    return messages


@router.patch("/messages/{message_id}/read", response_model=MessageResponseSchema)
def mark_message_read(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a specific message as read."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if message.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only mark your own received messages as read",
        )

    message.read = True
    message.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message
