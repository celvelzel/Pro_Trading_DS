import pandas as pd
import numpy as np
from legacy.config import (ATR_PCT_THRESHOLD, GAP_STD_THRESHOLD,
                    MA200_RECOVERY_DAYS, BENCHMARK)
from legacy.data_fetcher import fetch_benchmark

def compute_off_filter(df_daily, benchmark_data=None):
    """
    返回每天是否为OFF状态，以及原因字典。
    """
    df = df_daily.copy()
    results = pd.DataFrame(index=df.index)
    results['is_off'] = False
    results['ATR过高'] = np.zeros(len(df), dtype=bool)
    results['MA200恢复中'] = np.zeros(len(df), dtype=bool)
    results['Gap过大'] = np.zeros(len(df), dtype=bool)
    results['大盘风险'] = np.zeros(len(df), dtype=bool)
    reasons = {
        'ATR过高': results['ATR过高'],
        'MA200恢复中': results['MA200恢复中'],
        'Gap过大': results['Gap过大'],
        '大盘风险': results['大盘风险'],
    }

    # 1. ATR%过高
    if 'atr_pct' in df.columns:
        results['ATR过高'] = df['atr_pct'] > ATR_PCT_THRESHOLD
        results['is_off'] |= results['ATR过高']

    # 2. MA200恢复中
    if 'ma200' in df.columns and 'close' in df.columns:
        below_ma200 = df['close'] < df['ma200']
        ma200_falling = df['ma200'].diff() < 0
        results['MA200恢复中'] = below_ma200 & ma200_falling
        results['is_off'] |= results['MA200恢复中']

    # 3. Gap过大
    df['prev_close'] = df['close'].shift(1)
    df['gap'] = (df['open'] - df['prev_close']) / df['prev_close']
    gap_std = df['gap'].rolling(60).std()
    results['Gap过大'] = abs(df['gap']) > GAP_STD_THRESHOLD * gap_std
    results['is_off'] |= results['Gap过大']

    # 4. 大盘风险
    if benchmark_data is not None:
        bench_df = benchmark_data['daily']
        bench_df = bench_df.copy()
        bench_df['ma20'] = bench_df['close'].rolling(20).mean()
        bench_slope = bench_df['ma20'].diff()
        bench_risk = bench_slope < 0
        bench_risk = bench_risk.reindex(df.index, method='ffill').fillna(False)
        results['大盘风险'] = bench_risk.values
        results['is_off'] |= results['大盘风险']

    return results, reasons

def get_on_off_stats(df, off_results):
    """计算ON/OFF比例及原因分布"""
    total = len(off_results)
    off_days = off_results['is_off'].sum()
    stats = {
        'total_days': total,
        'off_days': off_days,
        'on_pct': (total - off_days) / total * 100,
        'off_pct': off_days / total * 100,
        'reasons': {}
    }
    # 原因分布
    off_mask = off_results['is_off']
    for reason, mask in off_results.iloc[:, 1:].items():  # 跳过is_off列
        count = (mask & off_mask).sum()
        if count > 0:
            stats['reasons'][reason] = count
    return stats