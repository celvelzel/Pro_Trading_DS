"""
Lobster Quant - Volatility Indicators
ATR, Bollinger Bands, and volatility measures.
"""

import pandas as pd
import numpy as np

from .base import Indicator, IndicatorResult, IndicatorRegistry
from src.utils.logging import get_logger

logger = get_logger()


class ATRIndicator(Indicator):
    """Average True Range."""
    name = "atr"
    params = {"period": 14}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        period = self.params.get("period", 14)
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        atr_pct = atr / close
        
        return IndicatorResult(
            name=self.name,
            values=atr,
            metadata={
                "period": period,
                "atr_pct": atr_pct,
                "true_range": tr
            }
        )


class BollingerBandsIndicator(Indicator):
    """Bollinger Bands."""
    name = "bollinger_bands"
    params = {"period": 20, "std_dev": 2.0}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        period = self.params.get("period", 20)
        std_dev = self.params.get("std_dev", 2.0)
        
        close = data['close']
        ma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        
        # Position within bands (0 = lower, 1 = upper)
        position = (close - lower) / (upper - lower)
        position = position.clip(0, 1)
        
        # Band width as volatility measure
        bandwidth = (upper - lower) / ma
        
        return IndicatorResult(
            name=self.name,
            values=ma,
            metadata={
                "period": period,
                "std_dev": std_dev,
                "upper": upper,
                "lower": lower,
                "position": position,
                "bandwidth": bandwidth
            }
        )


class GapIndicator(Indicator):
    """Price gap analysis."""
    name = "gap"
    params = {"lookback": 60}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        lookback = self.params.get("lookback", 60)
        
        prev_close = data['close'].shift(1)
        gap = (data['open'] - prev_close) / prev_close
        
        gap_std = gap.rolling(window=lookback).std()
        gap_zscore = gap / gap_std.replace(0, np.nan)
        
        # Large gap detection
        large_gap = gap.abs() > 2 * gap_std
        
        return IndicatorResult(
            name=self.name,
            values=gap,
            metadata={
                "gap_pct": gap * 100,
                "gap_std": gap_std,
                "gap_zscore": gap_zscore,
                "large_gap": large_gap,
                "lookback": lookback
            }
        )


# Register all indicators
IndicatorRegistry.register(ATRIndicator)
IndicatorRegistry.register(BollingerBandsIndicator)
IndicatorRegistry.register(GapIndicator)

