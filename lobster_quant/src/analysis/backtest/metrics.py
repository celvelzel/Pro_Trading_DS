"""
Lobster Quant - Backtest Metrics
Standalone metric calculation functions for backtest analysis.
"""

import numpy as np
import pandas as pd

from src.data.models import Trade
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
    downside_std = np.sqrt((downside**2).mean())

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
            return float("inf")
        return 0.0

    if gross_profit == 0:
        return 0.0

    return float(gross_profit / gross_loss)


def calculate_period_win_rate(returns: pd.Series) -> float:
    """Calculate win rate from periodic returns.

    Args:
        returns: Series of periodic returns

    Returns:
        Fraction of positive returns (0-1). Returns 0.0 for empty series.
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return 0.0

    wins = (returns > 0).sum()
    return float(wins / len(returns))


def calculate_win_rate(trades: list[Trade]) -> float:
    """Calculate win rate from trades.

    Args:
        trades: List of Trade objects

    Returns:
        Win rate as percentage (0-100)
    """
    if not trades:
        return 0.0

    winning = [t for t in trades if t.return_pct is not None and t.return_pct > 0]
    return len(winning) / len(trades) * 100


def calculate_profit_loss_ratio(trades: list[Trade]) -> float:
    """Calculate profit/loss ratio.

    Args:
        trades: List of Trade objects

    Returns:
        Profit/loss ratio (avg_win / abs(avg_loss))
    """
    if not trades:
        return 0.0

    winning = [t for t in trades if t.return_pct is not None and t.return_pct > 0]
    losing = [t for t in trades if t.return_pct is not None and t.return_pct <= 0]

    avg_win = (
        sum(t.return_pct for t in winning if t.return_pct is not None) / len(winning)
        if winning
        else 0.0
    )
    avg_loss = (
        sum(t.return_pct for t in losing if t.return_pct is not None) / len(losing)
        if losing
        else 0.0
    )

    return abs(avg_win / avg_loss) if avg_loss != 0 else 0.0


def calculate_monthly_returns(equity_curve: list[float], dates: list[str]) -> dict[str, float]:
    """Calculate monthly returns from equity curve.

    Args:
        equity_curve: List of equity values
        dates: List of date strings (YYYY-MM-DD)

    Returns:
        Dictionary of monthly returns {YYYY-MM: return%}
    """
    if len(equity_curve) < 2 or len(dates) < 2:
        return {}

    monthly = {}
    current_month = dates[0][:7]  # YYYY-MM
    month_start_equity = equity_curve[0]

    for i in range(1, len(dates)):
        month = dates[i][:7]

        if month != current_month:
            # Calculate return for previous month
            month_end_equity = equity_curve[i - 1]
            if month_start_equity > 0:
                ret = (month_end_equity - month_start_equity) / month_start_equity * 100
                monthly[current_month] = round(ret, 2)

            current_month = month
            month_start_equity = equity_curve[i]

    # Handle last month
    if month_start_equity > 0:
        ret = (equity_curve[-1] - month_start_equity) / month_start_equity * 100
        monthly[current_month] = round(ret, 2)

    return monthly


def calculate_yearly_returns(equity_curve: list[float], dates: list[str]) -> dict[str, float]:
    """Calculate yearly returns from equity curve.

    Args:
        equity_curve: List of equity values
        dates: List of date strings (YYYY-MM-DD)

    Returns:
        Dictionary of yearly returns {YYYY: return%}
    """
    if len(equity_curve) < 2 or len(dates) < 2:
        return {}

    yearly = {}
    current_year = dates[0][:4]
    year_start_equity = equity_curve[0]

    for i in range(1, len(dates)):
        year = dates[i][:4]

        if year != current_year:
            # Calculate return for previous year
            year_end_equity = equity_curve[i - 1]
            if year_start_equity > 0:
                ret = (year_end_equity - year_start_equity) / year_start_equity * 100
                yearly[current_year] = round(ret, 2)

            current_year = year
            year_start_equity = equity_curve[i]

    # Handle last year
    if year_start_equity > 0:
        ret = (equity_curve[-1] - year_start_equity) / year_start_equity * 100
        yearly[current_year] = round(ret, 2)

    return yearly


def calculate_rolling_metrics(returns: pd.Series, window: int = 22) -> dict[str, pd.Series]:
    """Calculate rolling window metrics.

    Args:
        returns: Series of periodic returns
        window: Rolling window size in periods (default: 22 = 1 month)

    Returns:
        Dictionary with rolling metrics:
        - rolling_return: Rolling cumulative return
        - rolling_volatility: Rolling annualized volatility
        - rolling_sharpe: Rolling Sharpe ratio
    """
    if len(returns) < window:
        return {
            "rolling_return": pd.Series(dtype=float),
            "rolling_volatility": pd.Series(dtype=float),
            "rolling_sharpe": pd.Series(dtype=float),
        }

    # Rolling cumulative return
    rolling_return = returns.rolling(window).apply(lambda x: (1 + x).prod() - 1, raw=True)

    # Rolling annualized volatility
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)

    # Rolling Sharpe ratio
    rolling_sharpe = returns.rolling(window).apply(
        lambda x: (x.mean() * 252) / (x.std() * np.sqrt(252)) if x.std() > 0 else 0, raw=True
    )

    return {
        "rolling_return": pd.Series(rolling_return),
        "rolling_volatility": pd.Series(rolling_vol),
        "rolling_sharpe": pd.Series(rolling_sharpe),
    }
