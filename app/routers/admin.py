from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String
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
    bookings_by_status_raw = db.query(
        cast(Booking.status, String), func.count(Booking.id)
    ).group_by(cast(Booking.status, String)).all()
    bookings_by_status = {str(k): v for k, v in bookings_by_status_raw}

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
        "total_users": total_users,
        "total_providers": total_providers,
        "total_customers": users_by_role.get(UserRole.customer, 0),
        "total_area_managers": users_by_role.get(UserRole.area_manager, 0),
        "total_bookings": total_bookings,
        "completed_bookings": bookings_by_status.get('completed', 0),
        "total_revenue": float(total_revenue),
        "open_complaints": open_complaints,
        "pending_verifications": pending_providers,
        "verified_providers": verified_providers,
        "active_providers": verified_providers,
        "completion_rate": round((bookings_by_status.get('completed', 0) / total_bookings * 100), 1) if total_bookings > 0 else 0,
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
            "role": u.role.value,
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

    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate another admin"
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
    """Area Manager: Stats for complaints, verifications, and approvals in their area."""
    total_complaints = db.query(func.count(Complaint.id)).scalar() or 0

    resolved_complaints = db.query(func.count(Complaint.id)).filter(
        Complaint.status == ComplaintStatus.resolved
    ).scalar() or 0

    pending_verifications = db.query(func.count(ServiceProviderProfile.id)).filter(
        ServiceProviderProfile.verification_status == VerificationStatus.pending
    ).scalar() or 0

    verified_by_me = db.query(func.count(ServiceProviderProfile.id)).filter(
        ServiceProviderProfile.verified_by == current_user.id
    ).scalar() or 0

    return {
        "pending_verifications": pending_verifications,
        "assigned_complaints": total_complaints,
        "resolved_complaints": resolved_complaints,
        "verified_providers": verified_by_me,
    }


# ──────────────────────────────────────────────
# Provider Approval (Admin only)
# ──────────────────────────────────────────────

@router.get("/providers/verified")
def get_verified_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin: List providers who are verified by area manager but not yet approved by admin."""
    profiles = (
        db.query(ServiceProviderProfile)
        .join(User, ServiceProviderProfile.user_id == User.id)
        .filter(
            ServiceProviderProfile.verification_status == VerificationStatus.verified,
            User.is_approved == False,
        )
        .all()
    )

    result = []
    for p in profiles:
        result.append({
            "id": p.id,
            "user_id": str(p.user_id),
            "full_name": p.user.full_name,
            "nid_number": p.user.nid_number,
            "nid_image_url": p.nid_image_url,
            "skill_category": p.skill_category,
            "experience_years": p.experience_years,
            "bio": p.bio,
            "area": p.user.area,
            "verification_status": p.verification_status.value,
            "created_at": str(p.created_at),
        })

    return result


@router.patch("/providers/{provider_id}/approve")
def approve_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin: Approve a verified service provider, granting full platform access."""
    profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.id == provider_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider profile not found")

    user = db.query(User).filter(User.id == profile.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if profile.verification_status != VerificationStatus.verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider must be verified by an area manager before admin approval"
        )

    if user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is already approved"
        )

    user.is_approved = True
    db.commit()

    return {"message": f"Provider {user.full_name} has been approved and granted full access"}
