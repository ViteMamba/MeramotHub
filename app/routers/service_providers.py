import os
import uuid
import traceback
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User, UserRole
from app.models.service_provider import ServiceProviderProfile, VerificationStatus
from app.schemas.service_provider import (
    ProfileCreateSchema,
    ProfileUpdateSchema,
    ProfileResponseSchema,
    LocationUpdateSchema,
    VerificationActionSchema,
)
from app.utils.auth import get_current_user
from app.utils.roles import require_role
from app.services.geo import haversine_distance

router = APIRouter(prefix="/providers", tags=["Service Providers"])

@router.post("/profile", response_model=ProfileResponseSchema, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: ProfileCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Service provider submits their profile for verification."""
    try:
        # Check if profile already exists
        existing_profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == current_user.id).first()
        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile already exists for this user"
            )
        
        # Check if NID already exists on User model
        existing_nid = db.query(User).filter(User.nid_number == profile_data.nid_number).first()
        if existing_nid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A profile with this NID number already exists"
            )

        # Save nid_number and area to User model
        current_user.nid_number = profile_data.nid_number
        if profile_data.area:
            current_user.area = profile_data.area

        new_profile = ServiceProviderProfile(
            user_id=current_user.id,
            nid_image_url=profile_data.nid_image_url,
            skill_category=profile_data.skill_category,
            experience_years=profile_data.experience_years,
            bio=profile_data.bio,
            verification_status=VerificationStatus.pending
        )
        
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return new_profile
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/profile", response_model=ProfileResponseSchema)
def update_profile(
    profile_data: ProfileUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Update provider profile fields (work type, bio, area, etc.)."""
    profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found. Create a profile first.")

    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile

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

@router.patch("/profile/location", response_model=ProfileResponseSchema)
def update_location(
    location_data: LocationUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider updates their current GPS location (stored on User) and availability status."""
    profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found. Create a profile first.")
    
    current_user.latitude = location_data.latitude
    current_user.longitude = location_data.longitude
    profile.is_available = location_data.is_available
    profile.last_seen_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(profile)
    return profile

@router.post("/profile/upload-nid")
async def upload_nid_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider])),
):
    """Upload NID image — returns URL + original filename (saved on form submit)."""
    original = file.filename or "nid_image.jpg"
    ext = os.path.splitext(original)[1] or ".jpg"
    filename = f"nid_{uuid.uuid4()}{ext}"
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "nid")
    os.makedirs(base_dir, exist_ok=True)
    filepath = os.path.join(base_dir, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    return {"url": f"/uploads/nid/{filename}", "original_name": original}

@router.get("/nearby", response_model=List[ProfileResponseSchema])
def search_nearby_providers(
    lat: float = Query(..., description="Customer latitude"),
    lng: float = Query(..., description="Customer longitude"),
    radius_km: float = Query(10.0, description="Search radius in kilometers"),
    skill: Optional[str] = Query(None, description="Filter by skill category"),
    db: Session = Depends(get_db)
):
    """Search for nearby available and verified providers within a given radius."""
    query = db.query(ServiceProviderProfile).join(User).filter(
        ServiceProviderProfile.verification_status == VerificationStatus.verified,
        ServiceProviderProfile.is_available == True,
        User.latitude.isnot(None),
        User.longitude.isnot(None),
    )
    
    if skill:
        query = query.filter(ServiceProviderProfile.skill_category == skill)
    
    all_available = query.all()
    
    # Filter by haversine distance in Python
    nearby = []
    for profile in all_available:
        distance = haversine_distance(
            lat, lng,
            float(profile.user.latitude), float(profile.user.longitude)
        )
        if distance <= radius_km:
            nearby.append(profile)
    
    # Sort by rating (best first)
    nearby.sort(key=lambda p: float(p.rating_avg or 0), reverse=True)
    return nearby

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
    
    # Update the user's is_verified flag
    user = db.query(User).filter(User.id == profile.user_id).first()
    if user:
        user.is_verified = (action_data.action == VerificationStatus.verified)
    
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/", response_model=List[ProfileResponseSchema])
def list_verified_providers(
    skill: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all verified service providers with optional filters."""
    query = db.query(ServiceProviderProfile).join(User).filter(ServiceProviderProfile.verification_status == VerificationStatus.verified)
    
    if skill:
        query = query.filter(ServiceProviderProfile.skill_category == skill)
    if area:
        query = query.filter(User.area.ilike(f"%{area}%"))
        
    return query.all()

@router.post("/profile/submit-verification", response_model=ProfileResponseSchema)
def submit_verification(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Provider submits or re-submits their profile for verification."""
    profile = db.query(ServiceProviderProfile).filter(ServiceProviderProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found. Create a profile first.")

    profile.verification_status = VerificationStatus.pending
    db.commit()
    db.refresh(profile)
    return profile

