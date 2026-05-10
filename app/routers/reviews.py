from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.models.booking import Booking, BookingStatus
from app.models.review import Review
from app.models.service_provider import ServiceProviderProfile
from app.schemas.review import ReviewCreateSchema, ReviewResponseSchema
from app.utils.roles import require_role

router = APIRouter(prefix="/reviews", tags=["Ratings & Reviews"])


@router.post("/", response_model=ReviewResponseSchema, status_code=status.HTTP_201_CREATED)
def create_review(
    review_data: ReviewCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer submits a review for a completed booking."""
    # Verify booking exists and belongs to the customer
    booking = db.query(Booking).filter(
        Booking.id == review_data.booking_id,
        Booking.customer_id == current_user.id
    ).first()

    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.status != BookingStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review completed bookings"
        )

    if not booking.provider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking has no assigned provider"
        )

    # Check if already reviewed
    existing = db.query(Review).filter(Review.booking_id == booking.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This booking has already been reviewed"
        )

    new_review = Review(
        booking_id=booking.id,
        customer_id=current_user.id,
        provider_id=booking.provider_id,
        rating=review_data.rating,
        comment=review_data.comment,
    )
    db.add(new_review)

    # Recompute provider rating_avg and rating_count
    provider_profile = db.query(ServiceProviderProfile).filter(
        ServiceProviderProfile.user_id == booking.provider_id
    ).first()

    if provider_profile:
        # Calculate new average using all reviews for this provider
        result = db.query(
            func.count(Review.id),
            func.avg(Review.rating)
        ).filter(Review.provider_id == booking.provider_id).first()

        # Include the current new review (not yet flushed)
        existing_count = result[0] or 0
        existing_avg = float(result[1]) if result[1] else 0.0

        new_count = existing_count + 1
        new_avg = ((existing_avg * existing_count) + review_data.rating) / new_count

        provider_profile.rating_count = new_count
        provider_profile.rating_avg = round(new_avg, 2)

    db.commit()
    db.refresh(new_review)
    return new_review


@router.get("/provider/{provider_user_id}", response_model=List[ReviewResponseSchema])
def get_provider_reviews(
    provider_user_id: UUID,
    db: Session = Depends(get_db)
):
    """List all reviews for a specific provider (Public)."""
    reviews = db.query(Review).filter(
        Review.provider_id == provider_user_id
    ).order_by(Review.created_at.desc()).all()
    return reviews


@router.get("/my", response_model=List[ReviewResponseSchema])
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.customer]))
):
    """Customer views reviews they have submitted."""
    return db.query(Review).filter(
        Review.customer_id == current_user.id
    ).order_by(Review.created_at.desc()).all()
