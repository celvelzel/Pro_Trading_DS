# ============================================================
# Pro_Trading_DS - 统一配置文件
# 整合自: quant_lobster + lobster_quant + quant_tool
# ============================================================

# ============================================================
# 一、市场开关
# ============================================================
ENABLE_MARKETS = {
    'a_stock': False,   # A股 - True启用，False关闭
    'hk_stock': True,   # 港股
    'us_stock': True,   # 美股
}

# ============================================================
# 二、数据源配置（统一管理）
# ============================================================
# quant_tool 数据源（单股分析用）
QUANT_TOOL_DATA_SOURCE = {
    'daily': 'yfinance',      # 日线数据
    'options': 'yfinance',    # 期权链数据
    'timeout': 10,            # API超时(秒)
    'cache_ttl': 3600,        # 缓存时间(秒)
}

# lobster_quant 数据源（多股扫描用）
DATA_SOURCE = {
    'a_stock': 'akshare',    # A股：akshare
    'hk_stock': 'yfinance',  # 港股：yfinance
    'us_stock': 'yfinance',  # 美股：yfinance
}

# 数据获取参数
DATA_YEARS = 3          # 拉取近3年日线
WEEKLY_COMPRESS = True  # 需要周线和月线数据

# ============================================================
# 三、股票池配置（统一标的）
# ============================================================
STOCK_LIST = [
    # -------- 美股 --------
    "MU", "WDC", "SNDK", "STX", "LRCX", "KLAC", "AMAT", "INTC",
    "SPY", "QQQ", "VTI", "TSLA", "GOOG", "EWJ", "IWM", "GLD", "EWY",
    "LITE", "COHR", "GLW", "XLE", "URA", "ICLN", "XLU",
    # -------- 港股 --------
    "03110.HK",
    "02800.HK",
    # -------- A股 --------
    # "300308",  # 中际旭创
    # "688981",  # 中芯国际
]

# 按市场分组的标的（用于龙虾扫描页面）
DEFAULT_UNIVERSE = {
    'a_stock': [],
    'hk_stock': [
        "03110.HK",
        "02800.HK",
    ],
    'us_stock': [
        "MU", "WDC", "SNDK", "STX", "LRCX", "KLAC", "AMAT", "INTC",
        "SPY", "QQQ", "VTI", "TSLA", "GOOG", "EWJ", "IWM", "GLD", "EWY",
        "LITE", "COHR", "GLW", "XLE", "URA", "ICLN", "XLU",
    ],
}

# ============================================================
# 四、市场识别规则
# ============================================================
def is_a_stock(code):
    """简单判断：6位数字或含.SZ/.SH"""
    if code.isdigit() and len(code) == 6:
        return True
    if code.endswith('.SZ') or code.endswith('.SH'):
        return True
    return False

def is_hk_stock(code):
    """港股判断：5位数字或以.HK结尾"""
    if code.isdigit() and len(code) == 5:
        return True
    if code.endswith('.HK') or code.endswith('.hk'):
        return True
    return False

# ============================================================
# 五、评分权重（lobster_quant 风格）
# ============================================================
SCORE_WEIGHTS = {
    "trend": 0.40,      # 趋势强度（日/周/月MA20斜率）
    "momentum": 0.20,   # 动量信号（RSI + 20日涨跌幅）
    "volume": 0.15,     # 成交量（量比）
    "pattern": 0.25,    # 技术形态（MACD金叉/MA多头/布林带）
}

# 评分权重（quant_lobster 风格）
SCORING_WEIGHTS = {
    'trend': 40,
    'momentum': 20,
    'volume': 15,
    'tech': 25,
}

# ============================================================
# 六、技术指标参数
# ============================================================
MA_SHORT = 20
MA_LONG = 200
RSI_PERIOD = 14
ATR_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2

# ============================================================
# 七、回测参数
# ============================================================
HOLDING_DAYS = 20       # 固定持仓周期
MIN_SCORE_FOR_ENTRY = 20  # 入场评分阈值
LOOKBACK_DAYS = 500      # 回测历史数据天数

# ============================================================
# 八、OFF Filter 风控参数（统一配置）
# ============================================================
OFF_FILTER = {
    # quant_lobster 风格
    'vix_threshold': 35.0,          # VIX阈值
    'spy_ma200_below': 1,
    'atr_pct_threshold': 0.10,       # ATR%/价格
    'gap_threshold': 0.08,          # Gap 阈值
    'min_volume_ratio': 0.05,       # 最小量比
    'earnings_days': 5,
    # lobster_quant 风格
    'atr_pct_threshold_2': 0.05,   # ATR% > 5% 则OFF
    'gap_std_threshold': 2.0,       # Gap > 2倍标准差
    'ma200_recovery_days': 60,
}

# lobster_quant 兼容别名
ATR_PCT_THRESHOLD = 0.05
GAP_STD_THRESHOLD = 2.0
MA200_RECOVERY_DAYS = 60

# ============================================================
# 九、大盘基准
# ============================================================
BENCHMARK = "SPY"   # 用于 OFF 过滤和市场对比
