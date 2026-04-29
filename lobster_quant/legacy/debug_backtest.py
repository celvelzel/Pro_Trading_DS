# -*- coding: utf-8 -*-
"""Debug backtest - why 0 trades?"""

import sys
sys.path.insert(0, ".")

from legacy.data_fetcher import fetch_stock_data, fetch_benchmark
from legacy.indicators import compute_indicators, compute_weekly_monthly_slopes
from legacy.scoring import compute_score

print("=== SPY score distribution ===")
spy = fetch_stock_data("SPY")
daily = compute_indicators(spy['daily'])
slopes = compute_weekly_monthly_slopes(spy)
score = compute_score(daily, slopes)

# Drop NA
valid = score.dropna()
print(f"Score range: {valid.min():.1f} - {valid.max():.1f}")
print(f"Score mean: {valid.mean():.1f}, median: {valid.median():.1f}")
print(f"Scores >= 50: {(valid >= 50).sum()} / {len(valid)}")
print(f"Scores >= 30: {(valid >= 30).sum()} / {len(valid)}")
print(f"Scores >= 20: {(valid >= 20).sum()} / {len(valid)}")

# Check entry signals for SPY
daily_valid = daily.dropna(subset=['close', 'ma20'])
df = daily_valid.copy()
df['score'] = score.reindex(daily_valid.index)
df['ma20_slope'] = df['ma20'].diff()
df['entry_signal'] = (
    (df['close'] > df['ma20']) &
    (df['ma20_slope'] > 0) &
    (df['score'] >= 50)
)
print(f"\nSPY entry signals (>=50): {df['entry_signal'].sum()}")
df['entry_signal30'] = (
    (df['close'] > df['ma20']) &
    (df['ma20_slope'] > 0) &
    (df['score'] >= 30)
)
print(f"SPY entry signals (>=30): {df['entry_signal30'].sum()}")
df['entry_signal20'] = (
    (df['close'] > df['ma20']) &
    (df['ma20_slope'] > 0) &
    (df['score'] >= 20)
)
print(f"SPY entry signals (>=20): {df['entry_signal20'].sum()}")

# Check condition breakdown
print(f"\n  close > ma20: {(df['close'] > df['ma20']).sum()} / {len(df)}")
print(f"  ma20_slope > 0: {(df['ma20_slope'] > 0).sum()} / {len(df)}")
print(f"  score >= 50: {(df['score'] >= 50).sum()} / {len(df)}")

print("\n=== TSLA score distribution ===")
tsla = fetch_stock_data("TSLA")
daily_t = compute_indicators(tsla['daily'])
slopes_t = compute_weekly_monthly_slopes(tsla)
score_t = compute_score(daily_t, slopes_t)
valid_t = score_t.dropna()
print(f"TSLA Score range: {valid_t.min():.1f} - {valid_t.max():.1f}")
print(f"TSLA Score mean: {valid_t.mean():.1f}, median: {valid_t.median():.1f}")
print(f"TSLA Scores >= 50: {(valid_t >= 50).sum()} / {len(valid_t)}")
print(f"TSLA Scores >= 30: {(valid_t >= 30).sum()} / {len(valid_t)}")

# Show top scores
print("\nTop 10 SPY scores:")
print(valid.nlargest(10).to_frame('score'))
print("\nTop 10 TSLA scores:")
print(valid_t.nlargest(10).to_frame('score'))