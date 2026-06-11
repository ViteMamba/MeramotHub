from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.models.booking import Booking, BookingStatus
from app.models.complaint import Complaint, ComplaintStatus, ComplaintResolution
from app.models.payment import Payment, PaymentStatus
from app.schemas.complaint import (
    ComplaintCreateSchema,
    ComplaintAssignSchema,
    ComplaintResolveSchema,
    ComplaintResponseSchema,
)
from app.utils.auth import get_current_user
from app.utils.roles import require_role
from app.services.payment_service import refund_payment, release_payment

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
    booking.status = BookingStatus.disputed
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
    """Area Manager or Admin resolves a complaint. Refund triggers admin approval flow."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    if complaint.status in [ComplaintStatus.resolved, ComplaintStatus.dismissed, ComplaintStatus.pending_approval]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint is already resolved, dismissed, or awaiting approval"
        )

    booking = db.query(Booking).filter(Booking.id == complaint.booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    complaint.resolution = resolve_data.resolution
    complaint.resolution_note = resolve_data.resolution_note
    complaint.resolved_at = datetime.now(timezone.utc)

    # Check resolution type
    if resolve_data.resolution in ["refund", "refunded", ComplaintResolution.refunded]:
        # Set status to pending_approval (Admin must approve to execute refund)
        complaint.status = ComplaintStatus.pending_approval
        # Booking status remains disputed while awaiting approval
    elif resolve_data.resolution in ["resolve", "no_action", ComplaintResolution.no_action]:
        if resolve_data.resolution == "resolve":
            complaint.status = ComplaintStatus.resolved
            booking.status = BookingStatus.completed
            # Release escrow payment to provider
            release_payment(db, complaint.booking_id)
        else:
            complaint.status = ComplaintStatus.dismissed
            booking.status = BookingStatus.pending_completion
    else:
        # Fallback default resolve
        complaint.status = ComplaintStatus.resolved
        booking.status = BookingStatus.completed
        release_payment(db, complaint.booking_id)

    db.commit()
    db.refresh(complaint)
    return complaint


@router.post("/{complaint_id}/rework")
def rework_booking(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer, UserRole.area_manager, UserRole.admin]))
):
    """Customer, AM, or Admin requests rework on a disputed booking."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    booking = db.query(Booking).filter(Booking.id == complaint.booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.status != BookingStatus.disputed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only request rework on disputed bookings"
        )

    # Reset booking back to pending and clear provider_id for reassignment
    booking.status = BookingStatus.pending
    booking.provider_id = None

    # Update payment provider_id as well so it's ready for the new provider
    payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
    if payment:
        payment.provider_id = None
        payment.status = PaymentStatus.held

    complaint.status = ComplaintStatus.resolved
    complaint.resolution = "rework"
    complaint.resolution_note = "Rework requested. Reassigned to open queue for a new provider."
    complaint.resolved_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Rework requested. Booking is back to pending and open for other providers."}


@router.patch("/{complaint_id}/approve")
def approve_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin approves a complaint resolution (e.g. executing a refund)."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    if complaint.status != ComplaintStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve complaints that are awaiting approval"
        )

    booking = db.query(Booking).filter(Booking.id == complaint.booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # Execute the financial refund if proposed resolution was refund
    if complaint.resolution in ["refund", "refunded"]:
        refund_result = refund_payment(db, complaint.booking_id)
        if not refund_result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refund execution failed")

    complaint.status = ComplaintStatus.resolved
    booking.status = BookingStatus.completed  # Release the escrow and finalize booking
    db.commit()
    return {"message": "Complaint resolution approved and executed"}


@router.patch("/{complaint_id}/reject")
def reject_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin rejects/dismisses a complaint resolution. Rejects pending approval back to assigned."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    booking = db.query(Booking).filter(Booking.id == complaint.booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # If complaint was awaiting refund approval, reject it back to the Area Manager (assigned status)
    if complaint.status == ComplaintStatus.pending_approval:
        complaint.status = ComplaintStatus.assigned
        complaint.resolution = None
        complaint.resolved_at = None
        db.commit()
        return {"message": "Resolution rejected, complaint sent back to Area Manager for review"}

    if complaint.status in [ComplaintStatus.dismissed]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint is already dismissed"
        )

    booking.status = BookingStatus.pending_completion
    complaint.status = ComplaintStatus.dismissed
    complaint.resolved_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Complaint rejected and dismissed"}

