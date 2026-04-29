# -*- coding: utf-8 -*-
"""Quick test script for lobster_quant"""

import sys
sys.path.insert(0, ".")

import config
from data_fetcher import fetch_stock_data, fetch_benchmark
from indicators import compute_indicators, compute_weekly_monthly_slopes
from scoring import compute_score
from backtest import run_backtest, backtest_summary
from off_filter import compute_off_filter, get_on_off_stats

print("1. Testing config import...")
print(f"   STOCK_LIST has {len(config.STOCK_LIST)} stocks")

print("\n2. Testing fetch_benchmark (SPY)...")
try:
    bench = fetch_benchmark()
    print(f"   Benchmark shape: daily={bench['daily'].shape}, weekly={bench['weekly'].shape}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")

print("\n3. Testing fetch_stock_data (MU)...")
try:
    data = fetch_stock_data("MU")
    if data is not None:
        print(f"   MU shape: daily={data['daily'].shape}, weekly={data['weekly'].shape}")
    else:
        print("   MU returned None!")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")

print("\n4. Testing indicators...")
try:
    mu_data = fetch_stock_data("MU")
    if mu_data:
        daily = compute_indicators(mu_data['daily'])
        slopes = compute_weekly_monthly_slopes(mu_data)
        print(f"   indicators OK, slopes shape={slopes.shape}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")

print("\n5. Testing scoring...")
try:
    mu_data = fetch_stock_data("MU")
    if mu_data:
        daily = compute_indicators(mu_data['daily'])
        slopes = compute_weekly_monthly_slopes(mu_data)
        score = compute_score(daily, slopes)
        print(f"   scoring OK, score shape={score.shape}, last={score.iloc[-1]:.1f}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")

print("\n6. Testing off_filter (FIXED version)...")
try:
    mu_data = fetch_stock_data("MU")
    bench = fetch_benchmark()
    if mu_data and bench:
        daily = compute_indicators(mu_data['daily'])
        off_res, reasons = compute_off_filter(daily, bench)
        stats = get_on_off_stats(daily, off_res)
        print(f"   off_filter OK, ON={stats['on_pct']:.1f}%, OFF={stats['off_pct']:.1f}%")
        print(f"   reasons keys: {list(reasons.keys())}")
        print(f"   reasons stats: {stats['reasons']}")
        # Verify reasons dict columns match results DataFrame columns (except is_off)
        df_cols = set(off_res.columns) - {'is_off'}
        reason_keys = set(reasons.keys())
        if df_cols == reason_keys:
            print("   columns match: OK")
        else:
            print(f"   columns mismatch: df={df_cols}, reasons={reason_keys}")
except Exception as e:
    import traceback
    print(f"   ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()

print("\n7. Testing backtest...")
try:
    mu_data = fetch_stock_data("MU")
    if mu_data:
        daily = compute_indicators(mu_data['daily'])
        slopes = compute_weekly_monthly_slopes(mu_data)
        score = compute_score(daily, slopes)
        trades = run_backtest(daily, score)
        summary = backtest_summary(trades)
        print(f"   backtest OK, trades={summary['trades']}, win_rate={summary['win_rate']*100:.1f}%")
        if summary['trades'] == 0:
            print("   NOTE: 0 trades - score threshold may be too high, try with TSLA or SPY")
            # Try with SPY which has more data
            spy_data = fetch_stock_data("SPY")
            daily_spy = compute_indicators(spy_data['daily'])
            slopes_spy = compute_weekly_monthly_slopes(spy_data)
            score_spy = compute_score(daily_spy, slopes_spy)
            trades_spy = run_backtest(daily_spy, score_spy)
            summary_spy = backtest_summary(trades_spy)
            print(f"   SPY backtest: trades={summary_spy['trades']}, avg_return={summary_spy['avg_return']*100:.2f}%")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")

print("\n8. Testing Streamlit app import...")
try:
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    print("   streamlit/plotly OK")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")

print("\nAll tests done!")