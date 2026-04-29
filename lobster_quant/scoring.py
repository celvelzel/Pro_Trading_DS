import pandas as pd
import numpy as np
from config import SCORE_WEIGHTS

def compute_score(df, slope_wm=None):
    """
    df: 已计算技术指标的日线DataFrame，必须包含所需字段。
    slope_wm: 包含 slope_weekly, slope_monthly 的DataFrame，与df同索引。
    返回 0-100 的评分序列。
    """
    df = df.copy()
    if slope_wm is not None:
        df['slope_weekly'] = slope_wm['slope_weekly']
        df['slope_monthly'] = slope_wm['slope_monthly']

    # 1. 趋势强度 (40%) - 日/周/月斜率综合
    # 将斜率标准化到0-1区间（基于历史最大值，但简单使用排名百分位）
    for col in ['slope_daily', 'slope_weekly', 'slope_monthly']:
        if col in df.columns:
            # 用最近500天数据
            recent = df[col].dropna().iloc[-500:]
            if len(recent) > 0:
                pct = df[col].rank(pct=True)
                df[f'{col}_score'] = pct.fillna(0.5) * 40  # 满分40
            else:
                df[f'{col}_score'] = 20

    # 三线斜率平均
    if all(col+'_score' in df.columns for col in ['slope_daily','slope_weekly','slope_monthly']):
        df['trend_score'] = (df['slope_daily_score'] + df['slope_weekly_score'] + df['slope_monthly_score']) / 3
    else:
        df['trend_score'] = df['slope_daily_score']

    # 2. 动量信号 (20%)
    # RSI映射：RSI>70过热扣分，30-70中性，<30超卖高分（逆向）
    def rsi_to_score(rsi):
        if pd.isna(rsi): return 10
        if rsi < 30: return 20
        if rsi < 50: return 10 + (rsi-30)*0.5
        if rsi < 70: return 20 - (rsi-50)*0.5
        return max(0, 20 - (rsi-70))
    df['rsi_score'] = df['rsi'].apply(rsi_to_score)

    # 20日价格变化率百分位
    df['ret_20d'] = df['close'].pct_change(20)
    ret_pct = df['ret_20d'].dropna().iloc[-500:].rank(pct=True)
    df['ret_score'] = ret_pct.reindex(df.index, method='ffill').fillna(0.5) * 20
    df['momentum_score'] = (df['rsi_score'] + df['ret_score'])

    # 3. 成交量 (15%)
    # 量比>1.5加分，<0.8减分
    def vol_score(vr):
        if pd.isna(vr): return 7.5
        if vr > 1.5: return 15
        if vr < 0.8: return 5
        return 7.5 + (vr-0.8)*10.7
    df['volume_score'] = df['volume_ratio'].apply(vol_score)

    # 4. 技术形态 (25%)
    df['pattern_score'] = 0
    # MACD金叉 (+10)
    df['pattern_score'] += df['macd_golden'].shift(1).astype(bool).fillna(False).astype(int) * 10
    # MA多头排列 (+10)
    df['pattern_score'] += df['ma_bullish'].astype(int) * 10
    # 价格在布林带中轨上方 (+5)
    df['pattern_score'] += (df['bb_position'] > 0.5).astype(int) * 5

    # 总分
    df['score'] = df['trend_score'] * SCORE_WEIGHTS['trend'] + \
                  df['momentum_score'] * SCORE_WEIGHTS['momentum'] + \
                  df['volume_score'] * SCORE_WEIGHTS['volume'] + \
                  df['pattern_score'] * SCORE_WEIGHTS['pattern']

    # 将分数裁剪到0-100
    df['score'] = df['score'].clip(0, 100)
    return df['score']