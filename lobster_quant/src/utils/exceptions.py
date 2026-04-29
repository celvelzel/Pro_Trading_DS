"""
Lobster Quant - Custom Exceptions
Unified exception hierarchy for better error handling.
"""


class LobsterQuantError(Exception):
    """Base exception for all Lobster Quant errors."""
    
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | details={self.details}"
        return self.message


# Data Layer Errors
class DataError(LobsterQuantError):
    """Base exception for data-related errors."""
    pass


class DataFetchError(DataError):
    """Failed to fetch data from external source."""
    
    def __init__(self, symbol: str, provider: str, reason: str):
        super().__init__(
            f"Failed to fetch data for {symbol} from {provider}: {reason}",
            details={"symbol": symbol, "provider": provider, "reason": reason}
        )
        self.symbol = symbol
        self.provider = provider


class DataValidationError(DataError):
    """Data validation failed."""
    
    def __init__(self, symbol: str, field: str, expected: str, actual: str):
        super().__init__(
            f"Data validation failed for {symbol}: {field} expected {expected}, got {actual}",
            details={"symbol": symbol, "field": field, "expected": expected, "actual": actual}
        )


class DataProviderError(DataError):
    """Data provider is unavailable or misconfigured."""
    pass


class CacheError(DataError):
    """Cache operation failed."""
    pass


# Analysis Layer Errors
class AnalysisError(LobsterQuantError):
    """Base exception for analysis-related errors."""
    pass


class IndicatorError(AnalysisError):
    """Indicator calculation failed."""
    
    def __init__(self, indicator_name: str, reason: str):
        super().__init__(
            f"Indicator '{indicator_name}' calculation failed: {reason}",
            details={"indicator": indicator_name, "reason": reason}
        )
        self.indicator_name = indicator_name


class SignalError(AnalysisError):
    """Signal generation failed."""
    pass


class ScoringError(AnalysisError):
    """Score calculation failed."""
    pass


class BacktestError(AnalysisError):
    """Backtest execution failed."""
    
    def __init__(self, symbol: str, reason: str):
        super().__init__(
            f"Backtest failed for {symbol}: {reason}",
            details={"symbol": symbol, "reason": reason}
        )
        self.symbol = symbol


# Risk Layer Errors
class RiskError(LobsterQuantError):
    """Base exception for risk-related errors."""
    pass


class OFFFilterError(RiskError):
    """OFF filter calculation failed."""
    pass


# Configuration Errors
class ConfigError(LobsterQuantError):
    """Configuration error."""
    pass


class ConfigValidationError(ConfigError):
    """Configuration validation failed."""
    pass


# UI Layer Errors
class UIError(LobsterQuantError):
    """UI rendering error."""
    pass


# Utility Errors
class ValidationError(LobsterQuantError):
    """General validation error."""
    pass


class SerializationError(LobsterQuantError):
    """Data serialization/deserialization failed."""
    pass
