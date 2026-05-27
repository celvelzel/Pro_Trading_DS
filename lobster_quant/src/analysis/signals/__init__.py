"""
Lobster Quant - Signal System
"""

from .composite_signal import CompositeSignalGenerator, CompositeSignalResult
from .lobster_signal import SignalGenerator

__all__ = [
    "SignalGenerator",
    "CompositeSignalGenerator",
    "CompositeSignalResult",
]
