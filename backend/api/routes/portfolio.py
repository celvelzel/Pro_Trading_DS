"""
Portfolio API Router
Endpoints for managing real portfolio positions and P&L tracking.
"""

from fastapi import APIRouter, HTTPException
from typing import List

from api.models.portfolio import (
    PositionResponse,
    AddPositionRequest,
    UpdatePositionRequest,
    CashBalanceResponse,
    SetCashRequest,
    AdjustCashRequest,
    PortfolioSummaryResponse,
    PortfolioPnlResponse,
    PnlByStrategyResponse,
)

router = APIRouter()


def _get_store():
    """Lazy import to avoid circular dependencies."""
    from lobster_quant.src.storage.portfolio_store import PortfolioStore
    return PortfolioStore()


def _get_current_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch current prices for symbols using the data engine."""
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        engine = get_data_engine()
        prices = {}
        for symbol in symbols:
            try:
                stock_data = engine.fetch_stock(symbol, years=1)
                if stock_data is not None:
                    price = stock_data.get_latest_price()
                    if price is not None:
                        prices[symbol] = price
            except Exception:
                continue
        return prices
    except Exception:
        return {}


@router.get("/", response_model=PortfolioSummaryResponse)
async def get_portfolio():
    """Get full portfolio summary with P&L calculations."""
    try:
        store = _get_store()
        positions = store.get_all_positions()
        symbols = [p["symbol"] for p in positions]
        prices = _get_current_prices(symbols) if symbols else {}
        summary = store.get_portfolio_summary(prices)
        return PortfolioSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=PositionResponse)
async def add_position(request: AddPositionRequest):
    """Add a new position to the portfolio."""
    try:
        store = _get_store()
        position = store.add_position(
            symbol=request.symbol,
            shares=request.shares,
            cost_basis=request.cost_basis,
            strategy_id=request.strategy_id,
        )
        return PositionResponse(**position)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{position_id}", response_model=PositionResponse)
async def update_position(position_id: str, request: UpdatePositionRequest):
    """Update an existing position."""
    try:
        store = _get_store()
        position = store.update_position(
            position_id=position_id,
            shares=request.shares,
            cost_basis=request.cost_basis,
            strategy_id=request.strategy_id,
        )
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        return PositionResponse(**position)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{position_id}")
async def delete_position(position_id: str):
    """Delete a position from the portfolio."""
    try:
        store = _get_store()
        deleted = store.delete_position(position_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Position not found")
        return {"success": True, "message": "Position deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_summary():
    """Get portfolio summary with current market values."""
    try:
        store = _get_store()
        positions = store.get_all_positions()
        symbols = [p["symbol"] for p in positions]
        prices = _get_current_prices(symbols) if symbols else {}
        summary = store.get_portfolio_summary(prices)
        return PortfolioSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl", response_model=PortfolioPnlResponse)
async def get_pnl():
    """Get P&L breakdown by strategy."""
    try:
        store = _get_store()
        positions = store.get_all_positions()
        symbols = [p["symbol"] for p in positions]
        prices = _get_current_prices(symbols) if symbols else {}
        strategies = store.get_pnl_by_strategy(prices)

        total_pnl = sum(s["pnl"] for s in strategies)
        total_cost = sum(s["total_cost"] for s in strategies)
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

        return PortfolioPnlResponse(
            strategies=[PnlByStrategyResponse(**s) for s in strategies],
            total_pnl=round(total_pnl, 2),
            total_pnl_percent=round(total_pnl_pct, 2),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cash", response_model=CashBalanceResponse)
async def get_cash():
    """Get current cash balance."""
    try:
        store = _get_store()
        cash_data = store._load_cash()
        return CashBalanceResponse(**cash_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cash", response_model=CashBalanceResponse)
async def set_cash(request: SetCashRequest):
    """Set cash balance."""
    try:
        store = _get_store()
        cash_data = store.set_cash_balance(request.balance)
        return CashBalanceResponse(**cash_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cash/adjust", response_model=CashBalanceResponse)
async def adjust_cash(request: AdjustCashRequest):
    """Adjust cash balance (positive = deposit, negative = withdrawal)."""
    try:
        store = _get_store()
        new_balance = store.adjust_cash(request.amount)
        cash_data = store._load_cash()
        return CashBalanceResponse(**cash_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
