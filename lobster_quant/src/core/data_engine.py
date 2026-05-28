"""
Lobster Quant - Data Engine
Unified data access layer with caching and async support.
"""

import asyncio
import time
from typing import Any

from ..config.settings import get_settings
from ..data.cache import DataCache
from ..data.circuit_breaker import CircuitBreakerConfig
from ..data.models import StockData
from ..data.provider_pool import FallbackChain
from ..data.providers.base import DataProvider, DataProviderFactory
from ..utils.logging import get_logger

logger = get_logger()


class DataEngine:
    """Unified data engine for all market data.

    Features:
        - Provider abstraction (yfinance, alpha_vantage, polygon, akshare, mock)
        - Priority-based fallback via FallbackChain
        - Per-provider circuit breaker protection
        - Persistent disk caching (parquet for DataFrames)
        - LRU memory cache with configurable size limit
        - Async batch fetching with concurrency control
        - Sliding-window provider metrics
    """

    def __init__(self, max_concurrent: int = 5):
        self.settings = get_settings()
        self.cache = DataCache(
            cache_dir=self.settings.data_cache_dir,
            default_ttl=self.settings.data_cache_ttl,
            max_memory_items=self.settings.data_cache_max_memory_items,
        )
        self.fallback_chains: dict[str, FallbackChain] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._initialize_provider_pools()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize_provider_pools(self) -> None:
        """Initialize data provider fallback chains based on configuration."""
        circuit_config = CircuitBreakerConfig(
            failure_threshold=self.settings.circuit_breaker_failure_threshold,
            recovery_timeout=self.settings.circuit_breaker_recovery_timeout,
        )

        if self.settings.enable_us_stock:
            chain = self._init_chain(
                "us_stock", self.settings.us_data_sources, circuit_config
            )
            self.fallback_chains["us_stock"] = chain

        if self.settings.enable_hk_stock:
            chain = self._init_chain(
                "hk_stock", self.settings.hk_data_sources, circuit_config
            )
            self.fallback_chains["hk_stock"] = chain

        if self.settings.enable_a_stock:
            chain = FallbackChain("a_stock")
            try:
                provider = DataProviderFactory.create(
                    self.settings.a_data_provider, timeout=self.settings.akshare_timeout
                )
                chain.add_provider(provider, priority=1)
            except Exception as e:
                logger.warning(f"Failed to initialize A-share provider: {e}")
            self.fallback_chains["a_stock"] = chain

    def _init_chain(
        self, market: str, sources_str: str, circuit_config: CircuitBreakerConfig
    ) -> FallbackChain:
        """Create a FallbackChain for a market from a comma-separated source list.

        Args:
            market: Market identifier (e.g., 'us_stock')
            sources_str: Comma-separated provider names
            circuit_config: Circuit breaker configuration

        Returns:
            Configured FallbackChain
        """
        chain = FallbackChain(market)
        sources = [s.strip() for s in sources_str.split(",")]
        for priority, source in enumerate(sources, start=1):
            try:
                provider = self._create_provider(source)
                if provider:
                    chain.add_provider(provider, priority)
            except Exception as e:
                logger.warning(f"Failed to initialize {market} provider {source}: {e}")
        logger.info(f"{market} provider chain: {', '.join(sources)}")
        return chain

    def _create_provider(self, source: str) -> DataProvider | None:
        """Create a data provider by name using per-provider timeout settings.

        Args:
            source: Provider name

        Returns:
            DataProvider instance, or None if not available
        """
        s = self.settings

        if source == "yfinance":
            return DataProviderFactory.create("yfinance", timeout=s.yfinance_timeout)
        elif source == "alpha_vantage":
            if not s.alpha_vantage_api_key:
                logger.warning("Alpha Vantage API key not configured, skipping")
                return None
            return DataProviderFactory.create(
                "alpha_vantage",
                api_key=s.alpha_vantage_api_key,
                timeout=s.alpha_vantage_timeout,
            )
        elif source == "polygon":
            if not s.polygon_api_key:
                logger.warning("Polygon API key not configured, skipping")
                return None
            return DataProviderFactory.create(
                "polygon", api_key=s.polygon_api_key, timeout=s.polygon_timeout
            )
        elif source == "mock":
            return DataProviderFactory.create("mock", timeout=s.data_timeout)
        else:
            logger.warning(f"Unknown provider: {source}")
            return None

    # ------------------------------------------------------------------
    # Market detection
    # ------------------------------------------------------------------

    @staticmethod
    def _get_market(symbol: str) -> str:
        """Determine market type from symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Market identifier string
        """
        if symbol.isdigit():
            if len(symbol) == 6:
                return "a_stock"
            elif len(symbol) == 5:
                return "hk_stock"

        upper = symbol.upper()
        if upper.endswith(".HK"):
            return "hk_stock"
        if upper.endswith(".SZ") or upper.endswith(".SH"):
            return "a_stock"

        return "us_stock"

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def fetch_stock(self, symbol: str, years: int | None = None) -> StockData | None:
        """Fetch complete stock data with caching and provider chain fallback.

        Args:
            symbol: Stock symbol
            years: Years of data (uses config default if None)

        Returns:
            StockData or None if fetch fails
        """
        years = years or self.settings.data_years
        market = self._get_market(symbol)
        cache_key = f"stock:{market}:{symbol}:{years}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for {symbol}")
            return cached

        # Get fallback chain
        chain = self.fallback_chains.get(market)
        if not chain:
            logger.error(f"No provider chain for market: {market}")
            return None

        # Try each provider in priority order
        for entry in chain.get_available_providers():
            try:
                start_time = time.time()
                stock_data = entry.provider.fetch_stock_data(symbol, years)
                response_time = time.time() - start_time

                if stock_data is not None and stock_data.daily is not None and not stock_data.daily.empty:
                    # Record success
                    entry.circuit_breaker.record_success()
                    entry.record_request(success=True, response_time=response_time)

                    self.cache.set(cache_key, stock_data)
                    logger.info(
                        f"Fetched {symbol} from {entry.provider.name} "
                        f"({len(stock_data.daily)} rows, {response_time:.2f}s)"
                    )
                    return stock_data
                else:
                    # No data returned — count as failure
                    entry.record_request(success=False, response_time=response_time)
                    logger.warning(f"Provider {entry.provider.name} returned empty data for {symbol}")

            except Exception as e:
                response_time = time.time() - start_time
                entry.circuit_breaker.record_failure()
                entry.record_request(success=False, response_time=response_time)
                logger.warning(f"Provider {entry.provider.name} failed for {symbol}: {e}")
                continue

        # All providers failed — try stale cache
        stale_cached = self.cache.get(cache_key)
        if stale_cached is not None:
            logger.warning(f"All providers failed for {symbol}, using stale cache")
            return stale_cached

        logger.error(f"No data available for {symbol} from any provider")
        return None

    # ------------------------------------------------------------------
    # Async support
    # ------------------------------------------------------------------

    async def fetch_stock_async(self, symbol: str, years: int | None = None) -> StockData | None:
        """Async version of fetch_stock with concurrency control."""
        async with self._semaphore:
            return await asyncio.to_thread(self.fetch_stock, symbol, years)

    async def fetch_batch(
        self, symbols: list[str], years: int | None = None
    ) -> dict[str, StockData | None]:
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
            for sym, res in zip(symbols, results, strict=False)
        }

    # ------------------------------------------------------------------
    # Benchmark
    # ------------------------------------------------------------------

    def fetch_benchmark(self, symbol: str | None = None) -> StockData | None:
        """Fetch benchmark data.

        Args:
            symbol: Benchmark symbol (uses config default if None)

        Returns:
            StockData or None
        """
        symbol = symbol or self.settings.benchmark_symbol
        return self.fetch_stock(symbol)

    # ------------------------------------------------------------------
    # Health & status
    # ------------------------------------------------------------------

    def get_health_status(self) -> dict[str, bool]:
        """Get health status of all providers.

        Returns:
            Dictionary mapping provider name to health status
        """
        result = {}
        for _, chain in self.fallback_chains.items():
            for entry in chain.get_available_providers():
                result[entry.provider.name] = entry.provider.health_check()
        return result

    def get_provider_status(self) -> dict[str, Any]:
        """Get status of all fallback chains with sliding-window metrics."""
        return {market: chain.get_provider_status() for market, chain in self.fallback_chains.items()}

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def clear_cache(self) -> int:
        """Clear all cached data.

        Returns:
            Number of items cleared
        """
        return self.cache.clear()

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()


# ------------------------------------------------------------------
# Global singleton
# ------------------------------------------------------------------

_data_engine: DataEngine | None = None


def get_data_engine() -> DataEngine:
    """Get global data engine instance (singleton)."""
    global _data_engine
    if _data_engine is None:
        _data_engine = DataEngine()
    return _data_engine


def reset_data_engine() -> None:
    """Reset the global data engine singleton.

    Useful for testing or when configuration changes require reinitialization.
    """
    global _data_engine
    _data_engine = None
