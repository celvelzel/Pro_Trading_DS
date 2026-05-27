"""
Lobster Quant - Technical Indicators
All indicators are registered in the IndicatorRegistry.
"""

# Import to trigger registration
from . import momentum, trend, volatility, volume
from .base import (
    Indicator,
    IndicatorRegistry,
    IndicatorResult,
    normalize_series,
    rolling_slope,
)

__all__ = [
    "Indicator",
    "IndicatorResult",
    "IndicatorRegistry",
    "rolling_slope",
    "normalize_series",
]
