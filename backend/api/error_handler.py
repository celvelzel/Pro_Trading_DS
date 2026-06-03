"""
Error handler utilities for safe data fetching with explicit error reporting.

Instead of silently swallowing exceptions and returning default values
(which causes users to see misleading data like $0.00 prices), these
functions return structured (value, error) tuples for proper error handling.
"""

import functools
import logging
import uuid
from typing import Any, Callable, TypeVar, Union

from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DataFetchError(Exception):
    """Raised when an external data source (yfinance, etc.) fails."""

    def __init__(self, detail: str, source: str = "unknown"):
        self.detail = detail
        self.source = source
        super().__init__(detail)


def handle_data_errors(func: Callable) -> Callable:
    """Decorator that catches DataFetchError and returns a structured 503 response.

    Usage::

        @handle_data_errors
        def fetch_price(symbol: str) -> dict:
            ...

    On failure returns::

        {"error": {"code": "DATA_UNAVAILABLE", "detail": "...", "request_id": "..."}}
        with status 503.
    """

    import asyncio

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            request_id = str(uuid.uuid4())[:8]
            try:
                return await func(*args, **kwargs)
            except DataFetchError as e:
                logger.error(
                    f"[{request_id}] DataFetchError in {func.__name__}: {e.detail} "
                    f"(source={e.source})",
                    exc_info=True,
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "DATA_UNAVAILABLE",
                            "detail": e.detail,
                            "source": e.source,
                            "request_id": request_id,
                        }
                    },
                )
            except Exception as e:
                logger.error(
                    f"[{request_id}] Unexpected error in {func.__name__}: {e}",
                    exc_info=True,
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "DATA_UNAVAILABLE",
                            "detail": str(e),
                            "source": "unknown",
                            "request_id": request_id,
                        }
                    },
                )

        return async_wrapper
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            request_id = str(uuid.uuid4())[:8]
            try:
                return func(*args, **kwargs)
            except DataFetchError as e:
                logger.error(
                    f"[{request_id}] DataFetchError in {func.__name__}: {e.detail} "
                    f"(source={e.source})",
                    exc_info=True,
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "DATA_UNAVAILABLE",
                            "detail": e.detail,
                            "source": e.source,
                            "request_id": request_id,
                        }
                    },
                )
            except Exception as e:
                logger.error(
                    f"[{request_id}] Unexpected error in {func.__name__}: {e}",
                    exc_info=True,
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "DATA_UNAVAILABLE",
                            "detail": str(e),
                            "source": "unknown",
                            "request_id": request_id,
                        }
                    },
                )

        return sync_wrapper


def safe_get_price(symbol: str) -> tuple[Union[float, None], Union[str, None]]:
    """
    Get current stock price with explicit error handling.

    Returns:
        (price, None) on success
        (None, error_message) on failure
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine

        engine = get_data_engine()
        stock_data = engine.fetch_stock(symbol)
        if stock_data is None:
            return None, f"No data available for {symbol}"
        return float(stock_data.daily.iloc[-1]["close"]), None
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}", exc_info=True)
        return None, f"Failed to fetch price: {e}"


def safe_get_score(symbol: str) -> tuple[Union[float, None], Union[str, None]]:
    """
    Get current stock score with explicit error handling.

    Returns:
        (score, None) on success
        (None, error_message) on failure
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.analysis.signals import SignalGenerator

        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()

        stock_data = data_engine.fetch_stock(symbol)
        if stock_data is None:
            return None, f"No data available for {symbol}"

        df = indicator_engine.compute_all(stock_data.daily)
        generator = SignalGenerator()
        signal = generator.generate(df, symbol)
        return float(signal.score), None
    except Exception as e:
        logger.error(f"Failed to get score for {symbol}: {e}", exc_info=True)
        return None, f"Failed to fetch score: {e}"


def safe_get_signal_type(symbol: str) -> tuple[Union[str, None], Union[str, None]]:
    """
    Get current stock signal type with explicit error handling.

    Returns:
        (signal_type, None) on success
        (None, error_message) on failure
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.analysis.signals import SignalGenerator

        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()

        stock_data = data_engine.fetch_stock(symbol)
        if stock_data is None:
            return None, f"No data available for {symbol}"

        df = indicator_engine.compute_all(stock_data.daily)
        generator = SignalGenerator()
        signal = generator.generate(df, symbol)
        return str(signal.signal_type), None
    except Exception as e:
        logger.error(f"Failed to get signal type for {symbol}: {e}", exc_info=True)
        return None, f"Failed to fetch signal type: {e}"
