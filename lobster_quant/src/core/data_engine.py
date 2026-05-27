"""
Lobster Quant - Data Engine
Unified data access layer with caching and async support.
"""

import asyncio
import time
from typing import Optional, Dict, List, Any
from datetime import datetime
import pandas as pd

from ..data.providers.base import DataProvider, DataProviderFactory
from ..data.cache import DataCache
from ..data.models import StockData
from ..data.provider_pool import ProviderPool
from ..data.circuit_breaker import CircuitBreakerConfig
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
        self.provider_pools: Dict[str, ProviderPool] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._initialize_provider_pools()
    
    def _initialize_provider_pools(self) -> None:
        """Initialize data provider pools based on configuration."""
        circuit_config = CircuitBreakerConfig(
            failure_threshold=self.settings.circuit_breaker_failure_threshold,
            recovery_timeout=self.settings.circuit_breaker_recovery_timeout
        )
        
        # US stocks
        if self.settings.enable_us_stock:
            pool = ProviderPool("us_stock")
            sources = [s.strip() for s in self.settings.us_data_sources.split(",")]
            for priority, source in enumerate(sources, start=1):
                try:
                    provider = self._create_provider(source, circuit_config)
                    if provider:
                        pool.add_provider(provider, priority)
                except Exception as e:
                    logger.warning(f"Failed to initialize US provider {source}: {e}")
            self.provider_pools['us_stock'] = pool
            logger.info(f"US stock provider pool: {', '.join(sources)}")
        
        # HK stocks
        if self.settings.enable_hk_stock:
            pool = ProviderPool("hk_stock")
            sources = [s.strip() for s in self.settings.hk_data_sources.split(",")]
            for priority, source in enumerate(sources, start=1):
                try:
                    provider = self._create_provider(source, circuit_config)
                    if provider:
                        pool.add_provider(provider, priority)
                except Exception as e:
                    logger.warning(f"Failed to initialize HK provider {source}: {e}")
            self.provider_pools['hk_stock'] = pool
            logger.info(f"HK stock provider pool: {', '.join(sources)}")
        
        # A-shares (single provider, no pool needed)
        if self.settings.enable_a_stock:
            pool = ProviderPool("a_stock")
            try:
                provider = DataProviderFactory.create(
                    self.settings.a_data_provider,
                    timeout=self.settings.data_timeout
                )
                pool.add_provider(provider, priority=1)
            except Exception as e:
                logger.warning(f"Failed to initialize A-share provider: {e}")
            self.provider_pools['a_stock'] = pool
    
    def _create_provider(self, source: str, circuit_config: CircuitBreakerConfig) -> Optional[DataProvider]:
        """Create a data provider by name."""
        if source == "yfinance":
            return DataProviderFactory.create("yfinance", timeout=self.settings.data_timeout)
        elif source == "alpha_vantage":
            if not self.settings.alpha_vantage_api_key:
                logger.warning("Alpha Vantage API key not configured, skipping")
                return None
            return DataProviderFactory.create(
                "alpha_vantage",
                api_key=self.settings.alpha_vantage_api_key,
                timeout=self.settings.data_timeout
            )
        elif source == "polygon":
            if not self.settings.polygon_api_key:
                logger.warning("Polygon API key not configured, skipping")
                return None
            return DataProviderFactory.create(
                "polygon",
                api_key=self.settings.polygon_api_key,
                timeout=self.settings.data_timeout
            )
        elif source == "mock":
            return DataProviderFactory.create("mock", timeout=self.settings.data_timeout)
        else:
            logger.warning(f"Unknown provider: {source}")
            return None
    
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
        """Get appropriate provider for symbol (backward compatibility)."""
        market = self._get_market(symbol)
        pool = self.provider_pools.get(market)
        if pool is None:
            return None
        available = pool.get_available_providers()
        if available:
            return available[0].provider
        return None
    
    def fetch_stock(self, symbol: str, years: Optional[int] = None) -> Optional[StockData]:
        """Fetch complete stock data with caching and provider pool fallback.
        
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
        
        # Get market and pool
        market = self._get_market(symbol)
        pool = self.provider_pools.get(market)
        
        if not pool:
            logger.error(f"No provider pool for market: {market}")
            return None
        
        # Try each provider in priority order
        for entry in pool.get_available_providers():
            try:
                start_time = time.time()
                result = entry.provider.fetch_daily(symbol, years)
                response_time = time.time() - start_time
                
                if result is not None and not result.empty:
                    # Record success
                    entry.circuit_breaker.record_success()
                    entry.success_count += 1
                    entry.avg_response_time = (
                        (entry.avg_response_time * (entry.success_count - 1) + response_time)
                        / entry.success_count
                    )
                    entry.last_used = datetime.now()
                    
                    # Build StockData
                    stock_data = entry.provider.fetch_stock_data(symbol, years)
                    if stock_data is not None:
                        self.cache.set(cache_key, stock_data)
                        logger.info(
                            f"Fetched {symbol} from {entry.provider.name} "
                            f"({len(result)} rows, {response_time:.2f}s)"
                        )
                        return stock_data
                    
            except Exception as e:
                entry.circuit_breaker.record_failure()
                entry.failure_count += 1
                logger.warning(
                    f"Provider {entry.provider.name} failed for {symbol}: {e}"
                )
                continue
        
        # All providers failed - try stale cache
        stale_cached = self.cache.get(cache_key)
        if stale_cached is not None:
            logger.warning(f"All providers failed for {symbol}, using stale cache")
            return stale_cached
        
        logger.error(f"No data available for {symbol} from any provider")
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
        result = {}
        for market, pool in self.provider_pools.items():
            for entry in pool.get_available_providers():
                result[entry.provider.name] = entry.provider.health_check()
        return result
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all provider pools."""
        return {
            market: pool.get_provider_status()
            for market, pool in self.provider_pools.items()
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
