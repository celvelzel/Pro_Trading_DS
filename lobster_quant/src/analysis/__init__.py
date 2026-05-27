"""
Lobster Quant - Analysis Layer
"""

from .backtest import BacktestEngine
from .indicators import (
    Indicator,
    IndicatorRegistry,
    IndicatorResult,
    normalize_series,
    rolling_slope,
)
from .signals import SignalGenerator

__all__ = [
    "Indicator",
    "IndicatorResult",
    "IndicatorRegistry",
    "rolling_slope",
    "normalize_series",
    "SignalGenerator",
    "BacktestEngine",
]
