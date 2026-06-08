from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.database import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.rate_limiter import chatbot_limiter
from app.utils.whatsapp import generate_whatsapp_url
from app.services.chatbot_service import get_chatbot_response

router = APIRouter(prefix="/chat", tags=["AI Chatbot & Communication"])


class ChatMessageSchema(BaseModel):
    message: str


class ChatResponseSchema(BaseModel):
    reply: str


class WhatsAppRequestSchema(BaseModel):
    provider_id: UUID
    message: Optional[str] = ""


class WhatsAppResponseSchema(BaseModel):
    whatsapp_link: str


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a WhatsApp click-to-chat URL for contacting a provider by provider_id."""
    provider = db.query(User).filter(User.id == wa_data.provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    if not provider.phone_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider has no phone number on file")

    url = generate_whatsapp_url(
        phone_number=provider.phone_number,
        message=wa_data.message or f"Hi, I'm {current_user.full_name} from MeramotHub."
    )
    return WhatsAppResponseSchema(whatsapp_link=url)
