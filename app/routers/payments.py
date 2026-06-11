from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import (
    PaymentInitSchema,
    PaymentResponseSchema,
    ProviderEarningsSummarySchema,
)
from app.utils.roles import require_role
from app.services.payment_service import refund_payment

router = APIRouter(prefix="/payments", tags=["Escrow Payments"])

@router.post("/pay", response_model=PaymentResponseSchema, status_code=status.HTTP_201_CREATED)
def initiate_payment(
    payment_data: PaymentInitSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer pays for an accepted booking. Funds are held in escrow."""
    booking = db.query(Booking).filter(Booking.id == payment_data.booking_id, Booking.customer_id == current_user.id).first()
    
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    if booking.status != BookingStatus.accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only pay for accepted bookings")
    
    # Check if already paid
    existing_payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
    if existing_payment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking already paid")

    # Calculation
    amount = booking.total_price
    commission_rate = Decimal("0.10")
    commission_amount = amount * commission_rate
    provider_amount = amount - commission_amount

    new_payment = Payment(
        booking_id=booking.id,
        customer_id=current_user.id,
        provider_id=booking.provider_id,
        amount=amount,
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        provider_amount=provider_amount,
        status=PaymentStatus.held,
        mfs_transaction_id=payment_data.mfs_transaction_id,
        paid_at=datetime.now(timezone.utc)
    )
    
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    return new_payment

@router.post("/{booking_id}/refund", response_model=PaymentResponseSchema)
def trigger_refund(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin triggers a refund for a disputed or cancelled booking."""
    if refund_payment(db, booking_id):
        return db.query(Payment).filter(Payment.booking_id == booking_id).first()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment not found or not in 'held' status")

@router.get("/my", response_model=List[PaymentResponseSchema])
def get_my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer views their payment history."""
    return db.query(Payment).filter(Payment.customer_id == current_user.id).all()

@router.get("/earnings", response_model=List[PaymentResponseSchema])
def get_my_earnings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider views their released earnings."""
    return db.query(Payment).filter(Payment.provider_id == current_user.id, Payment.status == PaymentStatus.released).all()

@router.get("/provider-summary", response_model=ProviderEarningsSummarySchema)
def get_provider_earnings_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider views their earnings summary (total, pending, released, refunded)."""
    all_payments = db.query(Payment).filter(Payment.provider_id == current_user.id)
    released_payments = all_payments.filter(Payment.status == PaymentStatus.released)

    total_earned = db.query(func.sum(Payment.provider_amount)).filter(
        Payment.provider_id == current_user.id,
        Payment.status.in_([PaymentStatus.held, PaymentStatus.released])
    ).scalar() or 0

    pending_release = db.query(func.sum(Payment.provider_amount)).filter(
        Payment.provider_id == current_user.id,
        Payment.status == PaymentStatus.held
    ).scalar() or 0

    total_released = db.query(func.sum(Payment.provider_amount)).filter(
        Payment.provider_id == current_user.id,
        Payment.status == PaymentStatus.released
    ).scalar() or 0

    total_refunded = db.query(func.sum(Payment.amount)).filter(
        Payment.provider_id == current_user.id,
        Payment.status == PaymentStatus.refunded
    ).scalar() or 0

    booking_count = all_payments.count()
    released_booking_count = released_payments.count()

    return ProviderEarningsSummarySchema(
        total_earned=total_earned,
        pending_release=pending_release,
        total_released=total_released,
        total_refunded=total_refunded,
        booking_count=booking_count,
        released_booking_count=released_booking_count,
    )

@router.get("/dashboard")
def get_payment_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin summary of all financial activity."""
    total_held = db.query(func.sum(Payment.amount)).filter(Payment.status == PaymentStatus.held).scalar() or 0
    total_commission = db.query(func.sum(Payment.commission_amount)).filter(Payment.status == PaymentStatus.released).scalar() or 0
    total_paid_out = db.query(func.sum(Payment.provider_amount)).filter(Payment.status == PaymentStatus.released).scalar() or 0
    
    return {
        "escrow_held": total_held,
        "total_revenue": total_commission,
        "total_paid_out": total_paid_out
    }
