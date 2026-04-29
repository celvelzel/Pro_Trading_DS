"""
Lobster Quant - Data Engine
Unified data access layer with caching and async support.
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime
import pandas as pd

from ..data.providers.base import DataProvider, DataProviderFactory
from ..data.cache import DataCache
from ..data.models import StockData
from ..config.settings import get_settings
from ..utils.logging import get_logger
from ..utils.exceptions import DataFetchError

logger = get_logger()


class DataEngine:
    """Unified data engine for all market data.
    
    Features:
    - Provider abstraction (yfinance, akshare, mock)
    - Persistent disk caching
    - Async batch fetching
    - Health monitoring
    """
    
    def __init__(self, max_concurrent: int = 5):
        self.settings = get_settings()
        self.cache = DataCache(
            cache_dir=self.settings.data_cache_dir,
            default_ttl=self.settings.data_cache_ttl
        )
        self.providers: Dict[str, DataProvider] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize data providers based on configuration."""
        # US stocks
        if self.settings.enable_us_stock:
            self.providers['us_stock'] = DataProviderFactory.create(
                self.settings.us_data_provider,
                timeout=self.settings.data_timeout
            )
            logger.info(f"US stock provider: {self.providers['us_stock'].name}")
        
        # HK stocks
        if self.settings.enable_hk_stock:
            self.providers['hk_stock'] = DataProviderFactory.create(
                self.settings.hk_data_provider,
                timeout=self.settings.data_timeout
            )
            logger.info(f"HK stock provider: {self.providers['hk_stock'].name}")
        
        # A-shares
        if self.settings.enable_a_stock:
            self.providers['a_stock'] = DataProviderFactory.create(
                self.settings.a_data_provider,
                timeout=self.settings.data_timeout
            )
            logger.info(f"A-share provider: {self.providers['a_stock'].name}")
    
    def _get_market(self, symbol: str) -> str:
        """Determine market type from symbol."""
        if symbol.isdigit():
            if len(symbol) == 6:
                return 'a_stock'
            elif len(symbol) == 5:
                return 'hk_stock'
        
        if symbol.endswith('.HK') or symbol.endswith('.hk'):
            return 'hk_stock'
        
        if symbol.endswith('.SZ') or symbol.endswith('.SH'):
            return 'a_stock'
        
        return 'us_stock'
    
    def _get_provider(self, symbol: str) -> Optional[DataProvider]:
        """Get appropriate provider for symbol."""
        market = self._get_market(symbol)
        return self.providers.get(market)
    
    def fetch_stock(self, symbol: str, years: Optional[int] = None) -> Optional[StockData]:
        """Fetch complete stock data with caching.
        
        Args:
            symbol: Stock symbol
            years: Years of data (uses config default if None)
        
        Returns:
            StockData or None if fetch fails
        """
        years = years or self.settings.data_years
        cache_key = f"stock:{symbol}:{years}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for {symbol}")
            return cached
        
        # Fetch from provider
        provider = self._get_provider(symbol)
        if provider is None:
            logger.error(f"No provider available for {symbol}")
            return None
        
        try:
            data = provider.fetch_stock_data(symbol, years)
            if data is not None:
                self.cache.set(cache_key, data)
                logger.info(f"Fetched and cached {symbol} ({len(data.daily)} rows)")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            return None
    
    async def fetch_stock_async(self, symbol: str, years: Optional[int] = None) -> Optional[StockData]:
        """Async version of fetch_stock with concurrency control."""
        async with self._semaphore:
            return await asyncio.to_thread(self.fetch_stock, symbol, years)
    
    async def fetch_batch(self, symbols: List[str], years: Optional[int] = None) -> Dict[str, Optional[StockData]]:
        """Fetch multiple stocks concurrently.
        
        Args:
            symbols: List of stock symbols
            years: Years of data
        
        Returns:
            Dictionary mapping symbol to StockData (or None)
        """
        tasks = [self.fetch_stock_async(sym, years) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            sym: res if not isinstance(res, Exception) else None
            for sym, res in zip(symbols, results)
        }
    
    def fetch_benchmark(self, symbol: Optional[str] = None) -> Optional[StockData]:
        """Fetch benchmark data.
        
        Args:
            symbol: Benchmark symbol (uses config default if None)
        
        Returns:
            StockData or None
        """
        symbol = symbol or self.settings.benchmark_symbol
        return self.fetch_stock(symbol)
    
    def get_health_status(self) -> Dict[str, bool]:
        """Get health status of all providers.
        
        Returns:
            Dictionary mapping provider name to health status
        """
        return {
            name: provider.health_check()
            for name, provider in self.providers.items()
        }
    
    def clear_cache(self) -> int:
        """Clear all cached data.
        
        Returns:
            Number of items cleared
        """
        return self.cache.clear()
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()


# Global data engine instance
_data_engine: Optional[DataEngine] = None


def get_data_engine() -> DataEngine:
    """Get global data engine instance (singleton)."""
    global _data_engine
    if _data_engine is None:
        _data_engine = DataEngine()
    return _data_engine
