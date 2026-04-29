import pandas as pd
import numpy as np
from config import (MA_SHORT, MA_LONG, RSI_PERIOD, ATR_PERIOD,
                    MACD_FAST, MACD_SLOW, MACD_SIGNAL, BB_PERIOD, BB_STD)

def compute_indicators(df):
    """
    输入DataFrame必须包含列: open, high, low, close, volume
    返回增加技术指标的DataFrame
    """
    df = df.copy()
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    # 均线
    df['ma20'] = close.rolling(MA_SHORT).mean()
    df['ma200'] = close.rolling(MA_LONG).mean()

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(RSI_PERIOD).mean()
    avg_loss = loss.rolling(RSI_PERIOD).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    df['macd'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd'].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    # 金叉死叉信号
    df['macd_golden'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))

    # 布林带
    df['bb_mid'] = close.rolling(BB_PERIOD).mean()
    bb_std = close.rolling(BB_PERIOD).std()
    df['bb_upper'] = df['bb_mid'] + BB_STD * bb_std
    df['bb_lower'] = df['bb_mid'] - BB_STD * bb_std
    df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # ATR
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(ATR_PERIOD).mean()
    df['atr_pct'] = df['atr'] / close

    # 量比（5日均量比较）
    df['volume_ma5'] = volume.rolling(5).mean()
    df['volume_ratio'] = volume / df['volume_ma5']

    # MA多头排列
    df['ma_bullish'] = (close > df['ma20']) & (df['ma20'] > df['ma200'])

    # 日/周/月斜率（需要周月数据，这里只给日线，周月斜率在外部处理）
    # 这里暂用20日斜率近似日线趋势
    x = np.arange(len(df))
    # 简单的线性回归斜率
    def rolling_slope(series, window):
        return series.rolling(window).apply(lambda y: np.polyfit(np.arange(len(y)), y, 1)[0] if len(y)==window else np.nan, raw=True)
    df['slope_daily'] = rolling_slope(close, 20)

    return df

def compute_weekly_monthly_slopes(data_dict):
    """
    从日/周/月数据中计算各自MA20的斜率。
    返回包含 'slope_weekly', 'slope_monthly' 的DataFrame（以日线索引对齐）
    """
    daily = data_dict['daily']
    weekly = data_dict['weekly']
    monthly = data_dict['monthly']

    # 周线MA20和斜率
    weekly['ma20'] = weekly['close'].rolling(MA_SHORT).mean()
    weekly['slope'] = weekly['ma20'].rolling(MA_SHORT).apply(
        lambda y: np.polyfit(np.arange(len(y)), y, 1)[0] if len(y)==MA_SHORT else np.nan, raw=True
    )
    # 月线同样
    monthly['ma20'] = monthly['close'].rolling(MA_SHORT).mean()
    monthly['slope'] = monthly['ma20'].rolling(MA_SHORT).apply(
        lambda y: np.polyfit(np.arange(len(y)), y, 1)[0] if len(y)==MA_SHORT else np.nan, raw=True
    )

    # 将斜率重新索引到日线：每个日期对应最近一周/月斜率
    # 简单方法：前向填充
    daily_idx = daily.index
    slope_w = weekly['slope'].reindex(daily_idx, method='ffill')
    slope_m = monthly['slope'].reindex(daily_idx, method='ffill')

    result = pd.DataFrame({
        'slope_weekly': slope_w,
        'slope_monthly': slope_m
    }, index=daily_idx)
    return result