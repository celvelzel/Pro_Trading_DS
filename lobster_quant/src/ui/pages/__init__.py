"""
Lobster Quant - UI Pages
"""

from .dashboard import render_dashboard
from .scanner import render_scanner
from .analyzer import render_analyzer
from .backtest import render_backtest
from .settings import render_settings

__all__ = [
    "render_dashboard",
    "render_scanner",
    "render_analyzer",
    "render_backtest",
    "render_settings",
]
