"""
Scanner API Router
Endpoints for stock scanning and screening.
"""

from fastapi import APIRouter, HTTPException
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from api.models.scanner import ScanRequest, StockResult, ScanResponse
from api.models.stocks import SignalType


def _map_signal_type(lobster_type: str) -> SignalType:
    """Map lobster_quant signal types to API signal types.

    lobster_quant uses: 强烈推荐, 推荐, 持有, 观望, sell, neutral
    API uses: bullish, bearish, neutral
    """
    mapping: dict[str, SignalType] = {
        "强烈推荐": "bullish",
        "推荐": "bullish",
        "持有": "neutral",
        "观望": "neutral",
        "sell": "bearish",
        "neutral": "neutral",
        "bullish": "bullish",
        "bearish": "bearish",
    }
    return mapping.get(lobster_type, "neutral")

router = APIRouter()


# Stock lists
US_STOCK_LIST = [
    'AIPO', 'AMZN', 'COHR', 'GLW', 'GOOG', 'ICLN', 'LITE', 'MU',
    'QQQ', 'SPY', 'TSLA', 'URA', 'VTI', 'XLE', 'XLU'
]

HK_STOCK_LIST = [
    '0005.HK', '0700.HK', '1299.HK', '2318.HK', '3690.HK',
    '9988.HK', '1810.HK', '2269.HK', '2020.HK', '9618.HK'
]

A_STOCK_LIST = [
    '600519', '000001', '300308', '002594', '600036',
    '000333', '300750', '601318', '600276', '002415'
]


@router.post("/scan", response_model=ScanResponse)
async def scan_stocks(request: ScanRequest):
    """
    Scan stocks based on market and minimum score.
    
    Args:
        request: Scan request with market and minScore
    
    Returns:
        List of stocks meeting the criteria
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.analysis.signals import SignalGenerator
        
        # Get stock list based on market
        if request.market == "US":
            stock_list = US_STOCK_LIST
        elif request.market == "HK":
            stock_list = HK_STOCK_LIST
        elif request.market == "A":
            stock_list = A_STOCK_LIST
        else:
            raise HTTPException(status_code=400, detail=f"Invalid market: {request.market}")
        
        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()
        signal_gen = SignalGenerator()
        
        results = []
        
        for symbol in stock_list:
            try:
                stock_data = data_engine.fetch_stock(symbol)
                if stock_data is None:
                    continue
                
                df = indicator_engine.compute_all(stock_data.daily)
                signal = signal_gen.generate_signal(df)
                signal.symbol = symbol
                
                # Filter by minimum score
                if signal.score >= request.minScore:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    
                    results.append(StockResult(
                        symbol=symbol,
                        name=symbol,  # lobster_quant StockData doesn't have name field
                        price=float(latest['close']),
                        change=float(latest['close'] - prev['close']),
                        changePercent=float((latest['close'] - prev['close']) / prev['close'] * 100),
                        score=int(signal.score),
                        signalType=_map_signal_type(signal.signal_type),
                        probability=int(signal.probability_up) if hasattr(signal, 'probability_up') else 50,
                        reasons=signal.reasons if signal.reasons else [],
                    ))
            except Exception as e:
                # Skip stocks that fail to process
                continue
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        return ScanResponse(
            results=results,
            total=len(results),
            market=request.market,
            minScore=request.minScore,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
