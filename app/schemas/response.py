"""
Standardized API response wrappers.
Use these to wrap endpoint responses for consistency across the API.
"""
from pydantic import BaseModel
from typing import Any, Optional


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: str = "OK"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    detail: str
    error_type: Optional[str] = None


def success(data: Any = None, message: str = "OK") -> dict:
    """Helper to create a success response dict."""
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error(detail: str, error_type: str = None) -> dict:
    """Helper to create an error response dict."""
    return {
        "success": False,
        "detail": detail,
        "error_type": error_type,
    }
