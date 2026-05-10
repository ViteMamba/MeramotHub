"""
Pagination utility for list endpoints.
Usage in routers:
    from app.utils.pagination import PaginationParams, paginate

    @router.get("/items")
    def list_items(
        pagination: PaginationParams = Depends(),
        db: Session = Depends(get_db)
    ):
        query = db.query(Item)
        return paginate(query, pagination)
"""
from fastapi import Query
from sqlalchemy.orm import Query as SAQuery
from typing import TypeVar, Generic, List, Any
from pydantic import BaseModel


class PaginationParams:
    """FastAPI dependency for extracting pagination query parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


class PaginatedResponse(BaseModel):
    """Standardized paginated response wrapper."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = {"from_attributes": True}


def paginate(query: SAQuery, params: PaginationParams) -> dict:
    """
    Apply pagination to a SQLAlchemy query and return a structured response.
    """
    total = query.count()
    items = query.offset(params.offset).limit(params.page_size).all()
    total_pages = (total + params.page_size - 1) // params.page_size  # Ceiling division

    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "total_pages": total_pages,
    }
