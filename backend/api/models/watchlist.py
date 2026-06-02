"""
Watchlist API Models
Pydantic models for watchlist CRUD operations.
"""

from pydantic import BaseModel, Field
from typing import Optional


class WatchlistData(BaseModel):
    """Watchlist data stored on disk."""
    symbols: list[str] = Field(default_factory=list)
    groups: dict[str, list[str]] = Field(default_factory=dict)
    tags: dict[str, list[str]] = Field(default_factory=dict)


class WatchlistResponse(BaseModel):
    """Response model for watchlist."""
    symbols: list[str] = Field(default_factory=list)
    groups: dict[str, list[str]] = Field(default_factory=dict)
    tags: dict[str, list[str]] = Field(default_factory=dict)


class AddSymbolRequest(BaseModel):
    """Request to add a symbol to watchlist."""
    symbol: str = Field(..., min_length=1, max_length=20)


class RemoveSymbolRequest(BaseModel):
    """Request to remove a symbol from watchlist."""
    symbol: str = Field(..., min_length=1, max_length=20)


class UpdateGroupsRequest(BaseModel):
    """Request to update groups."""
    groups: dict[str, list[str]] = Field(default_factory=dict)


class UpdateTagsRequest(BaseModel):
    """Request to update tags."""
    tags: dict[str, list[str]] = Field(default_factory=dict)
