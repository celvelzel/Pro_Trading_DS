"""
Static stock symbol → company name mapping.

Covers major US, HK, and A-share stocks. Uses yfinance naming convention
(e.g., "0700.HK" not "0700").

This avoids runtime API calls for name resolution, keeping lookups fast
and deterministic.
"""

STOCK_NAME_MAP: dict[str, str] = {
    # ── US Stocks ──────────────────────────────────────────────────────────
    "AAPL": "Apple Inc.",
    "AMZN": "Amazon.com Inc.",
    "COHR": "Coherent Corp.",
    "GLW": "Corning Inc.",
    "GOOG": "Alphabet Inc.",
    "ICLN": "iShares Global Clean Energy ETF",
    "LITE": "Lumentum Holdings Inc.",
    "MU": "Micron Technology Inc.",
    "QQQ": "Invesco QQQ Trust",
    "SPY": "SPDR S&P 500 ETF Trust",
    "TSLA": "Tesla Inc.",
    "URA": "Global X Uranium ETF",
    "VTI": "Vanguard Total Stock Market ETF",
    "XLE": "Energy Select Sector SPDR Fund",
    "XLU": "Utilities Select Sector SPDR Fund",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "META": "Meta Platforms Inc.",
    "BRK.B": "Berkshire Hathaway Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "JNJ": "Johnson & Johnson",
    "WMT": "Walmart Inc.",
    "PG": "Procter & Gamble Co.",
    "MA": "Mastercard Inc.",
    "UNH": "UnitedHealth Group Inc.",
    "HD": "The Home Depot Inc.",
    "DIS": "The Walt Disney Company",
    "BAC": "Bank of America Corporation",
    "XOM": "Exxon Mobil Corporation",
    "PFE": "Pfizer Inc.",
    "COST": "Costco Wholesale Corporation",
    "NFLX": "Netflix Inc.",
    "CRM": "Salesforce Inc.",
    "AMD": "Advanced Micro Devices Inc.",
    "INTC": "Intel Corporation",
    "PYPL": "PayPal Holdings Inc.",
    "NKE": "Nike Inc.",
    "T": "AT&T Inc.",
    "BA": "The Boeing Company",
    "CAT": "Caterpillar Inc.",
    "GS": "The Goldman Sachs Group Inc.",
    "IBM": "International Business Machines Corporation",
    "GE": "GE Aerospace",
    "MMM": "3M Company",
    "F": "Ford Motor Company",
    "GM": "General Motors Company",
    "UBER": "Uber Technologies Inc.",
    "ABNB": "Airbnb Inc.",
    "SQ": "Block Inc.",
    "SHOP": "Shopify Inc.",
    "ZM": "Zoom Communications Inc.",
    "PLTR": "Palantir Technologies Inc.",
    "COIN": "Coinbase Global Inc.",
    "ARM": "Arm Holdings plc",
    "SMCI": "Super Micro Computer Inc.",
    "CRWD": "CrowdStrike Holdings Inc.",
    "SNOW": "Snowflake Inc.",
    "LLY": "Eli Lilly and Company",
    "AVGO": "Broadcom Inc.",
    "ORCL": "Oracle Corporation",
    "NOW": "ServiceNow Inc.",

    # ── Hong Kong Stocks ──────────────────────────────────────────────────
    "0005.HK": "HSBC Holdings plc",
    "0700.HK": "Tencent Holdings Limited",
    "1299.HK": "AIA Group Limited",
    "2318.HK": "Ping An Insurance Group Co.",
    "3690.HK": "Meituan",
    "9988.HK": "Alibaba Group Holding Limited",
    "1810.HK": "Xiaomi Corporation",
    "2269.HK": "WuXi Biologics Cayman Inc.",
    "2020.HK": "ANSPORT INTERNATIONAL HOLDINGS LTD",
    "9618.HK": "JD.com Inc.",
    "0388.HK": "Hong Kong Exchanges and Clearing",
    "0941.HK": "China Mobile Limited",
    "1398.HK": "Industrial and Commercial Bank of China",
    "0883.HK": "CNOOC Limited",
    "2628.HK": "China Life Insurance Co. Ltd.",
    "1211.HK": "BYD Company Limited",
    "0027.HK": "Galaxy Entertainment Group Limited",
    "0066.HK": "MTR Corporation Limited",
    "0002.HK": "CLP Holdings Limited",
    "0003.HK": "Hong Kong and China Gas Company",
    "0011.HK": "Hang Seng Bank Limited",
    "0016.HK": "SHK Properties Limited",
    "0001.HK": "CK Hutchison Holdings Limited",
    "0006.HK": "Power Assets Holdings Limited",
    "0012.HK": "Henderson Land Development Company",

    # ── A-Shares (Shanghai / Shenzhen) ────────────────────────────────────
    "600519": "贵州茅台 (Kweichow Moutai)",
    "000001": "平安银行 (Ping An Bank)",
    "300308": "中际旭创 (Zhongji Innolight)",
    "002594": "比亚迪 (BYD)",
    "600036": "招商银行 (China Merchants Bank)",
    "000333": "美的集团 (Midea Group)",
    "300750": "宁德时代 (CATL)",
    "601318": "中国平安 (Ping An Insurance)",
    "600276": "恒瑞医药 (Jiangsu Hengrui)",
    "002415": "海康威视 (Hikvision)",
    "601398": "工商银行 (ICBC)",
    "600030": "中信证券 (CITIC Securities)",
    "000858": "五粮液 (Wuliangye)",
    "600900": "长江电力 (Yangtze Power)",
    "601012": "隆基绿能 (LONGi Green Energy)",
}


def lookup_name(symbol: str) -> str | None:
    """Return the company name for a stock symbol, or None if unknown.

    Args:
        symbol: Stock ticker in yfinance format (e.g., "AAPL", "0700.HK", "600519").

    Returns:
        Company name string, or None if the symbol is not in the map.
    """
    return STOCK_NAME_MAP.get(symbol.upper())
