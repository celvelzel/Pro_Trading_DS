"""
Scanner API Router
Endpoints for stock scanning and screening.
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
logger = logging.getLogger(__name__)

from api.models.scanner import ScanRequest, StockResult, ScanResponse
from api.models.stocks import SignalType
from api.deps import get_data_engine_dep, get_indicator_engine_dep
from api.error_handler import DataFetchError, handle_data_errors


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
@handle_data_errors
async def scan_stocks(request: ScanRequest):
    """
    Scan stocks based on market and minimum score.
    
    Args:
        request: Scan request with market and minScore
    
    Returns:
        List of stocks meeting the criteria
    """
    try:
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
        
        data_engine = get_data_engine_dep()
        indicator_engine = get_indicator_engine_dep()
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
                logger.warning(f"Failed to scan {symbol}: {e}")
                continue
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        return ScanResponse(
            results=results,
            total=len(results),
            market=request.market,
            minScore=request.minScore,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise DataFetchError(detail=str(e), source="data_engine")


@router.post("/scan/stream")
async def scan_stocks_stream(request: ScanRequest):
    """
    Stream stock scan results via SSE as each stock is computed.

    Sends events:
    - `stock`: a StockResult that passed the minScore filter
    - `progress`: { processed, total, symbol } for progress tracking
    - `done`: { total } when scan is complete
    - `error`: { detail } on failure

    Falls back gracefully — frontend can still use /scan for sync.
    """
    try:
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

        data_engine = get_data_engine_dep()
        indicator_engine = get_indicator_engine_dep()
        signal_gen = SignalGenerator()

        async def event_generator():
            total = len(stock_list)
            processed = 0

            for symbol in stock_list:
                processed += 1
                try:
                    stock_data = data_engine.fetch_stock(symbol)
                    if stock_data is None:
                        # Send progress even for skipped stocks
                        yield f"event: progress\ndata: {json.dumps({'processed': processed, 'total': total, 'symbol': symbol, 'status': 'skipped'})}\n\n"
                        continue

                    df = indicator_engine.compute_all(stock_data.daily)
                    signal = signal_gen.generate_signal(df)
                    signal.symbol = symbol

                    # Send progress update
                    yield f"event: progress\ndata: {json.dumps({'processed': processed, 'total': total, 'symbol': symbol, 'status': 'processing'})}\n\n"

                    # Filter by minimum score
                    if signal.score >= request.minScore:
                        latest = df.iloc[-1]
                        prev = df.iloc[-2] if len(df) > 1 else latest

                        result = StockResult(
                            symbol=symbol,
                            name=symbol,
                            price=float(latest['close']),
                            change=float(latest['close'] - prev['close']),
                            changePercent=float((latest['close'] - prev['close']) / prev['close'] * 100),
                            score=int(signal.score),
                            signalType=_map_signal_type(signal.signal_type),
                            probability=int(signal.probability_up) if hasattr(signal, 'probability_up') else 50,
                            reasons=signal.reasons if signal.reasons else [],
                        )
                        yield f"event: stock\ndata: {result.model_dump_json()}\n\n"

                except Exception as e:
                    logger.warning(f"Failed to scan {symbol}: {e}")
                    yield f"event: progress\ndata: {json.dumps({'processed': processed, 'total': total, 'symbol': symbol, 'status': 'error', 'error': str(e)})}\n\n"
                    continue

            yield f"event: done\ndata: {json.dumps({'total': total})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise DataFetchError(detail=str(e), source="data_engine")
