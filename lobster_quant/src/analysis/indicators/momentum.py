"""
Lobster Quant - Momentum Indicators
RSI, ROC, and other momentum measures.
"""

import pandas as pd
import numpy as np

from .base import Indicator, IndicatorResult, IndicatorRegistry
from src.utils.logging import get_logger

logger = get_logger()


class RSIIndicator(Indicator):
    """Relative Strength Index."""
    name = "rsi"
    params = {"period": 14}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        period = self.params.get("period", 14)
        close = data['close']
        
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        # Overbought/oversold signals
        overbought = rsi > 70
        oversold = rsi < 30
        
        return IndicatorResult(
            name=self.name,
            values=rsi,
            metadata={
                "period": period,
                "overbought": overbought,
                "oversold": oversold
            }
        )


class ROCIndicator(Indicator):
    """Rate of Change (momentum)."""
    name = "roc"
    params = {"period": 20}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        period = self.params.get("period", 20)
        roc = data['close'].pct_change(periods=period) * 100
        
        return IndicatorResult(
            name=self.name,
            values=roc,
            metadata={"period": period}
        )


class MomentumScoreIndicator(Indicator):
    """Composite momentum score combining RSI and ROC."""
    name = "momentum_score"
    params = {"rsi_period": 14, "roc_period": 20}
    
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        rsi_period = self.params.get("rsi_period", 14)
        roc_period = self.params.get("roc_period", 20)
        
        # RSI component (0-100)
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))
        avg_gain = gain.rolling(window=rsi_period).mean()
        avg_loss = loss.rolling(window=rsi_period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        # RSI score: oversold = high score, overbought = low score
        rsi_score = pd.Series(50.0, index=data.index)
        rsi_score = np.where(rsi < 30, 80, rsi_score)
        rsi_score = np.where((rsi >= 30) & (rsi < 50), 50 + (50 - rsi) * 0.6, rsi_score)
        rsi_score = np.where((rsi >= 50) & (rsi < 70), 50 - (rsi - 50) * 0.6, rsi_score)
        rsi_score = np.where(rsi >= 70, 20, rsi_score)
        rsi_score = pd.Series(rsi_score, index=data.index)
        
        # ROC component
        roc = data['close'].pct_change(periods=roc_period) * 100
        roc_score = pd.Series(50.0, index=data.index)
        roc_score = np.where(roc > 10, 80, roc_score)
        roc_score = np.where((roc > 0) & (roc <= 10), 50 + roc * 3, roc_score)
        roc_score = np.where((roc > -10) & (roc <= 0), 50 + roc * 3, roc_score)
        roc_score = np.where(roc <= -10, 20, roc_score)
        roc_score = pd.Series(roc_score, index=data.index)
        
        # Combined score
        combined = (rsi_score * 0.5 + roc_score * 0.5)
        
        return IndicatorResult(
            name=self.name,
            values=combined,
            metadata={
                "rsi": rsi,
                "roc": roc,
                "rsi_score": rsi_score,
                "roc_score": roc_score
            }
        )


# Register all indicators
IndicatorRegistry.register(RSIIndicator)
IndicatorRegistry.register(ROCIndicator)
IndicatorRegistry.register(MomentumScoreIndicator)

