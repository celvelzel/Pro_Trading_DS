"""
Lobster Quant - Volume Indicators
Volume analysis and ratios.
"""

import pandas as pd
import numpy as np

from .base import Indicator, IndicatorResult, IndicatorRegistry
from src.utils.logging import get_logger

logger = get_logger()


class VolumeRatioIndicator(Indicator):
    """Volume ratio compared to moving average."""
    name = "volume_ratio"
    params = {"period": 20}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        period = self.params.get("period", 20)
        
        volume = data['volume']
        volume_ma = volume.rolling(window=period).mean()
        ratio = volume / volume_ma.replace(0, np.nan)
        
        # High volume signal
        high_vol = ratio > 1.5
        low_vol = ratio < 0.8
        
        return IndicatorResult(
            name=self.name,
            values=ratio,
            metadata={
                "period": period,
                "volume_ma": volume_ma,
                "high_volume": high_vol,
                "low_volume": low_vol
            }
        )


class VolumeTrendIndicator(Indicator):
    """Volume trend analysis."""
    name = "volume_trend"
    params = {"short_period": 5, "long_period": 20}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        short = self.params.get("short_period", 5)
        long = self.params.get("long_period", 20)
        
        volume = data['volume']
        vol_short = volume.rolling(window=short).mean()
        vol_long = volume.rolling(window=long).mean()
        
        trend = vol_short / vol_long.replace(0, np.nan)
        
        # Volume increasing/decreasing
        increasing = trend > 1.2
        decreasing = trend < 0.8
        
        return IndicatorResult(
            name=self.name,
            values=trend,
            metadata={
                "short_period": short,
                "long_period": long,
                "vol_short": vol_short,
                "vol_long": vol_long,
                "increasing": increasing,
                "decreasing": decreasing
            }
        )


class OBVIndicator(Indicator):
    """On-Balance Volume."""
    name = "obv"
    params = {}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        close = data['close']
        volume = data['volume']
        
        # Calculate OBV
        obv = pd.Series(0.0, index=data.index)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(data)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        # OBV slope
        obv_ma = obv.rolling(window=20).mean()
        obv_trend = obv > obv_ma
        
        return IndicatorResult(
            name=self.name,
            values=obv,
            metadata={
                "obv_ma": obv_ma,
                "obv_trend": obv_trend
            }
        )


# Register all indicators
IndicatorRegistry.register(VolumeRatioIndicator)
IndicatorRegistry.register(VolumeTrendIndicator)
IndicatorRegistry.register(OBVIndicator)

