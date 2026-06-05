from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User, UserRole
from app.models.service import ServiceCategory, ServiceItem
from app.models.service_provider import ServiceProviderProfile
from app.services.geo import road_distance_km

from app.schemas.service import (
    CategoryCreateSchema,
    CategoryResponseSchema,
    ServiceItemCreateSchema,
    ServiceItemResponseSchema,
    ServiceItemUpdateSchema,
)
from app.utils.roles import require_role

router = APIRouter(prefix="/services", tags=["Service Catalogue"])

@router.post("/categories", response_model=CategoryResponseSchema, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Create a new service category (Admin only)."""
    existing = db.query(ServiceCategory).filter(ServiceCategory.name == category_data.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists")
    
    new_category = ServiceCategory(**category_data.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@router.get("/categories", response_model=List[CategoryResponseSchema])
def list_categories(db: Session = Depends(get_db)):
    """List all service categories (Public)."""
    return db.query(ServiceCategory).all()

@router.post("/items", response_model=ServiceItemResponseSchema, status_code=status.HTTP_201_CREATED)
def create_service_item(
    item_data: ServiceItemCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin, UserRole.service_provider]))
):
    """Create a new service item with fixed pricing (Admin/Provider)."""
    # Verify category exists
    category = db.query(ServiceCategory).filter(ServiceCategory.id == item_data.category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if current_user.role == UserRole.service_provider:
        missing = []
        if not current_user.nid_number:
            missing.append("NID number")
        if not current_user.area:
            missing.append("address")
        profile = db.query(ServiceProviderProfile).filter(
            ServiceProviderProfile.user_id == current_user.id
        ).first()
        if not profile or not profile.nid_image_url:
            missing.append("NID image upload")
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Complete your profile first: {', '.join(missing)}. "
                       f"Go to your Profile page to fill in the missing information."
            )

    new_item = ServiceItem(**item_data.model_dump())
    if current_user.role == UserRole.service_provider:
        new_item.provider_id = current_user.id
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    new_item.category = db.query(ServiceCategory).filter(ServiceCategory.id == new_item.category_id).first()
    return _enrich_item(new_item, db)

def _enrich_item(item, db=None):
    """Attach category_name and provider_area to a ServiceItem object."""
    if item.category:
        item.category_name = item.category.name
    if item.created_at:
        item.created_at = item.created_at.isoformat()
    if db and item.provider_id:
        provider = db.query(User).filter(User.id == item.provider_id).first()
        if provider:
            if provider.area:
                item.provider_area = provider.area
            if provider.latitude is not None:
                item.provider_latitude = provider.latitude
            if provider.longitude is not None:
                item.provider_longitude = provider.longitude
    return item

@router.get("/items/my", response_model=List[ServiceItemResponseSchema])
def list_my_service_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """List service items created by the current provider."""
    items = db.query(ServiceItem).filter(
        ServiceItem.provider_id == current_user.id
    ).order_by(ServiceItem.created_at.desc()).all()
    return [_enrich_item(item, db) for item in items]

@router.get("/items", response_model=List[ServiceItemResponseSchema])
def list_service_items(
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """List all service items (Public)."""
    query = db.query(ServiceItem).filter(ServiceItem.is_active == True)
    if category_id:
        query = query.filter(ServiceItem.category_id == category_id)
    return [_enrich_item(item, db) for item in query.all()]

@router.patch("/items/{item_id}/status", response_model=ServiceItemResponseSchema)
def toggle_service_item_status(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Toggle active status of own service item (Provider only)."""
    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")
    if str(item.provider_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only toggle your own items")
    item.is_active = not item.is_active
    db.commit()
    db.refresh(item)
    item.category = db.query(ServiceCategory).filter(ServiceCategory.id == item.category_id).first()
    return _enrich_item(item, db)

@router.get("/items/{item_id}", response_model=ServiceItemResponseSchema)
def get_service_item(item_id: int, db: Session = Depends(get_db)):
    """Get single service item detail."""
    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")
    return _enrich_item(item, db)

@router.patch("/items/{item_id}/edit", response_model=ServiceItemResponseSchema)
def edit_my_service_item(
    item_id: int,
    item_data: ServiceItemUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.service_provider]))
):
    """Edit own service item (Provider only)."""
    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")
    if str(item.provider_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own items")
    for key, value in item_data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    item.category = db.query(ServiceCategory).filter(ServiceCategory.id == item.category_id).first()
    return _enrich_item(item, db)

@router.patch("/items/{item_id}", response_model=ServiceItemResponseSchema)
def update_service_item(
    item_id: int,
    item_data: ServiceItemUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin]))
):
    """Update service item (Admin only)."""
    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")
    
    for key, value in item_data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
        
    db.commit()
    db.refresh(item)
    return _enrich_item(item, db)

class DistanceResponse(BaseModel):
    km: float
    method: str

@router.get("/distance", response_model=DistanceResponse)
async def get_road_distance(
    lat1: float = Query(...),
    lng1: float = Query(...),
    lat2: float = Query(...),
    lng2: float = Query(...),
):
    """Calculate distance between two points. Uses OSRM for road distance, falls back to straight-line."""
    result = await road_distance_km(lat1, lng1, lat2, lng2)
    return result
