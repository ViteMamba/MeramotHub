from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.auth import get_current_user
from app.services.payment_service import release_payment
from app.models.service import ServiceItem
from app.models.booking import Booking, BookingStatus, BookingType
from app.models.payment import Payment, PaymentStatus
from app.schemas.booking import (
    BookingCreateSchema,
    BookingWithPaymentSchema,
    BookingResponseSchema,
    BookingStatusUpdateSchema,
)
from app.utils.roles import require_role

router = APIRouter(prefix="/bookings", tags=["Bookings"])

def _enrich_booking(booking, db):
    """Attach provider_name to a Booking object if provider_id is set."""
    if booking.provider_id:
        provider = db.query(User).filter(User.id == booking.provider_id).first()
        if provider:
            booking.provider_name = provider.full_name
    return booking

@router.post("/", response_model=BookingResponseSchema, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: BookingCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer creates a new booking."""
    # Verify service item exists
    service_item = db.query(ServiceItem).filter(ServiceItem.id == booking_data.service_item_id).first()
    if not service_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")
    
    new_booking = Booking(
        customer_id=current_user.id,
        **booking_data.model_dump(),
        total_price=service_item.base_price, # Freeze price at booking time
        status=BookingStatus.pending
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return _enrich_booking(new_booking, db)

@router.post("/pay-and-book", response_model=BookingResponseSchema, status_code=status.HTTP_201_CREATED)
def pay_and_book(
    booking_data: BookingWithPaymentSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer creates a booking and pays immediately. Funds held in escrow."""
    service_item = db.query(ServiceItem).filter(ServiceItem.id == booking_data.service_item_id).first()
    if not service_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")

    booking = Booking(
        customer_id=current_user.id,
        service_item_id=booking_data.service_item_id,
        booking_type=booking_data.booking_type,
        scheduled_at=booking_data.scheduled_at,
        address=booking_data.address,
        latitude=booking_data.latitude,
        longitude=booking_data.longitude,
        notes=booking_data.notes,
        total_price=service_item.base_price,
        status=BookingStatus.pending,
    )
    db.add(booking)
    db.flush()

    amount = service_item.base_price
    commission_rate = Decimal("0.10")
    commission_amount = amount * commission_rate
    provider_amount = amount - commission_amount

    payment = Payment(
        booking_id=booking.id,
        customer_id=current_user.id,
        provider_id=service_item.provider_id,
        amount=amount,
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        provider_amount=provider_amount,
        status=PaymentStatus.held,
        payment_method=booking_data.payment_method,
        mfs_transaction_id=booking_data.mfs_transaction_id,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    db.commit()
    db.refresh(booking)
    return _enrich_booking(booking, db)

@router.get("/my", response_model=List[BookingResponseSchema])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer views their own bookings."""
    bookings = db.query(Booking).filter(Booking.customer_id == current_user.id).all()
    return [_enrich_booking(b, db) for b in bookings]

@router.get("/assigned", response_model=List[BookingResponseSchema])
def get_assigned_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider views bookings for service items they created."""
    provider_item_ids = db.query(ServiceItem.id).filter(
        ServiceItem.provider_id == current_user.id
    ).subquery()
    bookings = db.query(Booking).filter(
        or_(
            Booking.provider_id == current_user.id,
            Booking.service_item_id.in_(provider_item_ids)
        )
    ).all()
    return [_enrich_booking(b, db) for b in bookings]

@router.patch("/{booking_id}/accept", response_model=BookingResponseSchema)
def accept_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider accepts a pending booking."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    if booking.status != BookingStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot accept booking in {booking.status} status")
    
    booking.provider_id = current_user.id
    booking.status = BookingStatus.accepted
    db.commit()
    db.refresh(booking)
    return _enrich_booking(booking, db)

@router.patch("/{booking_id}/start", response_model=BookingResponseSchema)
def start_work(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider marks work as started."""
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.provider_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or not assigned to you")
    
    if booking.status != BookingStatus.accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work can only start after booking is accepted")
        
    booking.status = BookingStatus.started
    db.commit()
    db.refresh(booking)
    return _enrich_booking(booking, db)

@router.patch("/{booking_id}/complete", response_model=BookingResponseSchema)
def complete_work(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider marks work as finished — customer must confirm or complain."""
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.provider_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or not assigned to you")
    
    if booking.status != BookingStatus.started:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work can only be completed after it has started")
        
    booking.status = BookingStatus.pending_completion
    db.commit()
    db.refresh(booking)
    return _enrich_booking(booking, db)

@router.patch("/{booking_id}/confirm", response_model=BookingResponseSchema)
def confirm_completion(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer confirms work was finished properly."""
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or not assigned to you")
    
    if booking.status != BookingStatus.pending_completion:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot confirm booking in {booking.status} status")
        
    booking.status = BookingStatus.completed
    release_payment(db, booking.id)
    db.commit()
    db.refresh(booking)
    return _enrich_booking(booking, db)

@router.patch("/{booking_id}/cancel", response_model=BookingResponseSchema)
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Customer or provider cancels booking (only if pending or accepted)."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    # Check permissions
    if current_user.id != booking.customer_id and current_user.id != booking.provider_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this booking")
        
    if booking.status not in [BookingStatus.pending, BookingStatus.accepted]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel booking at this stage")
        
    booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(booking)
    return _enrich_booking(booking, db)
