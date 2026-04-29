"""
Lobster Quant - Legacy Bridge
Provides backward-compatible API wrapping the new architecture.
Allows gradual migration from old code to new modules.
"""

from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import pandas as pd
import warnings

from .core.data_engine import get_data_engine, DataEngine
from .core.indicator_engine import get_indicator_engine, IndicatorEngine
from .core.risk_engine import RiskEngine
from .analysis.signals import SignalGenerator
from .analysis.backtest import BacktestEngine
from .config.settings import get_settings
from .data.models import SignalResult, StockData

# Suppress import warnings for backward compatibility
warnings.filterwarnings("ignore", message=".*backward compatibility.*")


class LegacyAdapter:
    """Adapter providing backward-compatible API for old code.
    
    Usage:
        from src.compat import legacy
        
        # Old API: fetch data
        df = legacy.fetch_daily("AAPL")
        
        # Old API: compute indicators
        indicators = legacy.compute_indicators(df)
        
        # Old API: get signal
        signal = legacy.get_signal("AAPL")
    """
    
    def __init__(self):
        self._data_engine = None
        self._indicator_engine = None
        self._signal_gen = None
        self._risk_engine = None
        self._backtest_engine = None
        self._cache = {}
    
    @property
    def data_engine(self) -> DataEngine:
        if self._data_engine is None:
            self._data_engine = get_data_engine()
        return self._data_engine
    
    @property
    def indicator_engine(self) -> IndicatorEngine:
        if self._indicator_engine is None:
            self._indicator_engine = get_indicator_engine()
        return self._indicator_engine
    
    @property
    def signal_generator(self) -> SignalGenerator:
        if self._signal_gen is None:
            self._signal_gen = SignalGenerator()
        return self._signal_gen
    
    @property
    def risk_engine(self) -> RiskEngine:
        if self._risk_engine is None:
            self._risk_engine = RiskEngine()
        return self._risk_engine
    
    @property
    def backtest_engine(self) -> BacktestEngine:
        if self._backtest_engine is None:
            self._backtest_engine = BacktestEngine()
        return self._backtest_engine
    
    # ============================================================
    # Data Access (backward compatible)
    # ============================================================
    
    def fetch_daily(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV data (backward compatible)."""
        stock_data = self.data_engine.fetch_stock(symbol, years)
        if stock_data is None:
            return None
        return stock_data.daily
    
    def fetch_stock_data(self, symbol: str, years: int = 3) -> Optional[StockData]:
        """Fetch complete stock data."""
        return self.data_engine.fetch_stock(symbol, years)
    
    def fetch_options(self, symbol: str) -> Optional[dict]:
        """Fetch options data (backward compatible)."""
        provider = self.data_engine._get_provider(symbol)
        if provider is None:
            return None
        options = provider.fetch_options(symbol)
        if options is None:
            return None
        return options.model_dump()
    
    # ============================================================
    # Indicators (backward compatible)
    # ============================================================
    
    def compute_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute all indicators (backward compatible).
        
        Returns DataFrame with columns: slope_daily, slope_weekly, slope_monthly,
        rsi, volume_ratio, macd_golden, ma_bullish, bb_position, ma20, ma200,
        atr_pct, gap_pct, momentum_score, etc.
        """
        return self.indicator_engine.compute_all(data)
    
    def compute_slope(self, series: pd.Series, window: int = 20) -> pd.Series:
        """Compute linear regression slope."""
        from .analysis.indicators.base import rolling_slope
        return rolling_slope(series, window)
    
    # ============================================================
    # Signals (backward compatible)
    # ============================================================
    
    def get_signal(self, symbol: str, years: int = 3) -> Optional[Dict[str, Any]]:
        """Get signal for a symbol (backward compatible).
        
        Returns dict with keys:
        - signal_type: str
        - score: float
        - probability_up: float
        - reasons: list
        """
        stock_data = self.data_engine.fetch_stock(symbol, years)
        if stock_data is None:
            return None
        
        df = self.indicator_engine.compute_all(stock_data.daily)
        signal = self.signal_generator.generate_signal(df)
        signal.symbol = symbol
        
        return {
            'signal_type': signal.signal_type,
            'score': signal.score,
            'probability_up': signal.probability_up,
            'reasons': signal.reasons,
            'is_bullish': signal.is_bullish,
            'strength': signal.strength,
        }
    
    def calculate_score(self, data: pd.DataFrame) -> float:
        """Calculate composite score (backward compatible)."""
        return self.signal_generator.calculate_score(data)
    
    # ============================================================
    # Risk / OFF Filter (backward compatible)
    # ============================================================
    
    def assess_risk(self, data: pd.DataFrame) -> pd.DataFrame:
        """Assess market risk (backward compatible)."""
        return self.risk_engine.assess(data)
    
    def get_off_status(self, data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Get OFF status (backward compatible).
        
        Returns (is_on, reasons_list)
        """
        return self.risk_engine.should_trade(data)
    
    # ============================================================
    # Backtest (backward compatible)
    # ============================================================
    
    def run_backtest(self, 
                     data: pd.DataFrame, 
                     symbol: str = "") -> Dict[str, Any]:
        """Run backtest (backward compatible).
        
        Returns dict with key metrics.
        """
        score_series = pd.Series(
            [self.signal_generator.calculate_score(data.iloc[:i+1]) 
             for i in range(len(data))],
            index=data.index
        )
        result = self.backtest_engine.run(data, score_series, symbol=symbol)
        return self.backtest_engine.get_trade_summary(result)
    
    # ============================================================
    # Cache (backward compatible)
    # ============================================================
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self.data_engine.get_cache_stats()
    
    def clear_cache(self) -> int:
        """Clear data cache."""
        return self.data_engine.clear_cache()


# Global legacy adapter instance
legacy = LegacyAdapter()


def get_legacy_adapter() -> LegacyAdapter:
    """Get the global legacy adapter instance."""
    return legacy
