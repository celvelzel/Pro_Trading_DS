"""
Lobster Quant - Indicator Engine
High-level API for computing all indicators on stock data.
"""

from typing import Dict, List, Optional
import pandas as pd

from ..data.models import StockData
from ..analysis.indicators import IndicatorRegistry
from ..analysis.indicators.trend import SlopeIndicator, MACDIndicator, MABullishIndicator
from ..analysis.indicators.momentum import RSIIndicator, MomentumScoreIndicator
from ..analysis.indicators.volatility import ATRIndicator, BollingerBandsIndicator
from ..analysis.indicators.volume import VolumeRatioIndicator, VolumeTrendIndicator
from ..utils.logging import get_logger

logger = get_logger()


class IndicatorEngine:
    """High-level engine for computing technical indicators.
    
    Provides a unified interface to calculate all indicators
    for a given stock's data.
    """
    
    def __init__(self):
        self._indicators: Dict[str, any] = {}
        self._setup_default_indicators()
    
    def _setup_default_indicators(self) -> None:
        """Initialize default indicator instances."""
        self._indicators = {
            # Trend
            'sma20': IndicatorRegistry.create('sma', period=20),
            'sma50': IndicatorRegistry.create('sma', period=50),
            'sma200': IndicatorRegistry.create('sma', period=200),
            'ema20': IndicatorRegistry.create('ema', period=20),
            'macd': IndicatorRegistry.create('macd'),
            'ma_bullish': IndicatorRegistry.create('ma_bullish'),
            
            # Momentum
            'rsi': IndicatorRegistry.create('rsi', period=14),
            'roc': IndicatorRegistry.create('roc', period=20),
            'momentum_score': IndicatorRegistry.create('momentum_score'),
            
            # Volatility
            'atr': IndicatorRegistry.create('atr', period=14),
            'bb': IndicatorRegistry.create('bollinger_bands'),
            'gap': IndicatorRegistry.create('gap'),
            
            # Volume
            'volume_ratio': IndicatorRegistry.create('volume_ratio'),
            'volume_trend': IndicatorRegistry.create('volume_trend'),
            'obv': IndicatorRegistry.create('obv'),
        }
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute all indicators and merge into DataFrame.
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            DataFrame with all indicator columns added
        """
        df = data.copy()
        
        # Trend indicators
        self._add_slope_indicators(df)
        self._add_macd(df)
        self._add_ma_bullish(df)
        
        # Momentum indicators
        self._add_rsi(df)
        self._add_momentum_score(df)
        
        # Volatility indicators
        self._add_atr(df)
        self._add_bollinger_bands(df)
        self._add_gap(df)
        
        # Volume indicators
        self._add_volume_ratio(df)
        self._add_volume_trend(df)
        
        # Ensure all indicator columns are numeric (defense-in-depth)
        # This prevents TypeError when comparing with int/float in downstream consumers
        for col in df.columns:
            if col not in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def compute_for_stock(self, stock_data: StockData) -> Dict[str, pd.DataFrame]:
        """Compute indicators for all timeframes.
        
        Args:
            stock_data: StockData with daily/weekly/monthly
        
        Returns:
            Dictionary mapping timeframe to DataFrame
        """
        results = {}
        
        if stock_data.daily is not None:
            results['daily'] = self.compute_all(stock_data.daily)
        
        if stock_data.weekly is not None:
            results['weekly'] = self.compute_all(stock_data.weekly)
        
        if stock_data.monthly is not None:
            results['monthly'] = self.compute_all(stock_data.monthly)
        
        return results
    
    def _add_slope_indicators(self, df: pd.DataFrame) -> None:
        """Add slope indicators for multiple timeframes."""
        from ..analysis.indicators.base import rolling_slope
        
        # Daily slope
        df['slope_daily'] = rolling_slope(df['close'], window=20)
        
        # Weekly slope (approximate with 5-day slope)
        df['slope_weekly'] = rolling_slope(df['close'], window=5)
        
        # Monthly slope (approximate with 20-day slope)
        df['slope_monthly'] = rolling_slope(df['close'], window=20)
    
    def _add_macd(self, df: pd.DataFrame) -> None:
        """Add MACD indicator."""
        try:
            result = self._indicators['macd'].calculate(df)
            meta = result.metadata
            df['macd'] = meta['macd']
            df['macd_signal'] = meta['signal']
            df['macd_hist'] = meta['histogram']
            df['macd_golden'] = meta['golden_cross']
        except Exception as e:
            logger.warning(f"MACD calculation failed: {e}")
    
    def _add_ma_bullish(self, df: pd.DataFrame) -> None:
        """Add MA bullish alignment."""
        try:
            result = self._indicators['ma_bullish'].calculate(df)
            df['ma_bullish'] = result.values.astype(bool)
            
            # Also add individual MAs
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma50'] = df['close'].rolling(window=50).mean()
            df['ma200'] = df['close'].rolling(window=200).mean()
        except Exception as e:
            logger.warning(f"MA bullish calculation failed: {e}")
    
    def _add_rsi(self, df: pd.DataFrame) -> None:
        """Add RSI indicator."""
        try:
            result = self._indicators['rsi'].calculate(df)
            df['rsi'] = result.values
        except Exception as e:
            logger.warning(f"RSI calculation failed: {e}")
    
    def _add_momentum_score(self, df: pd.DataFrame) -> None:
        """Add momentum score."""
        try:
            result = self._indicators['momentum_score'].calculate(df)
            df['momentum_score'] = result.values
        except Exception as e:
            logger.warning(f"Momentum score calculation failed: {e}")
    
    def _add_atr(self, df: pd.DataFrame) -> None:
        """Add ATR indicator."""
        try:
            result = self._indicators['atr'].calculate(df)
            df['atr'] = result.values
            df['atr_pct'] = result.metadata['atr_pct']
        except Exception as e:
            logger.warning(f"ATR calculation failed: {e}")
    
    def _add_bollinger_bands(self, df: pd.DataFrame) -> None:
        """Add Bollinger Bands."""
        try:
            result = self._indicators['bb'].calculate(df)
            meta = result.metadata
            df['bb_upper'] = meta['upper']
            df['bb_lower'] = meta['lower']
            df['bb_position'] = meta['position']
            df['bb_width'] = meta['bandwidth']
        except Exception as e:
            logger.warning(f"Bollinger Bands calculation failed: {e}")
    
    def _add_gap(self, df: pd.DataFrame) -> None:
        """Add gap analysis."""
        try:
            result = self._indicators['gap'].calculate(df)
            meta = result.metadata
            df['gap_pct'] = meta['gap_pct']
            df['gap_zscore'] = meta['gap_zscore']
        except Exception as e:
            logger.warning(f"Gap calculation failed: {e}")
    
    def _add_volume_ratio(self, df: pd.DataFrame) -> None:
        """Add volume ratio."""
        try:
            result = self._indicators['volume_ratio'].calculate(df)
            df['volume_ratio'] = result.values
        except Exception as e:
            logger.warning(f"Volume ratio calculation failed: {e}")
    
    def _add_volume_trend(self, df: pd.DataFrame) -> None:
        """Add volume trend."""
        try:
            result = self._indicators['volume_trend'].calculate(df)
            df['volume_trend'] = result.values
        except Exception as e:
            logger.warning(f"Volume trend calculation failed: {e}")


# Global instance
_indicator_engine: Optional[IndicatorEngine] = None


def get_indicator_engine() -> IndicatorEngine:
    """Get global indicator engine instance."""
    global _indicator_engine
    if _indicator_engine is None:
        _indicator_engine = IndicatorEngine()
    return _indicator_engine
