"""
Lobster Quant - Composite Signal Generator
Combines signal generation, scoring, indicators, and risk assessment.
"""

from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field, ConfigDict

from src.data.models import (
    SignalResult,
    StockData,
)
from src.analysis.signals.lobster_signal import SignalGenerator
from src.core.scoring_engine import (
    ScoringEngine,
    get_scoring_engine,
)
from src.core.risk_engine import RiskEngine
from src.core.indicator_engine import IndicatorEngine, get_indicator_engine
from src.utils.logging import get_logger

logger = get_logger()


class CompositeSignalResult(BaseModel):
    """Result combining signal, risk, and scoring data."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    signal: SignalResult
    is_trading_allowed: bool
    risk_reasons: list[str] = Field(default_factory=list)
    score_series: Optional[pd.Series] = None


class CompositeSignalGenerator:
    """Composite signal generator integrating all analysis components.
    
    Combines indicator computation, signal generation, scoring,
    and risk assessment into a single unified pipeline.
    """
    
    def __init__(self) -> None:
        """Initialize component engines."""
        self.signal_generator = SignalGenerator()
        self.scoring_engine = get_scoring_engine()
        self.risk_engine = RiskEngine()
        self.indicator_engine = get_indicator_engine()
    
    def generate(
        self,
        stock_data: StockData,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> CompositeSignalResult:
        """Generate composite trading signal.
        
        Args:
            stock_data: Stock data with daily OHLCV
            benchmark_data: Optional benchmark data for risk assessment
            
        Returns:
            CompositeSignalResult with signal, risk status, and scores
        """
        # Step 1: Compute indicators
        df = self.indicator_engine.compute_all(stock_data.daily)
        
        # Step 2: Generate signal
        raw_signal = self.signal_generator.generate_signal(df)
        raw_signal.symbol = stock_data.symbol
        
        # Step 3: Compute score series
        score_series = self.scoring_engine.compute_score(df)
        
        # Step 4: Check risk status
        risk_status = self.risk_engine.get_latest_status(df, benchmark_data)
        
        # Step 5: Adjust signal for risk if needed
        if risk_status.is_off:
            adjusted_signal = self._adjust_for_risk(
                raw_signal,
                risk_status.is_off,
                risk_status.reasons
            )
        else:
            adjusted_signal = raw_signal
        
        return CompositeSignalResult(
            signal=adjusted_signal,
            is_trading_allowed=risk_status.is_on,
            risk_reasons=risk_status.reasons,
            score_series=score_series
        )
    
    def _adjust_for_risk(
        self,
        signal: SignalResult,
        is_off: bool,
        risk_reasons: list[str]
    ) -> SignalResult:
        """Adjust signal type when OFF filter triggers.
        
        Downgrades signal type:
        - 强烈推荐 -> 推荐
        - 推荐 -> 持有
        - 持有 -> 观望
        
        Appends risk reasons to signal reasons.
        
        Args:
            signal: Original signal
            is_off: Whether OFF filter is triggered
            risk_reasons: List of risk trigger reasons
            
        Returns:
            Adjusted signal result
        """
        if not is_off:
            return signal
        
        # Downgrade signal type
        if signal.signal_type == "强烈推荐":
            new_type = "推荐"
        elif signal.signal_type == "推荐":
            new_type = "持有"
        elif signal.signal_type == "持有":
            new_type = "观望"
        else:
            new_type = signal.signal_type
        
        # Build new reasons
        new_reasons = signal.reasons.copy()
        new_reasons.append(f"风险过滤触发: {', '.join(risk_reasons)}")
        
        return SignalResult(
            symbol=signal.symbol,
            signal_type=new_type,
            score=signal.score,
            probability_up=signal.probability_up,
            reasons=new_reasons,
            timestamp=signal.timestamp
        )