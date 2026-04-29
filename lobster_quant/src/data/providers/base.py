"""
Lobster Quant - Data Provider Base Class
Abstract base for all data sources with unified interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime
import pandas as pd

from src.data.models import StockData, OptionsData
from src.utils.exceptions import DataProviderError


class DataProvider(ABC):
    """Abstract base class for data providers."""
    
    def __init__(self, name: str, timeout: int = 10):
        self._name = name
        self._timeout = timeout
        self._last_health_check: Optional[datetime] = None
        self._health_status: bool = True
    
    @property
    def name(self) -> str:
        """Provider name."""
        return self._name
    
    @property
    def is_healthy(self) -> bool:
        """Check if provider is healthy."""
        return self._health_status
    
    @abstractmethod
    def fetch_daily(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV data.
        
        Args:
            symbol: Stock symbol
            years: Number of years of historical data
        
        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        pass
    
    @abstractmethod
    def fetch_weekly(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch weekly OHLCV data."""
        pass
    
    @abstractmethod
    def fetch_monthly(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch monthly OHLCV data."""
        pass
    
    def fetch_stock_data(self, symbol: str, years: int = 3) -> Optional[StockData]:
        """Fetch complete stock data with all timeframes.
        
        Args:
            symbol: Stock symbol
            years: Number of years of data
        
        Returns:
            StockData model or None if fetch fails
        """
        try:
            daily = self.fetch_daily(symbol, years)
            if daily is None or daily.empty:
                return None
            
            weekly = self.fetch_weekly(symbol, years)
            monthly = self.fetch_monthly(symbol, years)
            
            return StockData(
                symbol=symbol,
                daily=daily,
                weekly=weekly,
                monthly=monthly,
                source=self.name
            )
        except Exception as e:
            raise DataProviderError(f"Failed to fetch stock data for {symbol}: {e}")
    
    def fetch_options(self, symbol: str) -> Optional[OptionsData]:
        """Fetch options chain data.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            OptionsData model or None if not available
        """
        # Default implementation returns None
        # Override in providers that support options
        return None
    
    def health_check(self) -> bool:
        """Perform health check on provider.
        
        Returns:
            True if provider is healthy
        """
        self._last_health_check = datetime.now()
        try:
            # Try to fetch a well-known symbol
            test_data = self.fetch_daily("SPY", years=1)
            self._health_status = test_data is not None and not test_data.empty
        except Exception:
            self._health_status = False
        return self._health_status
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', healthy={self.is_healthy})"


class DataProviderFactory:
    """Factory for creating data provider instances."""
    
    _providers: dict[str, type[DataProvider]] = {}
    _instances: dict[str, DataProvider] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: type[DataProvider]) -> None:
        """Register a provider class.
        
        Args:
            name: Provider identifier
            provider_class: Provider class
        """
        cls._providers[name] = provider_class
    
    @classmethod
    def create(cls, name: str, **kwargs: Any) -> DataProvider:
        """Create a provider instance.
        
        Args:
            name: Provider identifier
            **kwargs: Provider constructor arguments
        
        Returns:
            Provider instance
        
        Raises:
            ValueError: If provider is not registered
        """
        if name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {name}. "
                f"Available: {list(cls._providers.keys())}"
            )
        
        # Return cached instance if available
        cache_key = f"{name}:{hash(str(kwargs))}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        instance = cls._providers[name](**kwargs)
        cls._instances[cache_key] = instance
        return instance
    
    @classmethod
    def get_available(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear provider instance cache."""
        cls._instances.clear()

