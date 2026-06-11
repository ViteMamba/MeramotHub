from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.auth import get_current_user
from app.services.payment_service import release_payment
from app.models.service import ServiceItem, ServiceCategory
from app.models.service_provider import ServiceProviderProfile
from app.models.booking import Booking, BookingStatus, BookingType
from app.models.payment import Payment, PaymentStatus
from app.schemas.booking import (
    BookingCreateSchema,
    BookingResponseSchema,
    BookingStatusUpdateSchema,
    PayAndBookSchema,
    PayAndBookResponseSchema,
)
from app.models.favorite_provider import FavoriteProvider
from app.models.subscription import Subscription
from app.utils.roles import require_role

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ── Helper: enrich a Booking ORM object with related names ──

def _enrich_booking(booking, db):
    """Attach provider_name, service_name etc. to a Booking ORM instance."""
    # Always initialize enriched fields to avoid missing attribute errors
    booking.provider_name = None
    booking.provider_phone = None
    booking.provider_area = None
    booking.provider_latitude = None
    booking.provider_longitude = None
    booking.service_name = None
    booking.customer_name = None

    if booking.provider_id:
        provider = db.query(User).filter(User.id == booking.provider_id).first()
        if provider:
            booking.provider_name = provider.full_name
            booking.provider_phone = provider.phone_number
            booking.provider_area = provider.area
            booking.provider_latitude = provider.latitude
            booking.provider_longitude = provider.longitude

    service_item = db.query(ServiceItem).filter(ServiceItem.id == booking.service_item_id).first()
    if service_item:
        booking.service_name = service_item.name

    customer = db.query(User).filter(User.id == booking.customer_id).first()
    if customer:
        booking.customer_name = customer.full_name

    return booking


def _enrich_bookings(bookings, db):
    """Enrich a list of bookings."""
    for b in bookings:
        _enrich_booking(b, db)
    return bookings


# ── Helper: auto-accept booking if provider is customer's Priyo ──

def _auto_accept_if_priyo(booking, customer_id, db):
    """If the provider is marked as Priyo by the customer and customer has active subscription, auto-accept."""
    if not booking.provider_id:
        return
    fav = db.query(FavoriteProvider).filter(
        FavoriteProvider.customer_id == customer_id,
        FavoriteProvider.provider_id == booking.provider_id
    ).first()
    if not fav:
        return
    sub = db.query(Subscription).filter(
        Subscription.user_id == customer_id,
        Subscription.is_active == True
    ).first()
    if not sub:
        return
    if sub.expires_at and sub.expires_at < datetime.now(timezone.utc):
        return
    booking.status = BookingStatus.accepted


# ── Create booking (standard two-step) ──

@router.post("/", response_model=BookingResponseSchema, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: BookingCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer creates a new booking."""
    service_item = db.query(ServiceItem).filter(ServiceItem.id == booking_data.service_item_id).first()
    if not service_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")
    
    new_booking = Booking(
        customer_id=current_user.id,
        **booking_data.model_dump(),
        total_price=service_item.base_price,
        status=BookingStatus.pending
    )
    
    db.add(new_booking)
    db.flush()
    _auto_accept_if_priyo(new_booking, current_user.id, db)
    db.commit()
    db.refresh(new_booking)
    return _enrich_booking(new_booking, db)


# ── Pay-and-book (combined flow) ──

@router.post("/pay-and-book", response_model=PayAndBookResponseSchema, status_code=status.HTTP_201_CREATED)
def pay_and_book(
    data: PayAndBookSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer creates a booking and pays in one step."""
    service_item = db.query(ServiceItem).filter(ServiceItem.id == data.service_item_id).first()
    if not service_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")

    new_booking = Booking(
        customer_id=current_user.id,
        provider_id=service_item.provider_id,
        service_item_id=data.service_item_id,
        booking_type=BookingType.standard,
        scheduled_at=data.scheduled_at,
        address=data.address,
        latitude=data.latitude,
        longitude=data.longitude,
        notes=data.notes,
        total_price=service_item.base_price,
        status=BookingStatus.pending,
    )
    db.add(new_booking)
    db.flush()

    amount = service_item.base_price
    commission_rate = Decimal("0.10")
    commission_amount = amount * commission_rate
    provider_amount = amount - commission_amount

    payment = Payment(
        booking_id=new_booking.id,
        customer_id=current_user.id,
        provider_id=service_item.provider_id,
        amount=amount,
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        provider_amount=provider_amount,
        status=PaymentStatus.held,
        mfs_transaction_id=data.mfs_transaction_id,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    _auto_accept_if_priyo(new_booking, current_user.id, db)
    db.commit()
    db.refresh(new_booking)
    db.refresh(payment)

    _enrich_booking(new_booking, db)

    return PayAndBookResponseSchema(
        booking=new_booking,
        payment_id=payment.id,
        payment_status=payment.status.value,
        amount_paid=payment.amount,
        mfs_transaction_id=payment.mfs_transaction_id,
    )


# ── List endpoints ──

@router.get("/my", response_model=List[BookingResponseSchema])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer views their own bookings."""
    bookings = db.query(Booking).filter(Booking.customer_id == current_user.id).order_by(Booking.created_at.desc()).all()
    return _enrich_bookings(bookings, db)


@router.get("/assigned", response_model=List[BookingResponseSchema])
def get_assigned_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider views bookings for their service items."""
    provider_item_ids = db.query(ServiceItem.id).filter(
        ServiceItem.provider_id == current_user.id
    )

    # Find general bookings matching provider's skill category
    profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == current_user.id).first()
    general_filter = []
    if profile:
        # Get category IDs matching provider's skill category
        category_ids = db.query(ServiceCategory.id).filter(
            ServiceCategory.skill_required == profile.skill_category
        )
        # Find general service items in those categories (where provider_id is null)
        general_item_ids = db.query(ServiceItem.id).filter(
            ServiceItem.category_id.in_(category_ids),
            ServiceItem.provider_id.is_(None)
        )
        general_filter = [
            and_(
                Booking.provider_id.is_(None),
                Booking.status == BookingStatus.pending,
                Booking.service_item_id.in_(general_item_ids)
            )
        ]

    bookings = db.query(Booking).filter(
        or_(
            Booking.provider_id == current_user.id,
            Booking.service_item_id.in_(provider_item_ids),
            *general_filter
        )
    ).order_by(Booking.created_at.desc()).all()
    return _enrich_bookings(bookings, db)


# ── Status transitions (Provider side) ──

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
    
    # Update payment with provider_id
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if payment:
        payment.provider_id = current_user.id

    db.commit()
    db.refresh(booking)
    return _enrich_booking(booking, db)


@router.patch("/{booking_id}/reject", response_model=BookingResponseSchema)
def reject_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider rejects a pending booking — cancels it."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    if booking.status != BookingStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot reject booking in {booking.status} status")
    
    booking.provider_id = current_user.id
    booking.status = BookingStatus.cancelled
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


# ── Status transitions (Customer side) ──

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
    
    if current_user.id != booking.customer_id and current_user.id != booking.provider_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this booking")
        
    if booking.status not in [BookingStatus.pending, BookingStatus.accepted]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel booking at this stage")
        
    booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(booking)
    return _enrich_booking(booking, db)
