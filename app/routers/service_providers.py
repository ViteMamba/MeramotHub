from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User, UserRole
from app.models.service_provider import ServiceProviderProfile, SkillCategory, VerificationStatus
from app.schemas.service_provider import (
    ProfileCreateSchema,
    ProfileUpdateSchema,
    ProfileResponseSchema,
    VerificationActionSchema,
)
from app.utils.auth import get_current_user
from app.utils.roles import require_role

router = APIRouter(prefix="/providers", tags=["Service Providers"])

@router.post("/profile", response_model=ProfileResponseSchema, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: ProfileCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Service provider submits their profile for verification."""
    # Check if profile already exists
    existing_profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == current_user.id).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists for this user"
        )
    
    # Check if NID already exists
    existing_nid = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.nid_number == profile_data.nid_number).first()
    if existing_nid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A profile with this NID number already exists"
        )

    new_profile = ServiceProviderProfile(
        user_id=current_user.id,
        **profile_data.model_dump(),
        verification_status=VerificationStatus.pending
    )
    
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile

@router.get("/profile/me", response_model=ProfileResponseSchema)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """View own profile."""
    profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile

@router.get("/pending", response_model=List[ProfileResponseSchema])
def list_pending_verifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.area_manager, UserRole.admin]))
):
    """List all pending verification requests (Area Manager / Admin only)."""
    return db.query(ServiceProviderProfile).filter(ServiceProviderProfile.verification_status == VerificationStatus.pending).all()

@router.patch("/{provider_id}/verify", response_model=ProfileResponseSchema)
def verify_provider(
    provider_id: int,
    action_data: VerificationActionSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.area_manager, UserRole.admin]))
):
    """Verify or reject a service provider profile."""
    profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.id == provider_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    profile.verification_status = action_data.action
    profile.verified_by = current_user.id
    profile.verified_at = datetime.now(timezone.utc)
    
    # If rejected, we might want to store the note in a separate table or a new field.
    # For now, let's just commit the status change.
    
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/", response_model=List[ProfileResponseSchema])
def list_verified_providers(
    skill: Optional[SkillCategory] = Query(None),
    area: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all verified service providers with optional filters."""
    query = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.verification_status == VerificationStatus.verified)
    
    if skill:
        query = query.filter(ServiceProviderProfile.skill_category == skill)
    if area:
        query = query.filter(ServiceProviderProfile.area.ilike(f"%{area}%"))
        
    return query.all()
