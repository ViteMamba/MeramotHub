# Commit `b076a1a` — "chat with service provider added"

All changes made in this commit, file by file.

---

## 1. `app/models/message.py` — **NEW FILE**

SQLAlchemy model for private messaging between users.

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Message(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    read_at = Column(DateTime(timezone=True), nullable=True)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
```

---

## 2. `app/models/__init__.py` — **MODIFIED**

Added import and export of the `Message` model.

**Added imports (line 7):**
```python
from app.models.message import Message
```

**Added to `__all__` (line 19):**
```python
"Message",
```

---

## 3. `app/schemas/message.py` — **NEW FILE**

Pydantic schemas for messaging.

```python
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


class ConversationResponseSchema(BaseModel):
    user: ConversationUserSchema
    last_message: Optional[MessageResponseSchema] = None
    unread_count: int = 0
```

---

## 4. `app/schemas/booking.py` — **MODIFIED**

Added `provider_name` field to `BookingResponseSchema`.

**After line 32 (`updated_at: datetime`), added:**
```python
    provider_name: Optional[str] = None
```

---

## 5. `app/schemas/service.py` — **MODIFIED**

Added `provider_name` field to `ServiceItemResponseSchema`.

**After line 38 (`provider_longitude`), added:**
```python
    provider_name: Optional[str] = None
```

---

## 6. `app/routers/chat.py` — **NEW FILE**

Full chat router with 6 endpoints.

```python
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
```

---

## 7. `app/routers/bookings.py` — **MODIFIED**

### Added `_enrich_booking` helper function (after line 20):

```python
def _enrich_booking(booking, db):
    """Attach provider_name to a Booking object if provider_id is set."""
    if booking.provider_id:
        provider = db.query(User).filter(User.id == booking.provider_id).first()
        if provider:
            booking.provider_name = provider.full_name
    return booking
```

### Changed every `return booking` to `return _enrich_booking(booking, db)` in these endpoints:

| Endpoint | Line (approx) |
|---|---|
| `create_booking` | 53 |
| `get_my_bookings` | 61 |
| `get_assigned_bookings` | 75 |
| `accept_booking` | 99 |
| `start_work` | 118 |
| `complete_work` | 137 |
| `confirm_completion` | 157 |
| `cancel_booking` | 180 |

### Also changed `get_my_bookings` and `get_assigned_bookings` to collect results before returning:

**Before:**
```python
return db.query(Booking).filter(...).all()
```

**After:**
```python
bookings = db.query(Booking).filter(...).all()
return [_enrich_booking(b, db) for b in bookings]
```

---

## 8. `app/routers/chatbot.py` — **MODIFIED**

### Import changes

- Added `HTTPException`, `status` to FastAPI imports
- Added `get_db` from `app.database`
- Added `Session` from `sqlalchemy.orm`

### Schema changes

**`WhatsAppRequestSchema`**: Changed `phone_number: str` → `provider_id: UUID`

**`WhatsAppResponseSchema`**: Renamed `whatsapp_url: str` → `whatsapp_link: str`

### `get_whatsapp_link` endpoint changes

- Added `db: Session = Depends(get_db)` parameter
- Now looks up provider by `provider_id` instead of accepting raw phone number
- Validates provider exists and has a phone number
- Generates URL using `provider.phone_number` instead of request data

**Before:**
```python
url = generate_whatsapp_url(
    phone_number=wa_data.phone_number,
    message=wa_data.message or f"Hi, I'm {current_user.full_name} from MeramotHub."
)
return WhatsAppResponseSchema(whatsapp_url=url)
```

**After:**
```python
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
```

---

## 9. `app/routers/services.py` — **MODIFIED**

### `_enrich_item` function docstring updated:

`"""Attach category_name and provider_area to a ServiceItem object."""` →
`"""Attach category_name, provider_area, and provider_name to a ServiceItem object."""`

### Inside `_enrich_item`, after getting `provider`, added:

```python
item.provider_name = provider.full_name
```

---

## 10. `app/main.py` — **MODIFIED**

### Added import (line 12):
```python
from app.routers.chat import router as chat_router
```

### Added router registration (line 64):
```python
app.include_router(chat_router)
```

---

## Summary of Patterns

1. **New messaging feature**: `Message` model, message schemas, chat router with 6 endpoints (`GET /users/{id}`, `POST /messages`, `GET /conversations`, `GET /conversations/{id}/messages`, `PATCH /messages/{id}/read`).

2. **`provider_name` enrichment**: Added `provider_name` field to booking and service item response schemas, populated via `_enrich_booking` / `_enrich_item` helper functions that look up the provider's `full_name` from the `User` table.

3. **WhatsApp link rework**: Changed from accepting a raw phone number to accepting a `provider_id`, looking up the provider's phone number in the database, and returning `whatsapp_link` (renamed from `whatsapp_url`).

4. **Router registration**: New `chat` router imported and registered in `main.py`.
