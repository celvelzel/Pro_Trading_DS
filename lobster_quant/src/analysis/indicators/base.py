"""
Lobster Quant - Indicator Base Classes
Abstract base for all technical indicators with registry pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from ...utils.logging import get_logger
from ...utils.exceptions import IndicatorError

logger = get_logger()


@dataclass
class IndicatorResult:
    """Result container for indicator calculations."""
    name: str
    values: pd.Series
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def last_value(self) -> Any:
        """Get the most recent value."""
        return self.values.iloc[-1] if not self.values.empty else None
    
    @property
    def is_valid(self) -> bool:
        """Check if result has valid data."""
        return not self.values.empty and not self.values.isna().all()


class Indicator(ABC):
    """Abstract base class for technical indicators.
    
    All indicators must implement:
    - name: Unique identifier
    - params: Configuration parameters
    - calculate(): Main computation logic
    - validate(): Input validation
    """
    
    name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, **kwargs):
        self.params.update(kwargs)
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """Calculate indicator values.
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            IndicatorResult with computed values
        """
        pass
    
    def validate(self, data: pd.DataFrame) -> bool:
        """Validate input data has required columns.
        
        Args:
            data: Input DataFrame
        
        Returns:
            True if valid
        
        Raises:
            IndicatorError: If validation fails
        """
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in data.columns]
        
        if missing:
            raise IndicatorError(
                self.name,
                f"Missing required columns: {missing}"
            )
        
        if len(data) < 20:
            raise IndicatorError(
                self.name,
                f"Insufficient data: {len(data)} rows (minimum 20)"
            )
        
        return True
    
    def __call__(self, data: pd.DataFrame) -> IndicatorResult:
        """Convenience method to calculate indicator."""
        self.validate(data)
        return self.calculate(data)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', params={self.params})"


class IndicatorRegistry:
    """Registry for indicator classes.
    
    Usage:
        @IndicatorRegistry.register
        class MyIndicator(Indicator):
            name = "my_indicator"
            ...
        
        # Later
        indicator = IndicatorRegistry.get("my_indicator")
    """
    
    _indicators: Dict[str, type[Indicator]] = {}
    
    @classmethod
    def register(cls, indicator_class: type[Indicator]) -> type[Indicator]:
        """Register an indicator class.
        
        Args:
            indicator_class: Indicator class to register
        
        Returns:
            The registered class (for decorator usage)
        """
        if not indicator_class.name:
            raise ValueError(f"Indicator class {indicator_class.__name__} must have a name")
        
        cls._indicators[indicator_class.name] = indicator_class
        logger.debug(f"Registered indicator: {indicator_class.name}")
        return indicator_class
    
    @classmethod
    def get(cls, name: str) -> type[Indicator]:
        """Get indicator class by name.
        
        Args:
            name: Indicator name
        
        Returns:
            Indicator class
        
        Raises:
            KeyError: If indicator not found
        """
        if name not in cls._indicators:
            raise KeyError(
                f"Indicator '{name}' not found. "
                f"Available: {list(cls._indicators.keys())}"
            )
        return cls._indicators[name]
    
    @classmethod
    def create(cls, name: str, **kwargs) -> Indicator:
        """Create indicator instance by name.
        
        Args:
            name: Indicator name
            **kwargs: Constructor arguments
        
        Returns:
            Indicator instance
        """
        indicator_class = cls.get(name)
        return indicator_class(**kwargs)
    
    @classmethod
    def list_indicators(cls) -> List[str]:
        """Get list of available indicator names."""
        return sorted(cls._indicators.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered indicators."""
        cls._indicators.clear()


# ============================================================
# Utility Functions
# ============================================================

def rolling_slope(series: pd.Series, window: int = 20) -> pd.Series:
    """Calculate rolling linear regression slope.
    
    Args:
        series: Price series
        window: Rolling window size
    
    Returns:
        Series of slope values
    """
    def _slope(y: np.ndarray) -> float:
        if len(y) < 2:
            return np.nan
        x = np.arange(len(y))
        return np.polyfit(x, y, 1)[0]
    
    return series.rolling(window=window, min_periods=window).apply(
        _slope, raw=True
    )


def normalize_series(series: pd.Series, method: str = "zscore") -> pd.Series:
    """Normalize a series.
    
    Args:
        series: Input series
        method: "zscore", "minmax", or "rank"
    
    Returns:
        Normalized series
    """
    if method == "zscore":
        return (series - series.mean()) / series.std()
    elif method == "minmax":
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(0.5, index=series.index)
        return (series - min_val) / (max_val - min_val)
    elif method == "rank":
        return series.rank(pct=True)
    else:
        raise ValueError(f"Unknown normalization method: {method}")
