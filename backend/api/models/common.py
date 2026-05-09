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
