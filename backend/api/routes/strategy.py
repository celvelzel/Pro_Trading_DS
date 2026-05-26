"""Strategy API Router."""
from fastapi import APIRouter, HTTPException
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from api.models.strategy import (
    CreateStrategyRequest, UpdateStrategyRequest, 
    StrategyResponse, CompareStrategiesRequest, StrategyComparisonResponse
)

router = APIRouter()


@router.get("/strategies", response_model=List[StrategyResponse])
async def list_strategies():
    """List all available strategies."""
    try:
        from lobster_quant.src.core.strategy_manager import StrategyManager
        
        manager = StrategyManager()
        strategies = manager.list_strategies()
        
        return [
            StrategyResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                params=s.params.model_dump(),
                logic=s.logic,
                isPreset=s.isPreset,
                createdAt=s.createdAt.isoformat(),
                updatedAt=s.updatedAt.isoformat() if s.updatedAt else None
            )
            for s in strategies
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: str):
    """Get strategy by ID."""
    try:
        from lobster_quant.src.core.strategy_manager import StrategyManager
        
        manager = StrategyManager()
        strategy = manager.get_strategy(strategy_id)
        
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
        
        return StrategyResponse(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            params=strategy.params.model_dump(),
            logic=strategy.logic,
            isPreset=strategy.isPreset,
            createdAt=strategy.createdAt.isoformat(),
            updatedAt=strategy.updatedAt.isoformat() if strategy.updatedAt else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies", response_model=StrategyResponse)
async def create_strategy(request: CreateStrategyRequest):
    """Create a new custom strategy."""
    try:
        from lobster_quant.src.core.strategy_manager import StrategyManager
        from lobster_quant.src.data.models import StrategyParams
        
        manager = StrategyManager()
        
        params = StrategyParams(
            holdingDays=request.params.holdingDays,
            minScore=request.params.minScore,
            slippagePct=request.params.slippagePct,
            commissionPct=request.params.commissionPct,
            positionSizing=request.params.positionSizing,
            positionSize=request.params.positionSize,
            initialCapital=request.params.initialCapital,
            maxPositions=request.params.maxPositions
        )
        
        strategy = manager.create_strategy(request.name, request.description, params)
        
        return StrategyResponse(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            params=strategy.params.model_dump(),
            logic=strategy.logic,
            isPreset=strategy.isPreset,
            createdAt=strategy.createdAt.isoformat(),
            updatedAt=strategy.updatedAt.isoformat() if strategy.updatedAt else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(strategy_id: str, request: UpdateStrategyRequest):
    """Update an existing strategy."""
    try:
        from lobster_quant.src.core.strategy_manager import StrategyManager
        from lobster_quant.src.data.models import StrategyParams
        
        manager = StrategyManager()
        
        kwargs = {}
        if request.name is not None:
            kwargs['name'] = request.name
        if request.description is not None:
            kwargs['description'] = request.description
        if request.params is not None:
            kwargs['params'] = StrategyParams(
                holdingDays=request.params.holdingDays,
                minScore=request.params.minScore,
                slippagePct=request.params.slippagePct,
                commissionPct=request.params.commissionPct,
                positionSizing=request.params.positionSizing,
                positionSize=request.params.positionSize,
                initialCapital=request.params.initialCapital,
                maxPositions=request.params.maxPositions
            )
        
        strategy = manager.update_strategy(strategy_id, **kwargs)
        
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found or is preset")
        
        return StrategyResponse(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            params=strategy.params.model_dump(),
            logic=strategy.logic,
            isPreset=strategy.isPreset,
            createdAt=strategy.createdAt.isoformat(),
            updatedAt=strategy.updatedAt.isoformat() if strategy.updatedAt else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """Delete a custom strategy."""
    try:
        from lobster_quant.src.core.strategy_manager import StrategyManager
        
        manager = StrategyManager()
        deleted = manager.delete_strategy(strategy_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found or is preset")
        
        return {"message": f"Strategy {strategy_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/compare", response_model=StrategyComparisonResponse)
async def compare_strategies(request: CompareStrategiesRequest):
    """Compare multiple strategies."""
    try:
        from lobster_quant.src.core.strategy_manager import StrategyManager
        
        manager = StrategyManager()
        result = manager.compare_strategies(
            request.strategyIds,
            request.symbol,
            request.startDate,
            request.endDate
        )
        
        return StrategyComparisonResponse(
            strategies=result["strategies"],
            bestReturn=result.get("best_return"),
            bestSharpe=result.get("best_sharpe"),
            lowestDrawdown=result.get("lowest_drawdown")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
