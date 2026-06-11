import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.user import User, UserRole
from app.models.booking import Booking, BookingStatus, BookingType
from app.models.complaint import Complaint, ComplaintStatus, ComplaintResolution
from app.schemas.complaint import (
    ComplaintCreateSchema,
    ComplaintAssignSchema,
    ComplaintResolveSchema,
    ComplaintResponseSchema,
)
from app.utils.auth import get_current_user
from app.utils.roles import require_role
from app.services.payment_service import refund_payment, create_rework_payment

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
    """Area Manager or Admin resolves a complaint.
    - 'refund' → pending_approval (admin must approve)
    - 'rework' → direct (rework booking created)
    - 'resolve' → direct (work completed, provider paid)
    """
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

        if complaint.status in [ComplaintStatus.resolved, ComplaintStatus.dismissed, ComplaintStatus.pending_approval, ComplaintStatus.refunded, ComplaintStatus.rework]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Complaint is already resolved or dismissed"
            )

        booking = db.query(Booking).filter(Booking.id == complaint.booking_id).first()

        complaint.resolution = resolve_data.resolution
        complaint.resolution_note = resolve_data.resolution_note
        complaint.resolved_at = datetime.now(timezone.utc)

        if resolve_data.resolution == ComplaintResolution.refund:
            complaint.status = ComplaintStatus.pending_approval

        elif resolve_data.resolution == ComplaintResolution.rework:
            if not booking:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Original booking not found")

            new_booking = Booking(
                customer_id=booking.customer_id,
                provider_id=booking.provider_id,
                service_item_id=booking.service_item_id,
                booking_type=BookingType.rework,
                scheduled_at=datetime.now(timezone.utc),
                address=booking.address,
                latitude=booking.latitude,
                longitude=booking.longitude,
                notes=f"Rework of booking {booking.id} | {booking.notes}" if booking.notes else f"Rework of booking {booking.id}",
                total_price=booking.total_price,
                status=BookingStatus.accepted,
            )
            db.add(new_booking)
            db.flush()

            create_rework_payment(
                db,
                booking_id=new_booking.id,
                customer_id=booking.customer_id,
                provider_id=booking.provider_id,
                amount=booking.total_price,
            )

            complaint.status = ComplaintStatus.rework

        elif resolve_data.resolution == ComplaintResolution.resolve:
            complaint.status = ComplaintStatus.resolved
            if booking:
                booking.status = BookingStatus.completed

        else:
            complaint.status = ComplaintStatus.resolved
            if booking:
                booking.status = BookingStatus.completed

        db.commit()
        db.refresh(complaint)
        return complaint

    except Exception as e:
        logger.exception("Error resolving complaint %s: %s", complaint_id, str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{complaint_id}/rework", response_model=ComplaintResponseSchema)
def rework_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.area_manager, UserRole.admin]))
):
    """Area Manager triggers a rework — creates a new pending booking with same details,
    payment at 80/20 split (80% provider, 20% commission). No admin approval needed."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    if complaint.status in [ComplaintStatus.resolved, ComplaintStatus.dismissed, ComplaintStatus.refunded, ComplaintStatus.rework]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint is already resolved"
        )

    booking = db.query(Booking).filter(Booking.id == complaint.booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original booking not found")

    # Create new rework booking
    new_booking = Booking(
        customer_id=booking.customer_id,
        provider_id=booking.provider_id,
        service_item_id=booking.service_item_id,
        booking_type=BookingType.rework,
        scheduled_at=datetime.now(timezone.utc),
        address=booking.address,
        latitude=booking.latitude,
        longitude=booking.longitude,
        notes=f"Rework of booking {booking.id} | {booking.notes}" if booking.notes else f"Rework of booking {booking.id}",
        total_price=booking.total_price,
        status=BookingStatus.accepted,
    )
    db.add(new_booking)
    db.flush()

    # Create payment with 80/20 split
    create_rework_payment(
        db,
        booking_id=new_booking.id,
        customer_id=booking.customer_id,
        provider_id=booking.provider_id,
        amount=booking.total_price,
    )

    # Update complaint
    complaint.resolution = ComplaintResolution.rework
    complaint.resolution_note = f"Rework approved — new booking {new_booking.id} created"
    complaint.resolved_at = datetime.now(timezone.utc)
    complaint.status = ComplaintStatus.rework

    db.commit()
    db.refresh(complaint)
    return complaint


@router.patch("/{complaint_id}/approve", response_model=ComplaintResponseSchema)
def approve_resolution(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin approves a pending resolution, executing the action.
    For refund: 90% to customer, 10% commission held by system, provider gets 0."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    if complaint.status != ComplaintStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint is not pending approval"
        )

    booking = db.query(Booking).filter(Booking.id == complaint.booking_id).first()

    if complaint.resolution == ComplaintResolution.refund:
        # 90% refund to customer, system keeps 10% commission, provider gets 0
        if not refund_payment(db, complaint.booking_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refund failed")

    complaint.status = ComplaintStatus.refunded
    if booking:
        booking.status = BookingStatus.completed
    db.commit()
    db.refresh(complaint)
    return complaint


@router.patch("/{complaint_id}/reject", response_model=ComplaintResponseSchema)
def reject_resolution(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Admin rejects a pending resolution, sending it back for review."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    if complaint.status != ComplaintStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint is not pending approval"
        )

    complaint.status = ComplaintStatus.in_review
    db.commit()
    db.refresh(complaint)
    return complaint
