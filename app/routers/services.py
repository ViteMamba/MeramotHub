from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.models.service import ServiceCategory, ServiceItem
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
        
    new_item = ServiceItem(**item_data.model_dump())
    if current_user.role == UserRole.service_provider:
        new_item.provider_id = current_user.id
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.get("/items", response_model=List[ServiceItemResponseSchema])
def list_service_items(
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """List all service items (Public)."""
    query = db.query(ServiceItem).filter(ServiceItem.is_active == True)
    if category_id:
        query = query.filter(ServiceItem.category_id == category_id)
    return query.all()

@router.get("/items/{item_id}", response_model=ServiceItemResponseSchema)
def get_service_item(item_id: int, db: Session = Depends(get_db)):
    """Get single service item detail."""
    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")
    return item

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
    return item
