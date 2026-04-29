"""
龙虾信号模块 - 整合自 quant_lobster
支持 quant_lobster 风格的多因子评分 + 信号生成
"""
import pandas as pd
import numpy as np
from config import SCORING_WEIGHTS


# ---- indicators 复用 lobster_quant 的实现 ----
def _ma(series, window):
    return series.rolling(window).mean()

def slope(series, window=20):
    """计算线性回归斜率，归一化"""
    if len(series) < window:
        return 0.0
    y = series.iloc[-window:].values
    x = np.arange(window)
    slope_val = np.polyfit(x, y, 1)[0]
    return slope_val / y[-1] if y[-1] != 0 else 0.0

def rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(close, fast=12, slow=26, signal=9):
    exp1 = close.ewm(span=fast, adjust=False).mean()
    exp2 = close.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def bollinger_bands(close, window=20, num_std=2):
    ma20 = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = ma20 + num_std * std
    lower = ma20 - num_std * std
    return upper, ma20, lower

def volume_ratio(df, window=20):
    avg_vol = df['volume'].rolling(window).mean()
    return df['volume'].iloc[-1] / avg_vol.iloc[-1] if len(df) > window else 1.0

def is_ma_bullish(df, short=20, long=50):
    ma_short = _ma(df['close'], short)
    ma_long = _ma(df['close'], long)
    return ma_short.iloc[-1] > ma_long.iloc[-1]


class SignalGenerator:
    """多因子评分 + 信号生成"""

    @staticmethod
    def calculate_probability_up(df, lookback=250):
        """基于历史统计的上涨概率"""
        if len(df) < lookback:
            return 50.0
        ret_20d = (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) if len(df) >= 21 else 0
        rsi_val = rsi(df['close']).iloc[-1]
        prob = 50 + (ret_20d * 100) * 0.3 + (rsi_val - 50) * 0.4
        return min(100, max(0, prob))

    @staticmethod
    def multi_period_trend(df_daily, df_weekly=None, df_monthly=None):
        """计算日/周/月三线MA20斜率"""
        daily_slope = slope(df_daily['close'], 20)
        weekly_slope = slope(df_weekly['close'], 20) if df_weekly is not None else daily_slope
        monthly_slope = slope(df_monthly['close'], 20) if df_monthly is not None else daily_slope
        all_positive = (daily_slope > 0) and (weekly_slope > 0) and (monthly_slope > 0)
        return all_positive, [daily_slope, weekly_slope, monthly_slope]

    @staticmethod
    def calculate_score(df, vol_ratio_val, config_weights):
        """完整评分系统，返回0-100分"""
        weights = config_weights

        # 趋势强度（40%）
        daily_slope = slope(df['close'], 20)
        norm_slope = max(0, min(100, (daily_slope + 0.03) / 0.06 * 100))
        trend_score = norm_slope * (weights['trend'] / 100)

        # 动量（20%）
        rsi_val = rsi(df['close']).iloc[-1]
        momentum_20d = (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) * 100 if len(df) >= 21 else 0
        rsi_score = max(0, min(100, (rsi_val - 30) / 40 * 100))
        momentum_score_val = max(0, min(100, (momentum_20d + 20) / 40 * 100))
        momentum_score = (rsi_score * 0.5 + momentum_score_val * 0.5) * (weights['momentum'] / 100)

        # 成交量（15%）
        vol_score = min(100, vol_ratio_val * 50) * (weights['volume'] / 100)

        # 技术形态（25%）
        tech_score = 0
        macd_line, signal_line, _ = macd(df['close'])
        if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
            tech_score += 10
        if is_ma_bullish(df):
            tech_score += 10
        upper, mid, lower = bollinger_bands(df['close'])
        if df['close'].iloc[-1] > mid.iloc[-1]:
            tech_score += 5
        tech_score = tech_score * (weights['tech'] / 25)

        total_score = trend_score + momentum_score + vol_score + tech_score
        return min(100, total_score)

    @staticmethod
    def get_signal(df, score, prob_up):
        """根据评分、上涨概率和技术形态输出信号"""
        daily_slope = slope(df['close'], 20)
        df_copy = df.set_index('date') if 'date' in df.columns else df.copy()
        try:
            weekly_slope = slope(df_copy['close'].resample('W').last(), 20) if len(df) >= 100 else daily_slope
            monthly_slope = slope(df_copy['close'].resample('ME').last(), 20) if len(df) >= 200 else daily_slope
        except Exception:
            weekly_slope = daily_slope
            monthly_slope = daily_slope

        three_up = (daily_slope > 0) and (weekly_slope > 0) and (monthly_slope > 0)
        ma_bull = is_ma_bullish(df)
        macd_line, signal_line, _ = macd(df['close'])
        macd_golden = (macd_line.iloc[-1] > signal_line.iloc[-1] and
                       macd_line.iloc[-2] <= signal_line.iloc[-2])

        if three_up and ma_bull and macd_golden and prob_up >= 60:
            return "强烈推荐", "MA多排+MACD金叉+三线上涨"
        elif ma_bull or macd_golden:
            return "推荐", "MA多头排列 或 MACD金叉"
        elif three_up and prob_up >= 50:
            return "持有", "三线上涨"
        elif daily_slope > 0:
            return "持有", "MA上升趋势"
        else:
            return "观望", ""
