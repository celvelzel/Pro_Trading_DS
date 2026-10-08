"""Deterministic price/volume facts; no causal inference or model arithmetic."""
from __future__ import annotations

from math import isfinite
from typing import Sequence


def calculate_market_anomaly(dates: Sequence[str], closes: Sequence[float], volumes: Sequence[float], benchmark_dates: Sequence[str] = (), benchmark_closes: Sequence[float] = ()) -> dict:
    if len(dates) != len(closes) or len(closes) != len(volumes) or len(set(dates)) != len(dates) or list(dates) != sorted(dates):
        raise ValueError("Unique sorted dates and aligned OHLCV are required")
    if any(not isfinite(x) or x <= 0 for x in closes) or any(not isfinite(x) or x < 0 for x in volumes):
        raise ValueError("Finite positive closes and nonnegative volumes required")
    if len(benchmark_dates) != len(benchmark_closes) or len(set(benchmark_dates)) != len(benchmark_dates) or any(not isfinite(x) or x <= 0 for x in benchmark_closes):
        raise ValueError("Invalid benchmark")
    result = {"return_pct": None, "volume_ratio_20": None, "excess_return_pct": None, "relative_strength": None, "limitations": []}
    if len(closes) < 2:
        result["limitations"].append("At least two bars required for return")
        return result
    ret = closes[-1] / closes[-2] - 1
    result["return_pct"] = ret * 100
    if len(volumes) >= 21:
        mean = sum(volumes[-21:-1]) / 20
        if mean > 0:
            result["volume_ratio_20"] = volumes[-1] / mean
        else:
            result["limitations"].append("Prior twenty-session mean volume is zero")
    else:
        result["limitations"].append("Twenty prior sessions required for volume ratio")
    benchmark = dict(zip(benchmark_dates, benchmark_closes))
    if dates[-2] in benchmark and dates[-1] in benchmark:
        bret = benchmark[dates[-1]] / benchmark[dates[-2]] - 1
        result["excess_return_pct"] = (ret - bret) * 100
        result["relative_strength"] = (1 + ret) / (1 + bret) - 1
    else:
        result["limitations"].append("Benchmark missing the same two session dates")
    return result
