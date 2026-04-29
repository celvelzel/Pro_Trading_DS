"""
Lobster Quant - Backtest Metrics
Standalone metric calculation functions for backtest analysis.
"""

import numpy as np
import pandas as pd
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger()


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> float:
    """Calculate Sharpe ratio.

    Args:
        returns: Series of periodic returns
        risk_free_rate: Risk-free rate (annualized)
        annualize: Whether to annualize the ratio
        periods_per_year: Number of periods per year for annualization

    Returns:
        Sharpe ratio (float). Returns 0.0 for edge cases.
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return 0.0

    mean_return = returns.mean()
    std_return = returns.std()

    if std_return == 0 or np.isnan(std_return):
        return 0.0

    sharpe = (mean_return - risk_free_rate / periods_per_year) / std_return

    if annualize and len(returns) > 1:
        sharpe *= np.sqrt(periods_per_year)

    return float(sharpe)


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> float:
    """Calculate Sortino ratio using downside deviation.

    Args:
        returns: Series of periodic returns
        risk_free_rate: Risk-free rate (annualized)
        annualize: Whether to annualize the ratio
        periods_per_year: Number of periods per year for annualization

    Returns:
        Sortino ratio (float). Returns 0.0 for edge cases.
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return 0.0

    mean_return = returns.mean()
    downside = returns.apply(lambda r: min(r - risk_free_rate / periods_per_year, 0.0))
    downside_std = np.sqrt((downside ** 2).mean())

    if downside_std == 0 or np.isnan(downside_std):
        return 0.0

    sortino = (mean_return - risk_free_rate / periods_per_year) / downside_std

    if annualize and len(returns) > 1:
        sortino *= np.sqrt(periods_per_year)

    return float(sortino)


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Calculate maximum drawdown.

    Args:
        equity_curve: Series of equity values over time

    Returns:
        Maximum drawdown as positive decimal (e.g., 0.15 = 15%).
        Returns 0.0 for empty or monotonically increasing series.
    """
    equity_curve = equity_curve.dropna()
    if len(equity_curve) == 0:
        return 0.0

    running_max = equity_curve.cummax()
    drawdown = (running_max - equity_curve) / running_max
    max_dd = drawdown.max()

    if np.isnan(max_dd):
        return 0.0

    return float(max_dd)


def calculate_profit_factor(returns: pd.Series) -> float:
    """Calculate profit factor.

    Profit factor = sum of positive returns / abs(sum of negative returns).

    Args:
        returns: Series of periodic returns

    Returns:
        Profit factor. Returns float('inf') if no losses,
        0.0 if no profits or empty series.
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return 0.0

    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())

    if gross_loss == 0:
        if gross_profit > 0:
            return float('inf')
        return 0.0

    if gross_profit == 0:
        return 0.0

    return float(gross_profit / gross_loss)


def calculate_win_rate(returns: pd.Series) -> float:
    """Calculate win rate.

    Args:
        returns: Series of periodic returns

    Returns:
        Fraction of positive returns. Returns 0.0 for empty series.
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return 0.0

    wins = (returns > 0).sum()
    return float(wins / len(returns))
