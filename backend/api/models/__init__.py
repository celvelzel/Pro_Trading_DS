"""
Lobster Quant - API Models
Centralized Pydantic schemas for all API endpoints.
"""

from .common import ApiResponse, ApiError
from .stocks import (
    Candle,
    StockData,
    Indicators,
    MACDData,
    Signal,
    OptionsAnalysis,
    RiskAssessment,
)
from .scanner import ScanRequest, StockResult, ScanResponse
from .backtest import (
    BacktestRequest,
    BacktestTrade,
    EquityPoint,
    BacktestResponse,
)
from .settings import (
    MarketSettings,
    DataSettings,
    ScoringWeights,
    BacktestSettings,
    OFFFilterSettings,
    IndicatorSettings,
    AppSettings,
    SettingsUpdateRequest,
    SettingsResponse,
)
from .strategy import (
    StrategyParamsRequest,
    CreateStrategyRequest,
    UpdateStrategyRequest,
    StrategyResponse,
    CompareStrategiesRequest,
    StrategyComparisonResponse,
)

__all__ = [
    # Common
    "ApiResponse",
    "ApiError",
    # Stocks
    "Candle",
    "StockData",
    "Indicators",
    "MACDData",
    "Signal",
    "OptionsAnalysis",
    "RiskAssessment",
    # Scanner
    "ScanRequest",
    "StockResult",
    "ScanResponse",
    # Backtest
    "BacktestRequest",
    "BacktestTrade",
    "EquityPoint",
    "BacktestResponse",
    # Settings
    "MarketSettings",
    "DataSettings",
    "ScoringWeights",
    "BacktestSettings",
    "OFFFilterSettings",
    "IndicatorSettings",
    "AppSettings",
    "SettingsUpdateRequest",
    "SettingsResponse",
    # Strategy
    "StrategyParamsRequest",
    "CreateStrategyRequest",
    "UpdateStrategyRequest",
    "StrategyResponse",
    "CompareStrategiesRequest",
    "StrategyComparisonResponse",
]
