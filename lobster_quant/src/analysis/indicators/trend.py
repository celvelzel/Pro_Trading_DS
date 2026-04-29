"""
Lobster Quant - Trend Indicators
Moving averages, slopes, and trend detection.
"""

import pandas as pd
import numpy as np

from .base import Indicator, IndicatorResult, IndicatorRegistry, rolling_slope
from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger()


class SMAIndicator(Indicator):
    """Simple Moving Average."""
    name = "sma"
    params = {"period": 20}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        period = self.params.get("period", 20)
        sma = data['close'].rolling(window=period).mean()
        return IndicatorResult(
            name=self.name,
            values=sma,
            metadata={"period": period}
        )


class EMAIndicator(Indicator):
    """Exponential Moving Average."""
    name = "ema"
    params = {"period": 20}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        period = self.params.get("period", 20)
        ema = data['close'].ewm(span=period, adjust=False).mean()
        return IndicatorResult(
            name=self.name,
            values=ema,
            metadata={"period": period}
        )


class SlopeIndicator(Indicator):
    """Linear regression slope over a window."""
    name = "slope"
    params = {"period": 20, "normalize": True}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        period = self.params.get("period", 20)
        normalize = self.params.get("normalize", True)
        
        slope = rolling_slope(data['close'], window=period)
        
        if normalize:
            # Normalize by current price
            slope = slope / data['close']
        
        return IndicatorResult(
            name=self.name,
            values=slope,
            metadata={"period": period, "normalized": normalize}
        )


class MACDIndicator(Indicator):
    """Moving Average Convergence Divergence."""
    name = "macd"
    params = {"fast": 12, "slow": 26, "signal": 9}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        fast = self.params.get("fast", 12)
        slow = self.params.get("slow", 26)
        signal_period = self.params.get("signal", 9)
        
        ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        # Golden cross signal
        golden_cross = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        
        return IndicatorResult(
            name=self.name,
            values=macd_line,
            metadata={
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram,
                "golden_cross": golden_cross,
                "fast": fast,
                "slow": slow,
                "signal_period": signal_period
            }
        )


class MABullishIndicator(Indicator):
    """Moving Average Bullish Alignment (close > MA_short > MA_long)."""
    name = "ma_bullish"
    params = {"short_period": 20, "long_period": 200}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        short = self.params.get("short_period", 20)
        long = self.params.get("long_period", 200)
        
        ma_short = data['close'].rolling(window=short).mean()
        ma_long = data['close'].rolling(window=long).mean()
        
        bullish = (data['close'] > ma_short) & (ma_short > ma_long)
        
        return IndicatorResult(
            name=self.name,
            values=bullish.astype(int),
            metadata={
                "short_period": short,
                "long_period": long,
                "ma_short": ma_short,
                "ma_long": ma_long
            }
        )


# Register all indicators
IndicatorRegistry.register(SMAIndicator)
IndicatorRegistry.register(EMAIndicator)
IndicatorRegistry.register(SlopeIndicator)
IndicatorRegistry.register(MACDIndicator)
IndicatorRegistry.register(MABullishIndicator)

