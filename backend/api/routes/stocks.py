"""
Stocks API Router
Endpoints for stock data, indicators, signals, options, and risk assessment.
"""

from fastapi import APIRouter, HTTPException
import sys
import os

# Add the parent directory to the path to import existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from api.models.stocks import (
    Candle,
    StockData,
    Indicators,
    MACDData,
    Signal,
    SignalType,
    OptionsAnalysis,
    RiskAssessment,
)


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


@router.get("/{symbol}", response_model=StockData)
async def get_stock_data(symbol: str, period: str = "1y"):
    """
    Get stock OHLCV data.
    
    Args:
        symbol: Stock symbol (e.g., AAPL, MSFT)
        period: Time period (1d, 1w, 1m, 3m, 6m, 1y, 5y)
    
    Returns:
        Stock data with OHLCV candles
    """
    try:
        # Import existing data engine
        from lobster_quant.src.core.data_engine import get_data_engine
        
        engine = get_data_engine()
        stock_data = engine.fetch_stock(symbol)
        
        if stock_data is None:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        # Convert to response format
        candles = []
        for idx, row in stock_data.daily.iterrows():
            candles.append(Candle(
                time=int(idx.timestamp()),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume']),
            ))
        
        latest = stock_data.daily.iloc[-1]
        prev = stock_data.daily.iloc[-2] if len(stock_data.daily) > 1 else latest
        
        return StockData(
            symbol=symbol,
            name=symbol,  # lobster_quant StockData doesn't have name field
            price=float(latest['close']),
            change=float(latest['close'] - prev['close']),
            changePercent=float((latest['close'] - prev['close']) / prev['close'] * 100),
            volume=int(latest['volume']),
            candles=candles,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/indicators", response_model=Indicators)
async def get_indicators(symbol: str):
    """
    Get technical indicators for a stock.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Technical indicators (RSI, MACD, MA20, MA200, ATR)
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        
        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()
        
        stock_data = data_engine.fetch_stock(symbol)
        if stock_data is None:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        df = indicator_engine.compute_all(stock_data.daily)
        latest = df.iloc[-1]
        
        return Indicators(
            rsi=float(latest.get('rsi', 0)),
            macd=MACDData(
                value=float(latest.get('macd', 0)),
                signal=float(latest.get('macd_signal', 0)),
                histogram=float(latest.get('macd_hist', 0)),
            ),
            ma20=float(latest.get('ma20', 0)),
            ma200=float(latest.get('ma200', 0)),
            atr=float(latest.get('atr', 0)),
            atrPercent=float(latest.get('atr_percent', 0)),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/signals", response_model=Signal)
async def get_signals(symbol: str):
    """
    Get trading signals for a stock.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Trading signal with score, probability, and reasons
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.analysis.signals import SignalGenerator
        
        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()
        
        stock_data = data_engine.fetch_stock(symbol)
        if stock_data is None:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        df = indicator_engine.compute_all(stock_data.daily)
        
        signal_gen = SignalGenerator()
        signal = signal_gen.generate_signal(df)
        
        return Signal(
            type=_map_signal_type(signal.signal_type),
            score=int(signal.score),
            probability=int(signal.probability_up),
            reasons=signal.reasons if signal.reasons else [],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/options", response_model=OptionsAnalysis)
async def get_options_analysis(symbol: str):
    """
    Get options analysis for a stock.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Options analysis including Max Pain, Put/Call ratio, Support/Resistance
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.ui.pages.quant_tool_indicators import (
            calc_max_pain,
            find_support_resistance,
            calc_put_call_ratio,
        )
        
        data_engine = get_data_engine()
        stock_data = data_engine.fetch_stock(symbol)
        
        if stock_data is None:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        df = stock_data.daily
        current_price = df['close'].iloc[-1]
        
        # Calculate options metrics
        max_pain = calc_max_pain(df, current_price)
        support, resistance = find_support_resistance(df)
        put_call_ratio = calc_put_call_ratio(df)
        
        return OptionsAnalysis(
            maxPain=float(max_pain) if max_pain else float(current_price),
            putCallRatio=float(put_call_ratio) if put_call_ratio else 1.0,
            support=[float(s) for s in support[:3]] if support else [],
            resistance=[float(r) for r in resistance[:3]] if resistance else [],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/risk", response_model=RiskAssessment)
async def get_risk_assessment(symbol: str):
    """
    Get risk assessment for a stock.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Risk assessment including OFF filter status
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.core.risk_engine import RiskEngine
        
        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()
        
        stock_data = data_engine.fetch_stock(symbol)
        if stock_data is None:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        df = indicator_engine.compute_all(stock_data.daily)
        
        risk_engine = RiskEngine()
        latest_status = risk_engine.get_latest_status(df)
        off_results = risk_engine.assess(df)
        stats = risk_engine.get_stats(df, off_results)
        
        return RiskAssessment(
            status=latest_status.status_text.lower(),
            statusText=latest_status.status_text,
            reasons=latest_status.reasons if latest_status.reasons else [],
            onPercent=float(stats.get('on_pct', 0)),
            offPercent=float(stats.get('off_pct', 0)),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
