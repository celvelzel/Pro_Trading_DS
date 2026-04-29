"""
Lobster Quant - Signal Engine
Orchestration layer that chains IndicatorEngine -> ScoringEngine -> SignalGenerator.
"""

from typing import Optional, Literal
import pandas as pd

from ..data.models import StockData, SignalResult
from ..analysis.signals.lobster_signal import SignalGenerator
from .indicator_engine import get_indicator_engine
from .scoring_engine import get_scoring_engine
from ..utils.logging import get_logger

logger = get_logger()


class SignalEngine:
    """Orchestration engine for signal generation.
    
    Chains three components:
    - IndicatorEngine: Computes technical indicators from price data
    - ScoringEngine: Applies multi-factor scoring to indicators
    - SignalGenerator: Classifies signals from scores
    """
    
    def __init__(self):
        self.indicator_engine = get_indicator_engine()
        self.scoring_engine = get_scoring_engine()
        self.signal_generator = SignalGenerator()
    
    def generate_signal(self, stock_data: StockData) -> SignalResult:
        """Generate complete trading signal for a stock.
        
        Args:
            stock_data: StockData with daily OHLCV data
            
        Returns:
            SignalResult with signal type, score, probability, and reasons
        """
        # Step 1: Compute indicators
        df_with_indicators = self.indicator_engine.compute_all(stock_data.daily)
        
        # Step 2: Compute score (returns a Series with score per row)
        score_series = self.scoring_engine.compute_score(df_with_indicators)
        
        # Get latest score value
        latest_score = score_series.iloc[-1] if len(score_series) > 0 else 0.0
        
        # Step 3: Calculate probability using SignalGenerator's method
        probability_up = self.signal_generator.calculate_probability_up(df_with_indicators)
        
        # Step 4: Classify signal type
        signal_type = self._classify_signal(latest_score, probability_up)
        
        # Step 5: Generate reasons using SignalGenerator helper
        latest_row = df_with_indicators.iloc[-1]
        reasons = self.signal_generator._generate_reasons(
            df_with_indicators, latest_row, latest_score
        )
        
        return SignalResult(
            symbol=stock_data.symbol,
            signal_type=signal_type,
            score=latest_score,
            probability_up=probability_up,
            reasons=reasons
        )
    
    def _classify_signal(self, score: float, probability_up: float) -> Literal["强烈推荐", "推荐", "持有", "观望"]:
        """Classify signal type based on score and probability.
        
        Args:
            score: Composite score (0-100)
            probability_up: Probability of price going up (0-100)
            
        Returns:
            Signal type string
        """
        if score >= 70 and probability_up >= 60:
            return "强烈推荐"
        elif score >= 50 and probability_up >= 50:
            return "推荐"
        elif score >= 30:
            return "持有"
        else:
            return "观望"


# Global singleton
_signal_engine: Optional[SignalEngine] = None


def get_signal_engine() -> SignalEngine:
    """Get global SignalEngine singleton."""
    global _signal_engine
    if _signal_engine is None:
        _signal_engine = SignalEngine()
    return _signal_engine