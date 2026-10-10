"""Pure date-aligned portfolio risk calculations; no provider or storage access."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, localcontext
from math import sqrt, isfinite
from statistics import mean, stdev
from typing import Mapping


def decimal_value(value: object, *, positive: bool = False) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError("Expected finite nonnegative value" if not positive else "Expected finite positive value")
    return result


def align_prices(histories: Mapping[str, Mapping[date, object]]) -> tuple[list[date], dict[str, list[Decimal]], int]:
    if not histories or any(len(history) < 2 for history in histories.values()):
        raise ValueError("At least two price observations per asset required")
    for history in histories.values():
        if any(not isinstance(day, date) for day in history):
            raise ValueError("Price keys must be dates")
        for price in history.values():
            decimal_value(price, positive=True)
    days = sorted(set.intersection(*(set(h) for h in histories.values())))
    if len(days) < 2:
        raise ValueError("Fewer than two common trading dates")
    dropped = len(set.union(*(set(h) for h in histories.values()))) - len(days)
    return days, {s: [decimal_value(h[d], positive=True) for d in days] for s, h in histories.items()}, dropped


class PortfolioRiskAnalyzer:
    """Constant-current-weight historical proxy; sample annualized volatility.

    Monetary valuation uses Decimal precision 28; statistical outputs use binary64.
    Historical returns do not reconstruct historical holdings or predict returns.
    """

    def analyze(self, market_values: Mapping[str, object], cash: object,
                histories: Mapping[str, Mapping[date, object]], periods_per_year: int = 252) -> dict:
        if not 1 <= periods_per_year <= 366:
            raise ValueError("Invalid annualization frequency")
        values = {s: decimal_value(v) for s, v in market_values.items()}
        if "CASH" in values:
            raise ValueError("CASH is reserved")
        cash_value = decimal_value(cash)
        with localcontext() as ctx:
            ctx.prec = 28
            total = sum(values.values(), cash_value)
            if total <= 0:
                raise ValueError("Portfolio total must be positive")
            weights = {s: v / total for s, v in values.items()}
            weights["CASH"] = cash_value / total
        active = {s for s, v in values.items() if v > 0}
        warnings = []
        concentration = max((weights[s] for s in active), default=Decimal(0))
        if concentration > Decimal("0.5"):
            warnings.append("high_single_asset_concentration")
        if not active:
            return dict(weights=weights, total_value=total, concentration=concentration,
                        cash_weight=weights["CASH"], annualized_volatility=0.0, max_drawdown=0.0,
                        correlations={}, dates=[], observations=0, warnings=warnings)
        if not active.issubset(histories):
            raise ValueError("Missing history for held asset")
        days, prices, dropped = align_prices({s: histories[s] for s in sorted(active)})
        if dropped:
            warnings.append("noncommon_dates_excluded")
        returns = {s: [float(p[i] / p[i-1] - 1) for i in range(1, len(p))] for s, p in prices.items()}
        portfolio = [sum(float(weights[s]) * returns[s][i] for s in returns) for i in range(len(days)-1)]
        volatility = stdev(portfolio) * sqrt(periods_per_year) if len(portfolio) >= 2 else None
        if volatility is None:
            warnings.append("insufficient_returns_for_sample_volatility")
        nav = peak = 1.0
        drawdown = 0.0
        for change in portfolio:
            nav *= 1 + change
            peak = max(peak, nav)
            drawdown = max(drawdown, 1 - nav / peak)
        correlations = {}
        symbols = sorted(returns)
        for i, left in enumerate(symbols):
            for right in symbols[i+1:]:
                x, y = returns[left], returns[right]
                sx = stdev(x) if len(x) >= 2 else 0
                sy = stdev(y) if len(y) >= 2 else 0
                key = left + "|" + right
                correlations[key] = (sum((a-mean(x))*(b-mean(y)) for a,b in zip(x,y)) / ((len(x)-1)*sx*sy)) if sx and sy else None
                if correlations[key] is None:
                    warnings.append("undefined_correlation:" + key)
                elif correlations[key] > 0.8:
                    warnings.append("high_correlation:" + key)
        if not all(isfinite(x) for x in portfolio) or not isfinite(drawdown) or (volatility is not None and not isfinite(volatility)):
            raise ValueError("Nonfinite statistical result")
        return dict(weights=weights, total_value=total, concentration=concentration,
                    cash_weight=weights["CASH"], annualized_volatility=volatility, max_drawdown=drawdown,
                    correlations=correlations, dates=days, observations=len(portfolio), warnings=warnings)
