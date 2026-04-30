"""
Lobster Quant - Signal System
"""

from .lobster_signal import SignalGenerator
from .composite_signal import CompositeSignalGenerator, CompositeSignalResult

__all__ = [
    "SignalGenerator",
    "CompositeSignalGenerator",
    "CompositeSignalResult",
]
