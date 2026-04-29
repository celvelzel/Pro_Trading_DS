"""
Lobster Quant - Quant Tool Indicators
Standalone technical indicators for the quant tool page.
"""

from typing import Optional

import numpy as np
import pandas as pd

from src.utils.logging import get_logger

logger = get_logger()


def calc_atr_percent(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculate Average True Range as percentage of close price.

    Args:
        df: DataFrame with 'high', 'low', 'close' columns.
        window: ATR window period.

    Returns:
        Series of ATR% values.

    Raises:
        ValueError: If required columns are missing.
    """
    if df is None or df.empty:
        return pd.Series([], dtype=float)

    required_cols = ["high", "low", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    atr_percent = (atr / close) * 100

    return atr_percent


def calc_ma200_dist(df: pd.DataFrame) -> pd.Series:
    """Calculate distance from 200-day moving average as percentage.

    Args:
        df: DataFrame with 'close' column.

    Returns:
        Series of MA200 distance values in percent.

    Raises:
        ValueError: If required column is missing.
    """
    if df is None or df.empty:
        return pd.Series([], dtype=float)

    if "close" not in df.columns:
        raise ValueError("Missing required column: close")

    close = df["close"]
    ma200 = close.rolling(window=200).mean()
    ma200_dist = ((close - ma200) / ma200) * 100

    return ma200_dist


def calc_gap_percent(df: pd.DataFrame) -> pd.Series:
    """Calculate gap percentage from previous close to today's open.

    Args:
        df: DataFrame with 'open' and 'close' columns.

    Returns:
        Series of gap percent values.

    Raises:
        ValueError: If required columns are missing.
    """
    if df is None or df.empty:
        return pd.Series([], dtype=float)

    required_cols = ["open", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    open_price = df["open"]
    prev_close = df["close"].shift(1)
    gap_percent = ((open_price / prev_close) - 1) * 100

    return gap_percent


def calc_put_call_ratio(
    calls: list[dict], puts: list[dict]
) -> Optional[float]:
    """Calculate Put/Call ratio based on volume.

    Args:
        calls: List of call option dicts with 'volume' key.
        puts: List of put option dicts with 'volume' key.

    Returns:
        Put/call volume ratio, or None if call volume is zero/missing.
    """
    if not calls or not puts:
        return None

    total_call_volume = sum(c.get("volume") or 0 for c in calls)
    total_put_volume = sum(p.get("volume") or 0 for p in puts)

    if total_call_volume == 0:
        return None

    return total_put_volume / total_call_volume


def calc_max_pain(
    calls: list[dict],
    puts: list[dict],
    current_price: float = 100.0,
) -> Optional[float]:
    """Calculate max pain strike — the strike with minimum intrinsic value loss.

    Args:
        calls: List of call option dicts with 'strike' and 'openInterest' keys.
        puts: List of put option dicts with 'strike' and 'openInterest' keys.
        current_price: Current underlying price.

    Returns:
        Max pain strike price, or None if insufficient data.
    """
    if not calls or not puts:
        return None

    all_strikes: set[float] = set()
    has_oi = False
    for c in calls:
        if "strike" in c and c.get("openInterest") and c["openInterest"] > 0:
            all_strikes.add(c["strike"])
            has_oi = True
    for p in puts:
        if "strike" in p and p.get("openInterest") and p["openInterest"] > 0:
            all_strikes.add(p["strike"])
            has_oi = True

    if not has_oi or not all_strikes:
        return None

    min_loss = float("inf")
    max_pain_strike: Optional[float] = None

    for strike in all_strikes:
        put_loss = 0.0
        for p in puts:
            s = p.get("strike") or 0
            oi = p.get("openInterest") or 0
            intrinsic = max(0.0, s - current_price)
            put_loss += intrinsic * oi

        call_loss = 0.0
        for c in calls:
            s = c.get("strike") or 0
            oi = c.get("openInterest") or 0
            intrinsic = max(0.0, current_price - s)
            call_loss += intrinsic * oi

        total_loss = put_loss + call_loss

        if total_loss < min_loss:
            min_loss = total_loss
            max_pain_strike = strike

    return max_pain_strike


def find_support_resistance(
    calls: list[dict], puts: list[dict]
) -> Optional[tuple[float, float]]:
    """Find support and resistance levels based on open interest.

    Support = strike with highest put OI.
    Resistance = strike with highest call OI.

    Args:
        calls: List of call option dicts with 'strike' and 'openInterest'.
        puts: List of put option dicts with 'strike' and 'openInterest'.

    Returns:
        (support, resistance) tuple, or None if insufficient data.
    """
    if not puts or not calls:
        return None

    max_put_oi = 0
    support_strike: Optional[float] = None
    for p in puts:
        oi = p.get("openInterest", 0)
        if oi > max_put_oi:
            max_put_oi = oi
            support_strike = p.get("strike")

    max_call_oi = 0
    resistance_strike: Optional[float] = None
    for c in calls:
        oi = c.get("openInterest", 0)
        if oi > max_call_oi:
            max_call_oi = oi
            resistance_strike = c.get("strike")

    if support_strike is None or resistance_strike is None:
        return None

    return (support_strike, resistance_strike)