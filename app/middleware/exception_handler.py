"""
Global exception handler middleware.
Catches unhandled exceptions and returns a standardized JSON error response.
"""
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Log the full traceback to server console
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "detail": "An internal server error occurred. Please try again later.",
                    "error_type": type(exc).__name__,
                },
            )
