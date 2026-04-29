# -*- coding: utf-8 -*-
"""Final verification - backtest with threshold=20"""

import sys
sys.path.insert(0, ".")

import config
print(f"MIN_SCORE_FOR_ENTRY = {config.MIN_SCORE_FOR_ENTRY}")

from data_fetcher import fetch_stock_data
from indicators import compute_indicators, compute_weekly_monthly_slopes
from scoring import compute_score
from backtest import run_backtest, backtest_summary

print("\n=== SPY Backtest (threshold=20) ===")
spy = fetch_stock_data("SPY")
daily = compute_indicators(spy['daily'])
slopes = compute_weekly_monthly_slopes(spy)
score = compute_score(daily, slopes)
trades = run_backtest(daily, score)
summary = backtest_summary(trades)
print(f"Trades: {summary['trades']}")
print(f"Win rate: {summary['win_rate']*100:.1f}%")
print(f"Avg return: {summary['avg_return']*100:.2f}%")
print(f"Profit factor: {summary['profit_factor']:.2f}")
print(f"Cum return: {summary.get('cum_return', 0)*100:.1f}%")

print("\n=== TSLA Backtest ===")
tsla = fetch_stock_data("TSLA")
daily_t = compute_indicators(tsla['daily'])
slopes_t = compute_weekly_monthly_slopes(tsla)
score_t = compute_score(daily_t, slopes_t)
trades_t = run_backtest(daily_t, score_t)
summary_t = backtest_summary(trades_t)
print(f"Trades: {summary_t['trades']}")
print(f"Win rate: {summary_t['win_rate']*100:.1f}%")
print(f"Avg return: {summary_t['avg_return']*100:.2f}%")

# Show first 3 trades
print("\nFirst 3 SPY trades:")
for t in trades[:3]:
    print(f"  {t['buy_date'].date()} -> {t['sell_date'].date()}: {t['return']*100:.2f}%")