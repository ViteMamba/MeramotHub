from sqlalchemy.orm import Session
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from app.models.payment import Payment, PaymentStatus
from app.models.booking import Booking, BookingStatus

def release_payment(db: Session, booking_id: UUID):
    """Business logic to release held escrow payment to provider.
    Note: Does NOT commit — caller must handle db.commit().
    """
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if payment and payment.status == PaymentStatus.held:
        payment.status = PaymentStatus.released
        payment.released_at = datetime.now(timezone.utc)
        return True
    return False

def refund_payment(db: Session, booking_id: UUID):
    """Business logic to refund held escrow payment to customer.
    Note: Does NOT commit — caller must handle db.commit().
    """
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if payment and payment.status == PaymentStatus.held:
        payment.status = PaymentStatus.refunded
        return True
    return False
