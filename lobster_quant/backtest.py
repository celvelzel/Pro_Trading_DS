import pandas as pd
import numpy as np
from config import HOLDING_DAYS, MIN_SCORE_FOR_ENTRY

def run_backtest(df_daily, score_series):
    """
    基于评分和历史数据，固定持仓20日的回测。
    返回 list of dict：每笔交易的买入、卖出、收益。
    """
    df = df_daily.copy()
    df['score'] = score_series
    df = df.dropna(subset=['close', 'ma20', 'score'])

    # 入场条件：收盘价>MA20，MA20斜率>0，评分>=阈值
    df['ma20_slope'] = df['ma20'].diff()  # 简化为日变化量>0
    df['entry_signal'] = (
        (df['close'] > df['ma20']) &
        (df['ma20_slope'] > 0) &
        (df['score'] >= MIN_SCORE_FOR_ENTRY)
    )

    # 防止连续入场：持仓期间不产生新信号
    signals = df.index[df['entry_signal']].tolist()
    trades = []
    blocked_until = None
    for date in signals:
        if blocked_until is not None and date < blocked_until:
            continue
        # 寻找卖出日（持仓HOLDING_DAYS个交易日）
        idx_loc = df.index.get_loc(date)
        if idx_loc + HOLDING_DAYS < len(df):
            sell_date = df.index[idx_loc + HOLDING_DAYS]
        else:
            break  # 数据不够持仓周期
        buy_price = df.at[date, 'close']
        sell_price = df.at[sell_date, 'close']
        ret = (sell_price - buy_price) / buy_price
        trades.append({
            'buy_date': date,
            'buy_price': buy_price,
            'sell_date': sell_date,
            'sell_price': sell_price,
            'return': ret
        })
        blocked_until = sell_date

    return trades

def backtest_summary(trades):
    """计算胜率、盈亏比、平均收益等"""
    if not trades:
        return {'trades':0, 'win_rate':0, 'avg_return':0, 'profit_factor':0, 'best':0, 'worst':0}
    returns = [t['return'] for t in trades]
    win = [r for r in returns if r > 0]
    loss = [r for r in returns if r <= 0]
    win_rate = len(win) / len(returns) if returns else 0
    avg_win = np.mean(win) if win else 0
    avg_loss = np.mean(loss) if loss else 0
    profit_factor = (avg_win / abs(avg_loss)) if avg_loss != 0 else np.inf
    cum_ret = np.prod([1+r for r in returns]) - 1
    return {
        'trades': len(returns),
        'win_rate': win_rate,
        'avg_return': np.mean(returns),
        'profit_factor': profit_factor,
        'best': max(returns),
        'worst': min(returns),
        'cum_return': cum_ret
    }