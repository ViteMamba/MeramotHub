from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models.user import User, UserRole
from app.models.booking import Booking, BookingStatus, BookingType
from app.models.service import ServiceItem
from app.models.service_provider import ServiceProviderProfile, VerificationStatus
from app.models.subscription import Subscription
from app.schemas.subscription import (
    SubscriptionCreateSchema,
    SubscriptionResponseSchema,
    SubscriptionCheckSchema,
    InstantBookingCreateSchema,
)
from app.schemas.booking import BookingResponseSchema
from app.utils.roles import require_role
from app.services.geo import haversine_distance

router = APIRouter(prefix="/priyo", tags=["Priyo / Subscription"])


# ──────────────────────────────────────────────
# Priyo subscription management
# ──────────────────────────────────────────────

def require_pro(db: Session, user_id) -> Subscription:
    """Check that the user has an active Priyo subscription."""
    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True
    ).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active Priyo subscription required for this feature"
        )
    if sub.expires_at and sub.expires_at < datetime.now(timezone.utc):
        sub.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your Priyo subscription has expired. Please renew."
        )
    return sub


@router.post("/subscribe", response_model=SubscriptionResponseSchema, status_code=status.HTTP_201_CREATED)
def subscribe_priyo(
    sub_data: SubscriptionCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer, UserRole.service_provider]))
):
    """Subscribe to Priyo Pro. Requires mfs_transaction_id for payment."""
    existing = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()

    if existing and existing.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active subscription"
        )

    if not sub_data.mfs_transaction_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFS transaction ID is required for payment"
        )

    if existing and not existing.is_active:
        existing.is_active = True
        existing.plan_name = sub_data.plan_name
        existing.mfs_transaction_id = sub_data.mfs_transaction_id
        existing.started_at = datetime.now(timezone.utc)
        existing.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        db.commit()
        db.refresh(existing)
        return existing

    new_sub = Subscription(
        user_id=current_user.id,
        plan_name=sub_data.plan_name,
        mfs_transaction_id=sub_data.mfs_transaction_id,
        is_active=True,
        started_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return new_sub


@router.get("/subscription", response_model=SubscriptionResponseSchema)
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer, UserRole.service_provider]))
):
    """Check your current subscription status."""
    sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found")
    return sub


@router.get("/check-subscription", response_model=SubscriptionCheckSchema)
def check_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer, UserRole.service_provider]))
):
    """Quick check if user has an active subscription."""
    sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).first()
    if not sub or (sub.expires_at and sub.expires_at < datetime.now(timezone.utc)):
        if sub:
            sub.is_active = False
            db.commit()
        return SubscriptionCheckSchema(is_active=False)
    return SubscriptionCheckSchema(
        is_active=True,
        plan_name=sub.plan_name,
        expires_at=sub.expires_at,
    )


@router.delete("/unsubscribe")
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer, UserRole.service_provider]))
):
    """Cancel your Priyo subscription."""
    sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found")

    sub.is_active = False
    db.commit()
    return {"message": "Subscription cancelled successfully"}


# ──────────────────────────────────────────────
# Instant booking with auto-assignment
# ──────────────────────────────────────────────

@router.post("/instant-book", response_model=BookingResponseSchema, status_code=status.HTTP_201_CREATED)
def create_instant_booking(
    booking_data: InstantBookingCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """
    Customer creates an instant booking.
    The system auto-assigns the nearest available Priyo-subscribed provider.
    Customer must have an active Priyo subscription to use this feature.
    """
    require_pro(db, current_user.id)

    service_item = db.query(ServiceItem).filter(ServiceItem.id == booking_data.service_item_id).first()
    if not service_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")

    assigned_provider = None
    best_distance = float("inf")

    providers = db.query(ServiceProviderProfile).filter(
        ServiceProviderProfile.verification_status == VerificationStatus.verified,
        ServiceProviderProfile.is_available == True,
        ServiceProviderProfile.current_latitude.isnot(None),
        ServiceProviderProfile.current_longitude.isnot(None),
    ).all()

    for provider in providers:
        sub = db.query(Subscription).filter(
            Subscription.user_id == provider.user_id,
            Subscription.is_active == True
        ).first()
        if not sub:
            continue
        if sub.expires_at and sub.expires_at < datetime.now(timezone.utc):
            continue
        if booking_data.latitude and booking_data.longitude:
            distance = haversine_distance(
                float(booking_data.latitude), float(booking_data.longitude),
                float(provider.current_latitude), float(provider.current_longitude)
            )
            if distance < best_distance:
                best_distance = distance
                assigned_provider = provider
        else:
            assigned_provider = provider
            break

    if not assigned_provider:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No Priyo providers are currently available. Try a standard booking instead."
        )

    new_booking = Booking(
        customer_id=current_user.id,
        provider_id=assigned_provider.user_id,
        service_item_id=booking_data.service_item_id,
        booking_type=BookingType.instant,
        address=booking_data.address,
        latitude=booking_data.latitude,
        longitude=booking_data.longitude,
        notes=booking_data.notes,
        total_price=service_item.base_price,
        status=BookingStatus.accepted,
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking
