"""
龙虾 OFF Filter - 整合自 quant_lobster
支持 quant_lobster 风格的 OFF 判断逻辑
"""
import yfinance as yf
import pandas as pd
import numpy as np
from config import OFF_FILTER, is_a_stock, is_hk_stock


def _get_market(symbol):
    """根据代码识别市场"""
    if is_a_stock(symbol):
        return 'a_stock'
    elif is_hk_stock(symbol):
        return 'hk_stock'
    else:
        return 'us_stock'


def should_trade(symbol, df):
    """
    返回 (是否交易, OFF原因列表)
    quant_lobster 风格的 OFF Filter
    """
    market = _get_market(symbol)
    reasons = []

    # 1. VIX恐慌指数（仅美股）
    if market == 'us_stock':
        try:
            vix = yf.Ticker("^VIX").fast_info.last_price
            if vix > OFF_FILTER.get('vix_threshold', 35.0):
                reasons.append(f"VIX恐慌过高({vix:.1f})")
        except Exception:
            pass

    # 2. SPY指数趋势（美股大盘）
    if market == 'us_stock':
        try:
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="200d")
            if len(spy_hist) > 20:
                spy_close = spy_hist['Close']
                # 简化斜率计算
                if len(spy_close) >= 20:
                    x = np.arange(20)
                    y = spy_close.iloc[-20:].values
                    spy_slope = np.polyfit(x, y, 1)[0] / y[-1]
                    spy_ma200 = spy_close.rolling(200).mean().iloc[-1]
                    if spy_close.iloc[-1] < spy_ma200 and spy_slope < 0:
                        reasons.append("SPY MA200恢复中")
        except Exception:
            pass

    # 3. 个股ATR%过高
    if df is not None and len(df) > 20:
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_val = tr.rolling(14).mean().iloc[-1]
        price = df['close'].iloc[-1]
        atr_pct = atr_val / price
        if atr_pct > OFF_FILTER.get('atr_pct_threshold', 0.10):
            reasons.append(f"ATR%过高({atr_pct:.1%})")

    # 4. 跳空过大（今日开盘 vs 昨日收盘）
    if df is not None and len(df) >= 2:
        gap = (df['open'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
        if abs(gap) > OFF_FILTER.get('gap_threshold', 0.08):
            reasons.append(f"Gap过大({gap:.1%})")

    # 5. 流动性不足（量比过小）
    if df is not None and len(df) > 20:
        vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
        if vol_ratio < OFF_FILTER.get('min_volume_ratio', 0.05):
            reasons.append(f"流动性不足(量比{vol_ratio:.2f})")

    return len(reasons) == 0, reasons


def get_off_status_table(symbols, stock_dict):
    """
    批量扫描 OFF 状态，返回 DataFrame
    用于龙虾扫描页面展示
    """
    results = []
    for code in symbols:
        if code not in stock_dict:
            continue
        daily = stock_dict[code]['daily']
        if daily is None or len(daily) < 20:
            continue
        trade_ok, reasons = should_trade(code, daily)
        latest = daily.iloc[-1]
        results.append({
            'Code': code,
            'Status': 'ON ✅' if trade_ok else 'OFF ❌',
            'OFF Reasons': ', '.join(reasons) if reasons else '-',
        })
    return pd.DataFrame(results)
