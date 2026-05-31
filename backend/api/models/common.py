"""
Lobster Quant - Common API Models
Shared response wrappers and error types.
"""

from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    data: T
    success: bool = True
    message: Optional[str] = None


class ApiError(BaseModel):
    """Standard API error response."""

    detail: str
    status: int = Field(..., ge=100, le=599)


class ErrorDetail(BaseModel):
    """Structured error detail inside ErrorResponse."""

    code: str = Field(..., description="Machine-readable error code, e.g. NOT_FOUND")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional detail")


class ErrorResponse(BaseModel):
    """Unified error response format.

    Includes top-level ``detail`` for backward compatibility with the frontend
    ``buildError`` helper (``src/lib/api.ts``), which reads ``body.detail``.
    """

    error: ErrorDetail
    detail: str = Field(..., description="Top-level detail for frontend backward compatibility")
    request_id: str = Field(..., description="Unique request identifier for tracing")
