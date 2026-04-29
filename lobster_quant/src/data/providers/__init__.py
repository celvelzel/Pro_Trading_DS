"""
Lobster Quant - Data Providers
"""

from .base import DataProvider, DataProviderFactory
from .yfinance_provider import YFinanceProvider, _register as _yfinance_register
from .akshare_provider import AkShareProvider, _register as _akshare_register
from .mock_provider import MockProvider, _register as _mock_register

# Register all providers lazily on import
_yfinance_register()
_akshare_register()
_mock_register()

__all__ = [
    "DataProvider",
    "DataProviderFactory",
    "YFinanceProvider",
    "AkShareProvider",
    "MockProvider",
]