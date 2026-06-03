"""
Watchlist API Router
Endpoints for managing the persistent watchlist.
"""

from fastapi import APIRouter, HTTPException
import json
import os
from pathlib import Path

from api.models.watchlist import (
    WatchlistData,
    WatchlistResponse,
    AddSymbolRequest,
    RemoveSymbolRequest,
    UpdateGroupsRequest,
    UpdateTagsRequest,
    BulkAddSymbolsRequest,
)

router = APIRouter()

# Data file path
DATA_DIR = Path(__file__).parent.parent.parent / "data"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"


def _ensure_data_dir():
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_watchlist() -> WatchlistData:
    """Load watchlist from disk."""
    if not WATCHLIST_FILE.exists():
        return WatchlistData()
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return WatchlistData(**data)
    except (json.JSONDecodeError, Exception):
        return WatchlistData()


def _save_watchlist(watchlist: WatchlistData):
    """Save watchlist to disk."""
    _ensure_data_dir()
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist.model_dump(), f, indent=2, ensure_ascii=False)


@router.get("/", response_model=WatchlistResponse)
async def get_watchlist():
    """Get the current watchlist."""
    watchlist = _load_watchlist()
    
    # Migration: if symbols exist but groups are empty, create a 'Default' group
    if watchlist.symbols and not watchlist.groups:
        watchlist.groups = {"Default": watchlist.symbols[:]}
        _save_watchlist(watchlist)
        
    return WatchlistResponse(
        symbols=watchlist.symbols,
        groups=watchlist.groups,
        tags=watchlist.tags,
    )


@router.post("/symbols", response_model=WatchlistResponse)
async def add_symbol(request: AddSymbolRequest):
    """Add a symbol to the watchlist."""
    watchlist = _load_watchlist()
    symbol = request.symbol.upper()
    
    if symbol not in watchlist.symbols:
        watchlist.symbols.append(symbol)
        _save_watchlist(watchlist)
    
    return WatchlistResponse(
        symbols=watchlist.symbols,
        groups=watchlist.groups,
        tags=watchlist.tags,
    )


@router.post("/symbols/bulk", response_model=WatchlistResponse)
async def bulk_add_symbols(request: BulkAddSymbolsRequest):
    """Add multiple symbols to the watchlist and optionally a group."""
    watchlist = _load_watchlist()
    new_symbols = [s.upper() for s in request.symbols if s.strip()]
    
    # Add to master symbols list
    for symbol in new_symbols:
        if symbol not in watchlist.symbols:
            watchlist.symbols.append(symbol)
            
    # Add to group if specified
    if request.group:
        group_name = request.group
        if group_name not in watchlist.groups:
            watchlist.groups[group_name] = []
        
        current_group = set(watchlist.groups[group_name])
        for symbol in new_symbols:
            if symbol not in current_group:
                watchlist.groups[group_name].append(symbol)
                
    _save_watchlist(watchlist)
    
    return WatchlistResponse(
        symbols=watchlist.symbols,
        groups=watchlist.groups,
        tags=watchlist.tags,
    )


@router.delete("/symbols/{symbol}", response_model=WatchlistResponse)
async def remove_symbol(symbol: str):
    """Remove a symbol from the watchlist."""
    watchlist = _load_watchlist()
    symbol = symbol.upper()
    
    if symbol in watchlist.symbols:
        watchlist.symbols.remove(symbol)
        # Also remove from groups and tags
        for group_name in watchlist.groups:
            watchlist.groups[group_name] = [
                s for s in watchlist.groups[group_name] if s != symbol
            ]
        if symbol in watchlist.tags:
            del watchlist.tags[symbol]
        _save_watchlist(watchlist)
    
    return WatchlistResponse(
        symbols=watchlist.symbols,
        groups=watchlist.groups,
        tags=watchlist.tags,
    )


@router.put("/groups", response_model=WatchlistResponse)
async def update_groups(request: UpdateGroupsRequest):
    """Update watchlist groups."""
    watchlist = _load_watchlist()
    watchlist.groups = request.groups
    _save_watchlist(watchlist)
    return WatchlistResponse(
        symbols=watchlist.symbols,
        groups=watchlist.groups,
        tags=watchlist.tags,
    )


@router.put("/tags", response_model=WatchlistResponse)
async def update_tags(request: UpdateTagsRequest):
    """Update watchlist tags."""
    watchlist = _load_watchlist()
    watchlist.tags = request.tags
    _save_watchlist(watchlist)
    return WatchlistResponse(
        symbols=watchlist.symbols,
        groups=watchlist.groups,
        tags=watchlist.tags,
    )


@router.delete("/", response_model=WatchlistResponse)
async def clear_watchlist():
    """Clear the entire watchlist."""
    watchlist = WatchlistData()
    _save_watchlist(watchlist)
    return WatchlistResponse(
        symbols=watchlist.symbols,
        groups=watchlist.groups,
        tags=watchlist.tags,
    )
