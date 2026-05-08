"""
Lobster Quant - Internationalization
Centralized translation system for Chinese/English support.
"""
import streamlit as st
from typing import Optional

# Translation dictionaries
TRANSLATIONS = {
    "zh": {
        # App
        "app.title": "🦞 Lobster Quant",
        "app.subtitle": "量化交易研究工具",
        "app.version": "v2.0.0 - 模块化架构",
        "app.built_with": "基于现代架构构建",
        
        # Navigation
        "nav.dashboard": "📊 仪表盘",
        "nav.scanner": "🔍 扫描器",
        "nav.analyzer": "📈 分析器",
        "nav.backtest": "🧪 回测",
        "nav.quant_tool": "🔧 量化工具",
        "nav.settings": "⚙️ 设置",
        
        # Dashboard
        "dashboard.title": "📊 Lobster Quant 仪表盘",
        "dashboard.market_status": "市场状态",
        "dashboard.market_condition": "市场状况",
        "dashboard.benchmark_price": "{symbol} 价格",
        "dashboard.on_off_ratio": "ON/OFF 比率",
        "dashboard.off_history": "历史 OFF 状态",
        "dashboard.risk_factors": "当前风险因素",
        "dashboard.failed_benchmark": "获取基准数据失败",
        "dashboard.error_loading": "加载仪表盘出错: {error}",
        
        # Scanner
        "scanner.title": "🔍 股票扫描器",
        "scanner.select_market": "选择市场",
        "scanner.min_score": "最低评分",
        "scanner.scan": "🚀 扫描",
        "scanner.scanning": "正在扫描 {count} 只股票...",
        "scanner.no_results": "没有股票满足条件",
        "scanner.found": "找到 {count} 只股票",
        "scanner.top_picks": "精选推荐",
        "scanner.us_stocks": "美股",
        "scanner.hk_stocks": "港股",
        "scanner.a_shares": "A股",
        
        # Analyzer
        "analyzer.title": "📈 股票分析器",
        "analyzer.enter_symbol": "输入股票代码",
        "analyzer.analyze": "分析",
        "analyzer.analyzing": "正在分析 {symbol}...",
        "analyzer.enter_to_analyze": "输入股票代码开始分析",
        "analyzer.signal": "信号",
        "analyzer.price_chart": "价格图表",
        "analyzer.off_filter": "OFF 过滤器状态",
        "analyzer.trading_status": "交易状态",
        "analyzer.backtest": "回测",
        "analyzer.no_trades": "当前参数下没有产生交易",
        "analyzer.error": "分析 {symbol} 出错: {error}",
        
        # Backtest
        "backtest.title": "🧪 策略回测",
        "backtest.symbol": "股票代码",
        "backtest.holding_days": "持有天数",
        "backtest.min_score": "最低评分",
        "backtest.run": "运行回测",
        "backtest.running": "正在回测 {symbol}...",
        "backtest.performance": "绩效摘要",
        "backtest.total_trades": "总交易数",
        "backtest.win_rate": "胜率",
        "backtest.avg_return": "平均收益",
        "backtest.profit_factor": "盈亏比",
        "backtest.max_drawdown": "最大回撤",
        "backtest.cumulative_return": "累计收益",
        "backtest.sharpe_ratio": "夏普比率",
        "backtest.equity_curve": "权益曲线",
        "backtest.trade_history": "交易历史",
        "backtest.no_trades": "没有产生交易，请尝试降低最低评分。",
        "backtest.error": "回测出错: {error}",
        
        # Settings
        "settings.title": "⚙️ 设置",
        "settings.market_config": "市场配置",
        "settings.us_stocks": "美股",
        "settings.hk_stocks": "港股",
        "settings.a_shares": "A股",
        "settings.data_config": "数据配置",
        "settings.data_years": "数据年数",
        "settings.cache_ttl": "缓存有效期（秒）",
        "settings.scoring_weights": "评分权重",
        "settings.trend": "趋势",
        "settings.momentum": "动量",
        "settings.volume": "成交量",
        "settings.pattern": "形态",
        "settings.weights_warning": "权重总和为 {total:.2f}，应为 1.00",
        "settings.backtest_config": "回测配置",
        "settings.holding_days": "持有天数",
        "settings.min_entry_score": "最低入场评分",
        "settings.off_filter": "OFF 过滤器参数",
        "settings.atr_threshold": "ATR% 阈值",
        "settings.gap_threshold": "Gap 阈值",
        "settings.save": "保存设置",
        "settings.saved": "设置已保存！（注意：部分设置需要重启）",
        "settings.language": "语言",
        
        # Quant Tool
        "quant.title": "量化工具",
        "quant.input_placeholder": "例如：AAPL, MSFT, TSLA",
        "quant.fetch_data": "获取数据",
        "quant.fetching": "正在获取 {symbol} 数据...",
        "quant.off_assessment": "🎯 OFF 评估",
        "quant.on_probability": "ON 概率",
        "quant.off_probability": "OFF 概率",
        "quant.reason_analysis": "📋 原因分析",
        "quant.atr_pct": "ATR%",
        "quant.ma200_dist": "MA200 距离",
        "quant.spy_env": "SPY 环境",
        "quant.above_threshold": "高于阈值",
        "quant.normal": "正常",
        "quant.below_ma200": "低于 MA200",
        "quant.above_ma200": "高于 MA200",
        "quant.bullish": "看涨",
        "quant.bearish": "看跌",
        "quant.options_analysis": "📊 期权分析",
        "quant.no_options": "该标的无可用期权数据",
        "quant.options_failed": "期权数据获取失败: {error}",
        "quant.max_pain": "Max Pain",
        "quant.pain_point": "痛点集中位",
        "quant.support": "支撑位",
        "quant.put_support": "看跌支撑位",
        "quant.resistance": "阻力位",
        "quant.call_resistance": "看涨阻力位",
        "quant.put_call_ratio": "看跌/看涨比率",
        "quant.option_charts": "📈 期权链图表",
        "quant.input_prompt": "👋 输入股票代码开始分析",
        "quant.input_help": "上方输入股票代码并点击\"获取数据\"以查看：",
        "quant.feature_off": "🎯 **OFF 评估** - 概率驱动的交易条件分析",
        "quant.feature_options": "📊 **期权分析** - Max Pain、支撑位/阻力位",
        "quant.feature_charts": "📈 **期权链图表** - 成交量与未平仓量分析",
        "quant.supported_codes": "支持代码：AAPL, MSFT, TSLA, NVDA, MU",
        "quant.page_failed": "页面渲染失败: {error}",
        "quant.refresh_hint": "请刷新页面后重试",
        "quant.powered_by": "数据来源: yfinance | 数据每小时刷新",
        
        # Signals
        "signal.strong_buy": "强烈推荐",
        "signal.buy": "推荐",
        "signal.hold": "持有",
        "signal.watch": "观望",
        "signal.score": "评分",
        "signal.probability": "上涨概率",
        
        # OFF Status
        "off.on": "ON",
        "off.off": "OFF",
        "off.atr_high": "ATR过高",
        "off.ma200_recovery": "MA200恢复",
        "off.gap_large": "Gap过大",
        "off.benchmark_risk": "大盘风险",
        "off.low_liquidity": "流动性不足",
        "off.reasons": "原因",
        "off.none": "无",
        
        # Errors
        "error.fetch_failed": "获取 {symbol} 数据失败",
        "error.network": "网络错误，请检查连接后重试",
        "error.timeout": "请求超时，请稍后重试",
        "error.invalid_symbol": "无效的股票代码: {symbol}",
        "error.no_provider": "没有可用的数据提供商",
        "error.cache_read": "缓存读取失败",
        "error.cache_write": "缓存写入失败",
        
        # Help/Tooltips
        "help.scoring_weights": "评分权重决定了各因素在综合评分中的占比，所有权重之和必须为 1.0",
        "help.trend_weight": "趋势权重：基于均线斜率的趋势强度",
        "help.momentum_weight": "动量权重：基于RSI和收益率的动量指标",
        "help.volume_weight": "成交量权重：基于成交量比率的确认信号",
        "help.pattern_weight": "形态权重：基于MACD、均线排列等技术形态",
        "help.off_filter": "OFF 过滤器用于识别不利的市场环境，当触发时建议暂停交易",
        "help.signal_legend": "信号说明：强烈推荐(≥70分且上涨概率≥60%)、推荐(≥50分且概率≥50%)、持有(≥30分)、观望(<30分)",
        "help.min_score": "最低评分：只显示评分高于此值的结果",
        "help.holding_days": "持有天数：回测中每笔交易的持有周期",
        
        # Common
        "common.loading": "加载中...",
        "common.error": "出错",
        "common.success": "成功",
        "common.warning": "警告",
        "common.info": "提示",
        "common.na": "N/A",
        "common.price": "价格",
        "common.rsi": "RSI",
        "common.atr_pct": "ATR%",
        "common.vol_ratio": "成交量比率",
        "common.save": "保存",
        "common.cancel": "取消",
        "common.confirm": "确认",
        "common.yes": "是",
        "common.no": "否",
    },
    "en": {
        # App
        "app.title": "🦞 Lobster Quant",
        "app.subtitle": "Quantitative Trading Research Tool",
        "app.version": "v2.0.0 - Modular Architecture",
        "app.built_with": "Built with modern architecture",
        
        # Navigation
        "nav.dashboard": "📊 Dashboard",
        "nav.scanner": "🔍 Scanner",
        "nav.analyzer": "📈 Analyzer",
        "nav.backtest": "🧪 Backtest",
        "nav.quant_tool": "🔧 Quant Tool",
        "nav.settings": "⚙️ Settings",
        
        # Dashboard
        "dashboard.title": "📊 Lobster Quant Dashboard",
        "dashboard.market_status": "Market Status",
        "dashboard.market_condition": "Market Condition",
        "dashboard.benchmark_price": "{symbol} Price",
        "dashboard.on_off_ratio": "ON/OFF Ratio",
        "dashboard.off_history": "Historical OFF Status",
        "dashboard.risk_factors": "Current Risk Factors",
        "dashboard.failed_benchmark": "Failed to fetch benchmark data",
        "dashboard.error_loading": "Error loading dashboard: {error}",
        
        # Scanner
        "scanner.title": "🔍 Stock Scanner",
        "scanner.select_market": "Select Market",
        "scanner.min_score": "Min Score",
        "scanner.scan": "🚀 Scan",
        "scanner.scanning": "Scanning {count} stocks...",
        "scanner.no_results": "No stocks meet the criteria",
        "scanner.found": "Found {count} stocks",
        "scanner.top_picks": "Top Picks",
        "scanner.us_stocks": "US Stocks",
        "scanner.hk_stocks": "HK Stocks",
        "scanner.a_shares": "A-Shares",
        
        # Analyzer
        "analyzer.title": "📈 Stock Analyzer",
        "analyzer.enter_symbol": "Enter Stock Symbol",
        "analyzer.analyze": "Analyze",
        "analyzer.analyzing": "Analyzing {symbol}...",
        "analyzer.enter_to_analyze": "Enter a stock symbol to analyze",
        "analyzer.signal": "Signal",
        "analyzer.price_chart": "Price Chart",
        "analyzer.off_filter": "OFF Filter Status",
        "analyzer.trading_status": "Trading Status",
        "analyzer.backtest": "Backtest",
        "analyzer.no_trades": "No trades generated with current parameters",
        "analyzer.error": "Error analyzing {symbol}: {error}",
        
        # Backtest
        "backtest.title": "🧪 Strategy Backtest",
        "backtest.symbol": "Symbol",
        "backtest.holding_days": "Holding Days",
        "backtest.min_score": "Min Score",
        "backtest.run": "Run Backtest",
        "backtest.running": "Backtesting {symbol}...",
        "backtest.performance": "Performance Summary",
        "backtest.total_trades": "Total Trades",
        "backtest.win_rate": "Win Rate",
        "backtest.avg_return": "Avg Return",
        "backtest.profit_factor": "Profit Factor",
        "backtest.max_drawdown": "Max Drawdown",
        "backtest.cumulative_return": "Cumulative Return",
        "backtest.sharpe_ratio": "Sharpe Ratio",
        "backtest.equity_curve": "Equity Curve",
        "backtest.trade_history": "Trade History",
        "backtest.no_trades": "No trades generated. Try lowering the minimum score.",
        "backtest.error": "Error running backtest: {error}",
        
        # Settings
        "settings.title": "⚙️ Settings",
        "settings.market_config": "Market Configuration",
        "settings.us_stocks": "US Stocks",
        "settings.hk_stocks": "HK Stocks",
        "settings.a_shares": "A-Shares",
        "settings.data_config": "Data Configuration",
        "settings.data_years": "Data Years",
        "settings.cache_ttl": "Cache TTL (seconds)",
        "settings.scoring_weights": "Scoring Weights",
        "settings.trend": "Trend",
        "settings.momentum": "Momentum",
        "settings.volume": "Volume",
        "settings.pattern": "Pattern",
        "settings.weights_warning": "Weights sum to {total:.2f}, should be 1.00",
        "settings.backtest_config": "Backtest Configuration",
        "settings.holding_days": "Holding Days",
        "settings.min_entry_score": "Min Entry Score",
        "settings.off_filter": "OFF Filter Parameters",
        "settings.atr_threshold": "ATR% Threshold",
        "settings.gap_threshold": "Gap Threshold",
        "settings.save": "Save Settings",
        "settings.saved": "Settings saved! (Note: Some settings require restart)",
        "settings.language": "Language",
        
        # Quant Tool
        "quant.title": "Quant Tool",
        "quant.input_placeholder": "e.g., AAPL, MSFT, TSLA",
        "quant.fetch_data": "Fetch Data",
        "quant.fetching": "Fetching {symbol} data...",
        "quant.off_assessment": "🎯 OFF Assessment",
        "quant.on_probability": "ON Probability",
        "quant.off_probability": "OFF Probability",
        "quant.reason_analysis": "📋 Reason Analysis",
        "quant.atr_pct": "ATR%",
        "quant.ma200_dist": "MA200 Distance",
        "quant.spy_env": "SPY Environment",
        "quant.above_threshold": "Above threshold",
        "quant.normal": "Normal",
        "quant.below_ma200": "Below MA200",
        "quant.above_ma200": "Above MA200",
        "quant.bullish": "Bullish",
        "quant.bearish": "Bearish",
        "quant.options_analysis": "📊 Options Analysis",
        "quant.no_options": "No options data available for this symbol",
        "quant.options_failed": "Failed to fetch options: {error}",
        "quant.max_pain": "Max Pain",
        "quant.pain_point": "Pain concentration point",
        "quant.support": "Support",
        "quant.put_support": "Put support level",
        "quant.resistance": "Resistance",
        "quant.call_resistance": "Call resistance level",
        "quant.put_call_ratio": "Put/Call Ratio",
        "quant.option_charts": "📈 Option Chain Charts",
        "quant.input_prompt": "👋 Enter a stock symbol to start analysis",
        "quant.input_help": "Enter a stock symbol above and click \"Fetch Data\" to view:",
        "quant.feature_off": "🎯 **OFF Assessment** - Probability-driven trading condition analysis",
        "quant.feature_options": "📊 **Options Analysis** - Max Pain, Support/Resistance levels",
        "quant.feature_charts": "📈 **Option Chain Charts** - Volume and Open Interest analysis",
        "quant.supported_codes": "Supported: AAPL, MSFT, TSLA, NVDA, MU",
        "quant.page_failed": "Page render failed: {error}",
        "quant.refresh_hint": "Please refresh the page and try again",
        "quant.powered_by": "Powered by yfinance | Data refreshes every hour",
        
        # Signals
        "signal.strong_buy": "Strong Buy",
        "signal.buy": "Buy",
        "signal.hold": "Hold",
        "signal.watch": "Watch",
        "signal.score": "Score",
        "signal.probability": "Up Probability",
        
        # OFF Status
        "off.on": "ON",
        "off.off": "OFF",
        "off.atr_high": "High ATR",
        "off.ma200_recovery": "MA200 Recovery",
        "off.gap_large": "Large Gap",
        "off.benchmark_risk": "Benchmark Risk",
        "off.low_liquidity": "Low Liquidity",
        "off.reasons": "Reasons",
        "off.none": "None",
        
        # Errors
        "error.fetch_failed": "Failed to fetch data for {symbol}",
        "error.network": "Network error, please check your connection",
        "error.timeout": "Request timed out, please try again later",
        "error.invalid_symbol": "Invalid stock symbol: {symbol}",
        "error.no_provider": "No data provider available",
        "error.cache_read": "Cache read failed",
        "error.cache_write": "Cache write failed",
        
        # Help/Tooltips
        "help.scoring_weights": "Scoring weights determine how each factor contributes to the composite score. All weights must sum to 1.0",
        "help.trend_weight": "Trend weight: trend strength based on moving average slopes",
        "help.momentum_weight": "Momentum weight: momentum indicators based on RSI and returns",
        "help.volume_weight": "Volume weight: confirmation signal based on volume ratio",
        "help.pattern_weight": "Pattern weight: technical patterns like MACD, MA alignment",
        "help.off_filter": "OFF filter identifies unfavorable market conditions. When triggered, it recommends pausing trades",
        "help.signal_legend": "Signals: Strong Buy (score≥70 & prob≥60%), Buy (≥50 & prob≥50%), Hold (≥30), Watch (<30)",
        "help.min_score": "Min Score: only show results with score above this value",
        "help.holding_days": "Holding Days: the holding period for each trade in backtest",
        
        # Common
        "common.loading": "Loading...",
        "common.error": "Error",
        "common.success": "Success",
        "common.warning": "Warning",
        "common.info": "Info",
        "common.na": "N/A",
        "common.price": "Price",
        "common.rsi": "RSI",
        "common.atr_pct": "ATR%",
        "common.vol_ratio": "Vol Ratio",
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.confirm": "Confirm",
        "common.yes": "Yes",
        "common.no": "No",
    }
}


def get_language() -> str:
    """Get current language from session state or settings."""
    try:
        import streamlit as st
        lang = st.session_state.get("language", None)
        if lang is None:
            from src.config.settings import get_settings
            lang = get_settings().language
        return lang if lang in TRANSLATIONS else "zh"
    except Exception:
        return "zh"


def t(key: str, **kwargs) -> str:
    """Translate a key to the current language.
    
    Args:
        key: Translation key (e.g., "dashboard.title")
        **kwargs: Format arguments for string interpolation
    
    Returns:
        Translated string, or the key itself if not found
    """
    lang = get_language()
    text = TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key)
    if text is None:
        # Fallback to Chinese, then to key
        text = TRANSLATIONS["zh"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def get_signal_label(signal_type: str) -> str:
    """Translate signal type to current language.
    
    Args:
        signal_type: One of "强烈推荐", "推荐", "持有", "观望"
    
    Returns:
        Translated signal label
    """
    signal_map = {
        "强烈推荐": "signal.strong_buy",
        "推荐": "signal.buy",
        "持有": "signal.hold",
        "观望": "signal.watch",
        "Strong Buy": "signal.strong_buy",
        "Buy": "signal.buy",
        "Hold": "signal.hold",
        "Watch": "signal.watch",
    }
    key = signal_map.get(signal_type, signal_type)
    return t(key)


def get_off_reason_label(reason: str) -> str:
    """Translate OFF filter reason to current language.
    
    Args:
        reason: Chinese reason string from risk engine
    
    Returns:
        Translated reason label
    """
    reason_map = {
        "ATR过高": "off.atr_high",
        "MA200恢复": "off.ma200_recovery",
        "Gap过大": "off.gap_large",
        "大盘风险": "off.benchmark_risk",
        "流动性不足": "off.low_liquidity",
    }
    key = reason_map.get(reason, reason)
    return t(key)
