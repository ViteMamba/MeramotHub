from sqlalchemy.orm import Session
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from app.models.payment import Payment, PaymentStatus
from app.models.booking import Booking, BookingStatus


def release_payment(db: Session, booking_id: UUID):
    """Release held escrow payment to provider.
    Note: Does NOT commit — caller must handle db.commit().
    """
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if payment and payment.status == PaymentStatus.held:
        payment.status = PaymentStatus.released
        payment.released_at = datetime.now(timezone.utc)
        return True
    return False


def refund_payment(db: Session, booking_id: UUID):
    """Refund 90% to customer, system keeps 10% commission, provider gets 0.
    Note: Does NOT commit — caller must handle db.commit().
    """
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if payment and payment.status == PaymentStatus.held:
        # 90% refund to customer = provider_amount (which is amount - 10% commission)
        # System keeps the commission_amount (10%)
        payment.status = PaymentStatus.refunded
        return True
    return False


def create_rework_payment(db: Session, booking_id: UUID, customer_id: UUID, provider_id: UUID, amount: Decimal):
    """Create a payment record for a rework booking with 80/20 split (80% provider, 20% commission).
    Note: Does NOT commit — caller must handle db.commit().
    """
    commission_rate = Decimal("0.20")
    commission_amount = (amount * commission_rate).quantize(Decimal("0.01"))
    provider_amount = (amount - commission_amount).quantize(Decimal("0.01"))

    payment = Payment(
        booking_id=booking_id,
        customer_id=customer_id,
        provider_id=provider_id,
        amount=amount,
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        provider_amount=provider_amount,
        status=PaymentStatus.held,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    return payment
