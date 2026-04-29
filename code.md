以下是可直接运行的“龙虾辅助决策”复刻版完整代码。按照你的要求，已移除期权模块，保留核心评分、回测、OFF过滤器及筛选器。你只需复制代码，按步骤运行，即可在浏览器中查看和使用。

---

## 一、项目文件结构
```
lobster_quant/
├── app.py            # Streamlit 主界面
├── config.py         # 参数与标的配置
├── data_fetcher.py   # 数据获取（支持美股/A股）
├── indicators.py     # 技术指标计算
├── scoring.py        # 多维度评分模型
├── backtest.py       # 回测引擎
├── off_filter.py     # OFF 过滤器逻辑
└── requirements.txt  # 依赖包
```

---

## 二、各模块完整代码

### 1. `requirements.txt`
```
streamlit>=1.25
pandas>=2.0
numpy>=1.24
yfinance>=0.2.18
pandas-ta>=0.3.14b
plotly>=5.15
akshare>=1.13
scikit-learn>=1.3
```

### 2. `config.py`
```python
# 股票池配置（根据你的标的修改）
STOCK_LIST = [
    # 美股（直接使用 yfinance 代码）
    "MU", "WDC", "SNDK", "STX", "LRCX", "KLAC", "AMAT", "INTC",
    # A股（使用标准代码，系统会自动处理）
    "300308",  # 中际旭创
    "601899",  # 紫金矿业
    "601318",  # 中国平安
    "688981",  # 中芯国际
]

# 市场类型识别规则
def is_a_stock(code):
    """简单判断：6位数字或含.SZ/.SH"""
    if code.isdigit() and len(code) == 6:
        return True
    if code.endswith('.SZ') or code.endswith('.SH'):
        return True
    return False

# 评分权重
SCORE_WEIGHTS = {
    "trend": 0.40,      # 趋势强度（日/周/月MA20斜率）
    "momentum": 0.20,   # 动量信号（RSI + 20日涨跌幅）
    "volume": 0.15,     # 成交量（量比）
    "pattern": 0.25,    # 技术形态（MACD金叉/MA多头/布林带）
}

# 技术指标参数
MA_SHORT = 20
MA_LONG = 200
RSI_PERIOD = 14
ATR_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2

# 数据获取参数
DATA_YEARS = 3          # 拉取近3年日线
WEEKLY_COMPRESS = True  # 需要周线和月线数据

# 回测参数
HOLDING_DAYS = 20       # 固定持仓周期
MIN_SCORE_FOR_ENTRY = 50  # 最低入场评分

# OFF 过滤器阈值
ATR_PCT_THRESHOLD = 0.05      # ATR(14)/收盘价 > 5% 则视为过高
GAP_STD_THRESHOLD = 2.0       # 开盘跳空幅度超过2倍标准差
MA200_RECOVERY_DAYS = 60      # 价格在MA200下方连续天数（简化）

# 大盘基准（用于OFF过滤和市场对比）
BENCHMARK = "SPY"   # 或 "000300" 对应沪深300
```

### 3. `data_fetcher.py`
```python
import yfinance as yf
import pandas as pd
import numpy as np
from config import DATA_YEARS, is_a_stock
import akshare as ak

def fetch_stock_data(code):
    """获取股票历史数据，返回包含日线、周线、月线的字典"""
    if is_a_stock(code):
        return _fetch_a_stock(code)
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

def fetch_benchmark():
    """获取基准数据（SPY）"""
    return fetch_stock_data("SPY")
```

### 4. `indicators.py`
```python
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
```

### 5. `scoring.py`
```python
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
    df['pattern_score'] += df['macd_golden'].shift(1).fillna(False).astype(int) * 10
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
```

### 6. `backtest.py`
```python
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
```

### 7. `off_filter.py`
```python
import pandas as pd
import numpy as np
from config import (ATR_PCT_THRESHOLD, GAP_STD_THRESHOLD,
                    MA200_RECOVERY_DAYS, BENCHMARK)
from data_fetcher import fetch_benchmark

def compute_off_filter(df_daily, benchmark_data=None):
    """
    返回每天是否为OFF状态，以及原因字典。
    """
    df = df_daily.copy()
    results = pd.DataFrame(index=df.index)
    results['is_off'] = False
    reasons = {
        'ATR过高': np.zeros(len(df), dtype=bool),
        'MA200恢复中': np.zeros(len(df), dtype=bool),
        'Gap过大': np.zeros(len(df), dtype=bool),
        '大盘风险': np.zeros(len(df), dtype=bool)
    }

    # 1. ATR%过高
    if 'atr_pct' in df.columns:
        atr_high = df['atr_pct'] > ATR_PCT_THRESHOLD
        reasons['ATR过高'] = atr_high
        results['is_off'] |= atr_high

    # 2. MA200恢复中（价格在MA200下方且MA200下降，或刚站上不久）
    if 'ma200' in df.columns and 'close' in df.columns:
        below_ma200 = df['close'] < df['ma200']
        ma200_falling = df['ma200'].diff() < 0
        ma200_recovery = below_ma200 & ma200_falling
        # 也可以检查之前是否长期低于MA200
        reasons['MA200恢复中'] = ma200_recovery
        results['is_off'] |= ma200_recovery

    # 3. Gap过大（今日开盘相对昨日收盘跳空超过2倍历史跳空标准差）
    df['prev_close'] = df['close'].shift(1)
    df['gap'] = (df['open'] - df['prev_close']) / df['prev_close']
    gap_std = df['gap'].rolling(60).std()
    large_gap = abs(df['gap']) > GAP_STD_THRESHOLD * gap_std
    reasons['Gap过大'] = large_gap
    results['is_off'] |= large_gap

    # 4. 大盘风险（基准指数MA50死叉或处于下跌趋势，这里简化：SPY的20日均线向下）
    if benchmark_data is not None:
        bench_df = benchmark_data['daily']
        bench_df['ma20'] = bench_df['close'].rolling(20).mean()
        bench_slope = bench_df['ma20'].diff()
        bench_risk = bench_slope < 0
        bench_risk = bench_risk.reindex(df.index, method='ffill').fillna(False)
        reasons['大盘风险'] = bench_risk
        results['is_off'] |= bench_risk

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
```

### 8. `app.py`（Streamlit 主程序）
```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

from config import STOCK_LIST, BENCHMARK, is_a_stock
from data_fetcher import fetch_stock_data, fetch_benchmark
from indicators import compute_indicators, compute_weekly_monthly_slopes
from scoring import compute_score
from backtest import run_backtest, backtest_summary
from off_filter import compute_off_filter, get_on_off_stats

st.set_page_config(layout="wide", page_title="龙虾辅助决策复刻版")

st.title("🦞 龙虾辅助决策量化工具")
st.caption("研究辅助，不构成投资建议 | 基于概率与OFF风控")

# 初始化缓存数据
@st.cache_data(ttl=3600)
def load_all_data():
    bar = st.progress(0, text="下载数据中...")
    bench = fetch_benchmark()
    stock_data = {}
    total = len(STOCK_LIST)
    for i, code in enumerate(STOCK_LIST):
        bar.progress((i+1)/total, text=f"处理 {code} ...")
        data = fetch_stock_data(code)
        if data is not None:
            # 计算日线指标
            daily = compute_indicators(data['daily'])
            # 周月斜率
            slopes = compute_weekly_monthly_slopes(data)
            # 评分
            score = compute_score(daily, slopes)
            # 存储
            stock_data[code] = {
                'daily': daily,
                'weekly': data['weekly'],
                'monthly': data['monthly'],
                'score': score,
                'slopes': slopes
            }
    bar.empty()
    return bench, stock_data

bench, stock_dict = load_all_data()

# 页面导航
tab1, tab2, tab3 = st.tabs(["📊 OFF 风控仪表盘", "🔍 股票筛选器", "📈 个股深度分析"])

# ========== 仪表盘 ==========
with tab1:
    st.header("OFF Filter 状态监控")
    st.markdown("不交易（OFF）本身是策略的一部分，以下展示系统选择“不参与”的时间统计。")

    # 汇总所有股票的OFF统计
    total_on_days = 0
    total_days = 0
    all_reasons = {}
    for code, d in stock_dict.items():
        off_res, reasons_dict = compute_off_filter(d['daily'], bench)
        stats = get_on_off_stats(d['daily'], off_res)
        total_on_days += stats['total_days'] - stats['off_days']
        total_days += stats['total_days']
        for r, count in stats['reasons'].items():
            all_reasons[r] = all_reasons.get(r, 0) + count

    on_pct = total_on_days / total_days * 100 if total_days else 0
    off_pct = 100 - on_pct

    col1, col2 = st.columns(2)
    col1.metric("ON（允许交易）", f"{on_pct:.1f}%")
    col2.metric("OFF（不交易）", f"{off_pct:.1f}%")

    if all_reasons:
        st.subheader("OFF 原因分布")
        reason_df = pd.DataFrame({
            '原因': list(all_reasons.keys()),
            '次数': list(all_reasons.values())
        }).sort_values('次数', ascending=False)
        st.bar_chart(reason_df.set_index('原因'))
    else:
        st.info("无OFF记录，市场环境良好。")

# ========== 筛选器 ==========
with tab2:
    st.header("股票筛选器")
    st.markdown("基于评分和信号筛选潜在机会，点击股票查看深度分析。")

    # 获取最新一日快照
    snapshot = []
    for code, d in stock_dict.items():
        daily = d['daily'].dropna(subset=['close','ma20','score'])
        if daily.empty:
            continue
        latest = daily.iloc[-1]
        score_val = d['score'].iloc[-1] if len(d['score']) > 0 else np.nan
        # RSI
        rsi_val = latest.get('rsi', np.nan)
        # 日/周/月斜率
        slope_d = latest.get('slope_daily', np.nan)
        slope_w = d['slopes']['slope_weekly'].iloc[-1] if len(d['slopes']) > 0 else np.nan
        slope_m = d['slopes']['slope_monthly'].iloc[-1] if len(d['slopes']) > 0 else np.nan
        # 信号标签
        tags = []
        if latest.get('ma_bullish', False):
            tags.append('MA多排')
        if latest.get('macd_golden', False):
            tags.append('MACD金叉')
        if latest.get('volume_ratio', 0) > 1.5:
            tags.append('放量')
        # 三线上涨（简化为三斜率>0）
        if slope_d > 0 and slope_w > 0 and slope_m > 0:
            tags.append('三线上涨')

        snapshot.append({
            '代码': code,
            '收盘价': round(latest['close'], 2),
            '评分': round(score_val, 1) if not pd.isna(score_val) else 0,
            '日斜率': f"{slope_d:.2f}" if not pd.isna(slope_d) else "N/A",
            '周斜率': f"{slope_w:.2f}" if not pd.isna(slope_w) else "N/A",
            '月斜率': f"{slope_m:.2f}" if not pd.isna(slope_m) else "N/A",
            'RSI': round(rsi_val, 1) if not pd.isna(rsi_val) else "N/A",
            '信号': ', '.join(tags)
        })

    df_snapshot = pd.DataFrame(snapshot)
    # 筛选条件
    st.sidebar.header("筛选条件")
    min_score = st.sidebar.slider("最低评分", 0, 100, 50)
    min_rsi = st.sidebar.slider("RSI 下限", 0, 100, 0)
    max_rsi = st.sidebar.slider("RSI 上限", 0, 100, 100)
    show_ma = st.sidebar.checkbox("仅MA多头排列")
    show_golden = st.sidebar.checkbox("仅MACD金叉")
    show_vol = st.sidebar.checkbox("仅放量")

    filtered = df_snapshot[df_snapshot['评分'] >= min_score]
    if show_ma:
        filtered = filtered[filtered['信号'].str.contains('MA多排', na=False)]
    if show_golden:
        filtered = filtered[filtered['信号'].str.contains('MACD金叉', na=False)]
    if show_vol:
        filtered = filtered[filtered['信号'].str.contains('放量', na=False)]
    # RSI过滤
    rsi_mask = pd.Series(True, index=filtered.index)
    if min_rsi > 0:
        rsi_mask &= filtered['RSI'].astype(float) >= min_rsi
    if max_rsi < 100:
        rsi_mask &= filtered['RSI'].astype(float) <= max_rsi
    filtered = filtered[rsi_mask]

    st.write(f"显示 {len(filtered)} / {len(df_snapshot)} 只股票")
    st.dataframe(filtered.set_index('代码'), use_container_width=True)

    if len(filtered) > 0:
        selected = st.selectbox("选择股票查看深度分析", filtered['代码'].tolist())
        if selected:
            st.session_state['selected_stock'] = selected
            st.experimental_rerun()

# ========== 个股深度分析 ==========
with tab3:
    if 'selected_stock' not in st.session_state:
        st.session_state['selected_stock'] = STOCK_LIST[0]
    code = st.selectbox("输入或选择股票代码", STOCK_LIST, key='stock_sel')
    if code != st.session_state['selected_stock']:
        st.session_state['selected_stock'] = code

    if code not in stock_dict:
        st.error(f"股票 {code} 数据不可用")
    else:
        stock = stock_dict[code]
        daily = stock['daily']
        score = stock['score']

        st.header(f"{code} - 深度分析")
        # 最新指标卡
        last = daily.iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("最新评分", f"{score.iloc[-1]:.1f}")
        col2.metric("RSI", f"{last.get('rsi', 0):.1f}")
        col3.metric("量比", f"{last.get('volume_ratio', 0):.2f}")

        # K线图
        st.subheader("K线图 & 技术指标")
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            vertical_spacing=0.02,
                            row_heights=[0.6, 0.2, 0.2])
        # 日K
        fig.add_trace(go.Candlestick(x=daily.index, open=daily['open'],
                                     high=daily['high'], low=daily['low'],
                                     close=daily['close'], name='K线'), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily.index, y=daily['ma20'], line=dict(color='orange', width=1), name='MA20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily.index, y=daily['ma200'], line=dict(color='blue', width=1), name='MA200'), row=1, col=1)
        # 布林带
        if 'bb_upper' in daily.columns:
            fig.add_trace(go.Scatter(x=daily.index, y=daily['bb_upper'], line=dict(color='gray', dash='dot'), name='BB上轨'), row=1, col=1)
            fig.add_trace(go.Scatter(x=daily.index, y=daily['bb_lower'], line=dict(color='gray', dash='dot'), name='BB下轨'), row=1, col=1)

        # 成交量
        colors = ['green' if daily['close'].iloc[i] >= daily['open'].iloc[i] else 'red' for i in range(len(daily))]
        fig.add_trace(go.Bar(x=daily.index, y=daily['volume'], marker_color=colors, name='成交量'), row=2, col=1)

        # MACD
        if 'macd' in daily.columns:
            fig.add_trace(go.Scatter(x=daily.index, y=daily['macd'], line=dict(color='blue', width=1), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=daily.index, y=daily['macd_signal'], line=dict(color='red', width=1), name='Signal'), row=3, col=1)
            # 柱状图
            colors_macd = ['green' if v > 0 else 'red' for v in daily['macd_hist']]
            fig.add_trace(go.Bar(x=daily.index, y=daily['macd_hist'], marker_color=colors_macd, name='MACD Hist'), row=3, col=1)

        fig.update_layout(height=800, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 回测表现
        st.subheader("历史回测表现 (固定持仓20日)")
        trades = run_backtest(daily, score)
        summary = backtest_summary(trades)
        if summary['trades'] > 0:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("交易次数", summary['trades'])
            c2.metric("胜率", f"{summary['win_rate']*100:.1f}%")
            c3.metric("平均收益", f"{summary['avg_return']*100:.2f}%")
            c4.metric("盈亏比", f"{summary['profit_factor']:.2f}")
            # 收益曲线
            if trades:
                cum_returns = [1]
                for t in trades:
                    cum_returns.append(cum_returns[-1] * (1 + t['return']))
                cum_df = pd.DataFrame({
                    '交易序号': range(len(cum_returns)),
                    '累计净值': cum_returns
                })
                st.line_chart(cum_df.set_index('交易序号'))
        else:
            st.warning("当前评分条件下没有历史交易记录。")

        # OFF过滤器状态
        st.subheader("OFF Filter 状态 (最近60天)")
        off_res, reasons = compute_off_filter(daily, bench)
        recent_off = off_res.iloc[-60:]
        off_count = recent_off['is_off'].sum()
        st.write(f"近60天中 OFF 天数: {off_count} / 60 ({off_count/60*100:.1f}%)")
        if off_count > 0:
            st.write("OFF 原因分布（最近）:")
            reason_counts = {r: recent_off[r].sum() for r in reasons if recent_off[r].sum()>0}
            st.bar_chart(pd.DataFrame({'原因': list(reason_counts.keys()), '次数': list(reason_counts.values())}).set_index('原因'))
```

---

## 三、如何搭建与运行

### 步骤1：准备环境
- 安装 **Python 3.9+**（推荐使用 Anaconda 或 venv）。
- 创建项目文件夹（如 `lobster_quant`），将上述代码保存为对应文件名。
- 在文件夹内打开终端，执行：
```bash
pip install -r requirements.txt
```

### 步骤2：导入你的标的
编辑 `config.py` 中的 `STOCK_LIST`，按格式添加你关注的股票代码：
```python
STOCK_LIST = [
    # 美股直接写代码
    "AAPL", "MSFT", "GOOGL",
    # A股写6位数字（系统自动识别）
    "600519",  # 贵州茅台
    "000858",  # 五粮液
]
```
支持混排，程序会自动通过 `yfinance`（美股）或 `akshare`（A股）获取数据。

### 步骤3：启动系统
在项目根目录下运行：
```bash
streamlit run app.py
```
出现类似 `Local URL: http://localhost:8501` 后，用浏览器打开该地址即可。

首次运行会下载所有股票3年的日线数据，请耐心等待进度条完成。后续再次运行会使用缓存（1小时有效）。

---

## 四、重要说明与使用建议

- **免责声明**：该工具仅为历史数据回测的**研究辅助**，所有信号、评分、回测结果均不代表未来表现，**不构成投资建议**。
- **OFF过滤器阈值**：你可以在 `config.py` 中调整 `ATR_PCT_THRESHOLD`、`GAP_STD_THRESHOLD` 等参数以适应自己的风险偏好。
- **评分模型**：当前权重和逻辑仿照截图设计，你可以根据回测反馈微调 `SCORE_WEIGHTS`。
- **数据更新**：A股使用 `akshare`，免费但有时不稳定；美股使用 `yfinance`。若遇连接问题，可考虑更换数据源或增加重试机制。
- **扩展方向**：后续可加入更多因子（如资金流向、新闻情绪）、优化持仓周期、增加动态止损等，代码结构已为此预留空间。

现在你就可以拥有一个属于自己的量化决策辅助工具了。运行中遇到任何问题，欢迎反馈调整。