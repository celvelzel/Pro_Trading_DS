import yfinance as yf
import pandas as pd
import numpy as np
from config import DATA_YEARS, is_a_stock, is_hk_stock
import akshare as ak

def fetch_stock_data(code):
    """获取股票历史数据，返回包含日线、周线、月线的字典"""
    if is_a_stock(code):
        return _fetch_a_stock(code)
    elif is_hk_stock(code):
        return _fetch_hk_stock(code)
    else:
        return _fetch_us_stock(code)

def _fetch_us_stock(symbol):
    """美股数据"""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{DATA_YEARS}y")
    if df.empty:
        return None
    df = df[['Open','High','Low','Close','Volume']]
    df.columns = ['open','high','low','close','volume']
    df.index = df.index.tz_localize(None)  # 去掉时区

    # 周线和月线重采样
    weekly = df.resample('W').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
    monthly = df.resample('ME').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
    return {'daily': df, 'weekly': weekly, 'monthly': monthly}

def _fetch_a_stock(code):
    """A股数据（使用akshare）"""
    # 适配akshare格式：如 '300308' -> 'sz300308' 或 'sh600...'
    if code.startswith('6'):
        sym = f"sh{code}"
    else:
        sym = f"sz{code}"
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20190101", end_date="20500101", adjust="qfq")
        if df.empty:
            return None
        df = df.rename(columns={
            '日期':'date', '开盘':'open', '收盘':'close', '最高':'high', '最低':'low', '成交量':'volume'
        })
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')[['open','high','low','close','volume']]
        df = df.astype(float)
        # 周线和月线
        weekly = df.resample('W').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        monthly = df.resample('ME').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        return {'daily': df, 'weekly': weekly, 'monthly': monthly}
    except Exception as e:
        print(f"A股数据获取失败 {code}: {e}")
        return None

def _fetch_hk_stock(code):
    """港股数据（使用yfinance，需添加.HK后缀）"""
    # 港股代码处理：5位数字直接加.HK，或已带.HK的直接使用
    if code.isdigit() and len(code) == 5:
        symbol = f"{code}.HK"
    elif code.endswith('.HK') or code.endswith('.hk'):
        symbol = code.upper()
    else:
        symbol = code

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{DATA_YEARS}y")
        if df.empty:
            return None
        df = df[['Open','High','Low','Close','Volume']]
        df.columns = ['open','high','low','close','volume']
        df.index = df.index.tz_localize(None)

        # 周线和月线重采样
        weekly = df.resample('W').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        monthly = df.resample('ME').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        return {'daily': df, 'weekly': weekly, 'monthly': monthly}
    except Exception as e:
        print(f"港股数据获取失败 {code}: {e}")
        return None

def fetch_benchmark():
    """获取基准数据（SPY）"""
    return fetch_stock_data("SPY")