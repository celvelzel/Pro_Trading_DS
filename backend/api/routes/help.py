"""
Lobster Quant - Help API Routes
Endpoints for providing help text and documentation to the frontend.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter()


class HelpText(BaseModel):
    """Help text response model."""
    key: str
    title: Optional[str] = None
    content: str
    updated_at: Optional[str] = None


# ============================================================================
# Help Text Database
# In production, this could be stored in a database or configuration file.
# ============================================================================

HELP_TEXTS: Dict[str, HelpText] = {
    # Dashboard
    "dashboard.title": HelpText(
        key="dashboard.title",
        title="Dashboard",
        content="市场概览和快速分析中心。显示基准指数(SPY)表现、市场状态、风险指标，以及您的自选股票列表。",
    ),
    "dashboard.market_status": HelpText(
        key="dashboard.market_status",
        title="Market Status",
        content="显示当前市场状态和趋势方向。基于SPY基准指数分析市场是处于上涨、下跌还是震荡状态。",
    ),
    "dashboard.risk_metrics": HelpText(
        key="dashboard.risk_metrics",
        title="Risk Metrics",
        content="显示当前市场的风险评估指标，包括波动率、风险等级和市场情绪。帮助您了解当前市场的风险水平。",
    ),
    "dashboard.watchlist": HelpText(
        key="dashboard.watchlist",
        title="Watchlist",
        content="您的自选股票列表。可以添加、删除股票，查看实时价格和涨跌幅。点击股票代码可查看详细分析。",
    ),

    # Scanner
    "scanner.title": HelpText(
        key="scanner.title",
        title="Stock Scanner",
        content="股票扫描器。根据技术指标和评分标准扫描各市场的股票，发现潜在的交易机会。",
    ),
    "scanner.scan_parameters": HelpText(
        key="scanner.scan_parameters",
        title="Scan Parameters",
        content="配置扫描参数：选择市场（美股/港股/A股）和最低评分阈值。评分越高，筛选条件越严格。",
    ),
    "scanner.results": HelpText(
        key="scanner.results",
        title="Scan Results",
        content="扫描结果列表。显示符合筛选条件的股票，包括评分、价格和技术指标。点击股票可查看详细分析。",
    ),

    # Analysis
    "analysis.title": HelpText(
        key="analysis.title",
        title="Stock Analysis",
        content="个股详细分析页面。显示股票的价格走势、技术指标、交易信号和风险评估。",
    ),
    "analysis.charts": HelpText(
        key="analysis.charts",
        title="Price Charts",
        content="K线图显示股票价格走势。可以切换时间周期（日K、周K、月K），添加技术指标（MA、RSI、MACD等）。",
    ),
    "analysis.indicators": HelpText(
        key="analysis.indicators",
        title="Technical Indicators",
        content="技术指标面板。包括移动平均线(MA)、相对强弱指数(RSI)、MACD等常用技术分析工具。",
    ),

    # Backtest
    "backtest.title": HelpText(
        key="backtest.title",
        title="Strategy Backtest",
        content="策略回测工具。测试交易策略在历史数据上的表现，评估策略的盈利能力和风险水平。",
    ),
    "backtest.config": HelpText(
        key="backtest.config",
        title="Backtest Configuration",
        content="配置回测参数：选择股票、时间范围、初始资金和交易策略。设置完成后点击运行回测。",
    ),
    "backtest.results": HelpText(
        key="backtest.results",
        title="Backtest Results",
        content="回测结果展示。包括总收益率、年化收益、最大回撤、夏普比率等关键指标，以及权益曲线图。",
    ),

    # Strategy
    "strategy.title": HelpText(
        key="strategy.title",
        title="Trading Strategy",
        content="交易策略管理。选择和配置交易策略，包括技术指标参数、买入卖出条件等。",
    ),
    "strategy.selector": HelpText(
        key="strategy.selector",
        title="Strategy Selector",
        content="策略选择器。从预设策略中选择，或创建自定义策略。每种策略有不同的风险收益特征。",
    ),
    "strategy.config": HelpText(
        key="strategy.config",
        title="Strategy Configuration",
        content="策略参数配置。调整技术指标的参数，如移动平均线周期、RSI阈值等，以优化策略表现。",
    ),

    # Simulation
    "simulation.title": HelpText(
        key="simulation.title",
        title="Paper Trading",
        content="模拟交易功能。使用虚拟资金进行实时模拟交易，测试策略在当前市场环境下的表现。",
    ),
    "simulation.trades": HelpText(
        key="simulation.trades",
        title="Trade History",
        content="交易历史记录。显示所有模拟交易的详情，包括买入/卖出价格、数量、盈亏等信息。",
    ),

    # Settings
    "settings.title": HelpText(
        key="settings.title",
        title="Settings",
        content="系统设置页面。配置数据源、通知偏好、显示选项等系统参数。",
    ),
}


@router.get("/{key}", response_model=HelpText)
async def get_help_text(key: str) -> HelpText:
    """
    Get help text by key.

    Args:
        key: Help text identifier (e.g., "dashboard.title")

    Returns:
        HelpText object with title and content

    Raises:
        HTTPException: If help text not found
    """
    if key not in HELP_TEXTS:
        raise HTTPException(
            status_code=404,
            detail=f"Help text not found for key: {key}"
        )
    return HELP_TEXTS[key]


@router.get("/", response_model=Dict[str, HelpText])
async def get_all_help_texts() -> Dict[str, HelpText]:
    """
    Get all help texts.

    Returns:
        Dictionary of all help texts keyed by their identifier
    """
    return HELP_TEXTS
