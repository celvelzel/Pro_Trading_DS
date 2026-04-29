"""
Lobster Quant - Technical Indicators
All indicators are registered in the IndicatorRegistry.
"""

from .base import (
    Indicator,
    IndicatorResult,
    IndicatorRegistry,
    rolling_slope,
    normalize_series,
)

# Import to trigger registration
from . import trend
from . import momentum
from . import volatility
from . import volume

__all__ = [
    "Indicator",
    "IndicatorResult",
    "IndicatorRegistry",
    "rolling_slope",
    "normalize_series",
]
