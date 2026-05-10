from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.models.booking import Booking
from app.models.complaint import Complaint, ComplaintStatus, ComplaintResolution
from app.schemas.complaint import (
    ComplaintCreateSchema,
    ComplaintAssignSchema,
    ComplaintResolveSchema,
    ComplaintResponseSchema,
)
from app.utils.auth import get_current_user
from app.utils.roles import require_role
from app.services.payment_service import refund_payment

router = APIRouter(prefix="/complaints", tags=["Complaint System"])


@router.post("/", response_model=ComplaintResponseSchema, status_code=status.HTTP_201_CREATED)
def file_complaint(
    complaint_data: ComplaintCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Customer or provider files a complaint about a booking."""
    booking = db.query(Booking).filter(Booking.id == complaint_data.booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # Verify the user is involved in the booking
    if current_user.id != booking.customer_id and current_user.id != booking.provider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not part of this booking"
        )

    new_complaint = Complaint(
        booking_id=complaint_data.booking_id,
        filed_by=current_user.id,
        subject=complaint_data.subject,
        description=complaint_data.description,
        status=ComplaintStatus.open,
    )
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    return new_complaint


@router.get("/", response_model=List[ComplaintResponseSchema])
def list_complaints(
    complaint_status: ComplaintStatus = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.area_manager, UserRole.admin]))
):
    """List all complaints (Area Manager / Admin). Optionally filter by status."""
    query = db.query(Complaint)
    if complaint_status:
        query = query.filter(Complaint.status == complaint_status)
    return query.order_by(Complaint.created_at.desc()).all()


@router.get("/my", response_model=List[ComplaintResponseSchema])
def get_my_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User views complaints they have filed."""
    return db.query(Complaint).filter(
        Complaint.filed_by == current_user.id
    ).order_by(Complaint.created_at.desc()).all()


@router.patch("/{complaint_id}/assign", response_model=ComplaintResponseSchema)
def assign_complaint(
    complaint_id: int,
    assign_data: ComplaintAssignSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin assigns a complaint to an area manager for investigation."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    if complaint.status not in [ComplaintStatus.open]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign complaint in '{complaint.status}' status"
        )

    # Verify the assignee is an area_manager
    assignee = db.query(User).filter(User.id == assign_data.assigned_to).first()
    if not assignee or assignee.role != UserRole.area_manager:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be an area manager"
        )

    complaint.assigned_to = assign_data.assigned_to
    complaint.status = ComplaintStatus.assigned
    db.commit()
    db.refresh(complaint)
    return complaint


@router.patch("/{complaint_id}/resolve", response_model=ComplaintResponseSchema)
def resolve_complaint(
    complaint_id: int,
    resolve_data: ComplaintResolveSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.area_manager, UserRole.admin]))
):
    """Area Manager or Admin resolves a complaint. Optionally triggers a refund."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    if complaint.status in [ComplaintStatus.resolved, ComplaintStatus.dismissed]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint is already resolved or dismissed"
        )

    complaint.resolution = resolve_data.resolution
    complaint.resolution_note = resolve_data.resolution_note
    complaint.resolved_at = datetime.now(timezone.utc)

    if resolve_data.resolution == ComplaintResolution.refunded:
        # Trigger refund through payment service
        refund_result = refund_payment(db, complaint.booking_id)
        if not refund_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not process refund — payment not found or not in 'held' status"
            )
        complaint.status = ComplaintStatus.resolved
    elif resolve_data.resolution == ComplaintResolution.no_action:
        complaint.status = ComplaintStatus.dismissed
    else:
        complaint.status = ComplaintStatus.resolved

    db.commit()
    db.refresh(complaint)
    return complaint
