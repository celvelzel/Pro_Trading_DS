"""
Quant Tool 数据层模块
整合自 quant_tool/data_layer.py，适配 lobster_quant 配置
"""

import warnings
from typing import Any

import yfinance as yf
import pandas as pd
import numpy as np

from config import QUANT_TOOL_DATA_SOURCE

TIMEOUT = QUANT_TOOL_DATA_SOURCE.get('timeout', 10)


def _clean_value(value: Any) -> Any:
    """Clean a single value for JSON serialization."""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
    """Clean a dictionary record for JSON serialization."""
    return {k: _clean_value(v) for k, v in record.items()}


def fetch_daily_data(symbol: str, period: str = "1y") -> dict[str, Any]:
    """Fetch daily OHLCV data for a given symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MU").
        period: Time period to fetch (e.g., "1y", "6mo", "5d").
    
    Returns:
        Dictionary with keys: date, open, high, low, close, volume.
        Returns error dict {"error": "message"} on failure.
    """
    if not symbol or not symbol.strip():
        return {"error": "Symbol cannot be empty"}

    symbol = symbol.strip().upper()

    try:
        ticker = yf.Ticker(symbol)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            hist = ticker.history(period=period, timeout=TIMEOUT)

        if hist.empty:
            return {"error": f"No data available for symbol {symbol}"}

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in required_cols:
            if col not in hist.columns:
                return {"error": f"Missing column {col} in data for {symbol}"}

        if hist["Close"].isna().all():
            return {"error": f"No valid price data for symbol {symbol}"}

        result = {
            "date": hist.index.strftime("%Y-%m-%d").tolist(),
            "open": hist["Open"].tolist(),
            "high": hist["High"].tolist(),
            "low": hist["Low"].tolist(),
            "close": hist["Close"].tolist(),
            "volume": hist["Volume"].astype(int).tolist(),
        }

        return result

    except TimeoutError:
        return {"error": f"Timeout fetching data for {symbol}"}
    except Exception as e:
        return {"error": f"Failed to fetch data for {symbol}: {str(e)}"}


def fetch_option_chain(symbol: str) -> dict | None:
    """Fetch options chain for the nearest expiration date.
    
    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT").
    
    Returns:
        Dictionary with keys: expiration, calls, puts.
        Returns None if the symbol has no options available.
        Returns error dict {"error": "message"} on failure.
    """
    if not symbol or not symbol.strip():
        return {"error": "Symbol cannot be empty"}

    symbol = symbol.strip().upper()

    try:
        ticker = yf.Ticker(symbol)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            options_dates = ticker.options

        if not options_dates or len(options_dates) == 0:
            return None

        nearest_expiration = options_dates[0]
        opt_chain = ticker.option_chain(nearest_expiration)

        calls = opt_chain.calls
        puts = opt_chain.puts

        calls_list = [_clean_record(record) for record in calls.to_dict("records")] if not calls.empty else []
        puts_list = [_clean_record(record) for record in puts.to_dict("records")] if not puts.empty else []

        return {
            "expiration": nearest_expiration,
            "calls": calls_list,
            "puts": puts_list,
        }

    except TimeoutError:
        return {"error": f"Timeout fetching options for {symbol}"}
    except Exception as e:
        return {"error": f"Failed to fetch options for {symbol}: {str(e)}"}
