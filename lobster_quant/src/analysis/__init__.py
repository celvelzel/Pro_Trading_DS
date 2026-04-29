"""
Lobster Quant - Analysis Layer
"""

from .indicators import (
    Indicator,
    IndicatorResult,
    IndicatorRegistry,
    rolling_slope,
    normalize_series,
)
from .signals import SignalGenerator
from .backtest import BacktestEngine

__all__ = [
    "Indicator",
    "IndicatorResult",
    "IndicatorRegistry",
    "rolling_slope",
    "normalize_series",
    "SignalGenerator",
    "BacktestEngine",
]
