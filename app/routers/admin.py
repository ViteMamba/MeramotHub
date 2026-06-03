from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.models.service_provider import ServiceProviderProfile, VerificationStatus
from app.models.complaint import Complaint, ComplaintStatus
from app.models.review import Review
from app.utils.roles import require_role

router = APIRouter(prefix="/admin", tags=["Admin & Area Manager Dashboard"])


# ──────────────────────────────────────────────
# Admin-only endpoints
# ──────────────────────────────────────────────

@router.get("/stats")
def get_platform_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin: Get overall platform statistics."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    users_by_role = dict(
        db.query(User.role, func.count(User.id)).group_by(User.role).all()
    )

    total_providers = db.query(func.count(ServiceProviderProfile.id)).scalar() or 0
    verified_providers = db.query(func.count(ServiceProviderProfile.id)).filter(
        ServiceProviderProfile.verification_status == VerificationStatus.verified
    ).scalar() or 0
    pending_providers = db.query(func.count(ServiceProviderProfile.id)).filter(
        ServiceProviderProfile.verification_status == VerificationStatus.pending
    ).scalar() or 0

    total_bookings = db.query(func.count(Booking.id)).scalar() or 0
    bookings_by_status = dict(
        db.query(Booking.status, func.count(Booking.id)).group_by(Booking.status).all()
    )

    total_revenue = db.query(func.sum(Payment.commission_amount)).filter(
        Payment.status == PaymentStatus.released
    ).scalar() or 0
    total_paid_out = db.query(func.sum(Payment.provider_amount)).filter(
        Payment.status == PaymentStatus.released
    ).scalar() or 0
    escrow_held = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.held
    ).scalar() or 0

    open_complaints = db.query(func.count(Complaint.id)).filter(
        Complaint.status.in_([ComplaintStatus.open, ComplaintStatus.assigned])
    ).scalar() or 0

    total_reviews = db.query(func.count(Review.id)).scalar() or 0
    avg_platform_rating = db.query(func.avg(Review.rating)).scalar()

    return {
        "users": {
            "total": total_users,
            "by_role": {str(k): v for k, v in users_by_role.items()},
        },
        "providers": {
            "total": total_providers,
            "verified": verified_providers,
            "pending": pending_providers,
        },
        "bookings": {
            "total": total_bookings,
            "by_status": {str(k): v for k, v in bookings_by_status.items()},
        },
        "financials": {
            "total_revenue": float(total_revenue),
            "total_paid_out": float(total_paid_out),
            "escrow_held": float(escrow_held),
        },
        "complaints": {
            "open": open_complaints,
        },
        "reviews": {
            "total": total_reviews,
            "avg_rating": round(float(avg_platform_rating), 2) if avg_platform_rating else None,
        },
    }


@router.get("/users")
def list_users(
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin: List all users with optional filters."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    users = query.order_by(User.created_at.desc()).all()

    return [
        {
            "id": str(u.id),
            "full_name": u.full_name,
            "phone_number": u.phone_number,
            "email": u.email,
            "role": str(u.role),
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "is_approved": u.is_approved,
            "created_at": str(u.created_at),
        }
        for u in users
    ]


@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin: Deactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    user.is_active = False
    db.commit()
    return {"message": f"User {user.full_name} has been deactivated"}


@router.patch("/users/{user_id}/activate")
def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin: Reactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = True
    db.commit()
    return {"message": f"User {user.full_name} has been activated"}


@router.patch("/users/{user_id}/role")
def change_user_role(
    user_id: UUID,
    new_role: UserRole = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin: Change a user's role (e.g. promote to area_manager)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )

    user.role = new_role
    db.commit()
    return {"message": f"User {user.full_name} role changed to {new_role.value}"}


# ──────────────────────────────────────────────
# Area Manager endpoints
# ──────────────────────────────────────────────

@router.get("/area-manager/stats")
def get_area_manager_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.area_manager]))
):
    """Area Manager: Stats for complaints and verifications assigned to them."""
    assigned_complaints = db.query(func.count(Complaint.id)).filter(
        Complaint.assigned_to == current_user.id
    ).scalar() or 0

    resolved_complaints = db.query(func.count(Complaint.id)).filter(
        Complaint.assigned_to == current_user.id,
        Complaint.status == ComplaintStatus.resolved
    ).scalar() or 0

    pending_complaints = db.query(func.count(Complaint.id)).filter(
        Complaint.assigned_to == current_user.id,
        Complaint.status == ComplaintStatus.assigned
    ).scalar() or 0

    verified_by_me = db.query(func.count(ServiceProviderProfile.id)).filter(
        ServiceProviderProfile.verified_by == current_user.id
    ).scalar() or 0

    return {
        "complaints": {
            "total_assigned": assigned_complaints,
            "resolved": resolved_complaints,
            "pending": pending_complaints,
        },
        "verifications": {
            "verified_by_me": verified_by_me,
        },
    }
