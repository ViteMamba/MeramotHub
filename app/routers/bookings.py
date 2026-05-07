from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User, UserRole
from uuid import UUID
from app.utils.auth import get_current_user
from app.services.payment_service import release_payment
from app.models.service import ServiceItem
from app.models.booking import Booking, BookingStatus, BookingType
from app.schemas.booking import (
    BookingCreateSchema,
    BookingResponseSchema,
    BookingStatusUpdateSchema,
)
from app.utils.roles import require_role

router = APIRouter(prefix="/bookings", tags=["Bookings"])

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
    return new_booking

@router.get("/my", response_model=List[BookingResponseSchema])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer views their own bookings."""
    return db.query(Booking).filter(Booking.customer_id == current_user.id).all()

@router.get("/assigned", response_model=List[BookingResponseSchema])
def get_assigned_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider views bookings assigned to them."""
    return db.query(Booking).filter(Booking.provider_id == current_user.id).all()

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
    return booking

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
    return booking

@router.patch("/{booking_id}/complete", response_model=BookingResponseSchema)
def complete_work(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider marks work as completed."""
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.provider_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or not assigned to you")
    
    if booking.status != BookingStatus.started:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work can only be completed after it has started")
        
    booking.status = BookingStatus.completed
    
    # Release payment from escrow
    release_payment(db, booking.id)
    
    db.commit()
    db.refresh(booking)
    return booking

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
    return booking
