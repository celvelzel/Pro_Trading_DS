"""
Lobster Quant - Unified Configuration
Pydantic Settings with environment variable support.
"""

from typing import Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Unified application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # ============================================================
    # Application
    # ============================================================
    app_name: str = "Lobster Quant"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # ============================================================
    # Market Configuration
    # ============================================================
    enable_us_stock: bool = Field(default=True, description="Enable US stock market")
    enable_hk_stock: bool = Field(default=True, description="Enable HK stock market")
    enable_a_stock: bool = Field(default=False, description="Enable A-share market")
    
    # ============================================================
    # Data Configuration
    # ============================================================
    data_years: int = Field(default=3, ge=1, le=10, description="Years of historical data")
    data_cache_dir: str = Field(default="./data/cache", description="Cache directory")
    data_cache_ttl: int = Field(default=3600, ge=300, description="Cache TTL in seconds")
    data_timeout: int = Field(default=10, ge=1, le=60, description="API timeout in seconds")
    
    # Data providers
    us_data_provider: Literal["yfinance", "mock"] = Field(default="yfinance")
    hk_data_provider: Literal["yfinance", "mock"] = Field(default="yfinance")
    a_data_provider: Literal["akshare", "mock"] = Field(default="akshare")
    
    # ============================================================
    # Technical Indicator Parameters
    # ============================================================
    ma_short_period: int = Field(default=20, ge=5, le=100)
    ma_long_period: int = Field(default=200, ge=50, le=500)
    rsi_period: int = Field(default=14, ge=5, le=50)
    atr_period: int = Field(default=14, ge=5, le=50)
    macd_fast: int = Field(default=12, ge=5, le=50)
    macd_slow: int = Field(default=26, ge=10, le=100)
    macd_signal: int = Field(default=9, ge=5, le=50)
    bb_period: int = Field(default=20, ge=5, le=100)
    bb_std: float = Field(default=2.0, ge=1.0, le=4.0)
    
    # ============================================================
    # Scoring Weights (must sum to 1.0)
    # ============================================================
    score_weight_trend: float = Field(default=0.40, ge=0.0, le=1.0)
    score_weight_momentum: float = Field(default=0.20, ge=0.0, le=1.0)
    score_weight_volume: float = Field(default=0.15, ge=0.0, le=1.0)
    score_weight_pattern: float = Field(default=0.25, ge=0.0, le=1.0)
    
    # ============================================================
    # Backtest Parameters
    # ============================================================
    backtest_holding_days: int = Field(default=20, ge=5, le=100)
    backtest_min_score: int = Field(default=20, ge=0, le=100)
    backtest_lookback_days: int = Field(default=500, ge=100, le=2000)
    backtest_slippage_pct: float = Field(default=0.001, ge=0.0, le=0.01)
    backtest_commission_pct: float = Field(default=0.001, ge=0.0, le=0.01)
    
    # ============================================================
    # OFF Filter Parameters
    # ============================================================
    off_vix_threshold: float = Field(default=35.0, ge=10.0, le=100.0)
    off_atr_pct_threshold: float = Field(default=0.05, ge=0.01, le=0.20)
    off_gap_threshold: float = Field(default=0.08, ge=0.01, le=0.30)
    off_min_volume_ratio: float = Field(default=0.05, ge=0.0, le=1.0)
    off_ma200_recovery_days: int = Field(default=60, ge=10, le=200)
    
    # ============================================================
    # Benchmark
    # ============================================================
    benchmark_symbol: str = Field(default="SPY", description="Benchmark symbol for market comparison")
    
    # ============================================================
    # Computed Properties
    # ============================================================
    @property
    def scoring_weights(self) -> dict[str, float]:
        """Get scoring weights as a dictionary."""
        return {
            "trend": self.score_weight_trend,
            "momentum": self.score_weight_momentum,
            "volume": self.score_weight_volume,
            "pattern": self.score_weight_pattern,
        }
    
    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug
    
    @property
    def enabled_markets(self) -> list[str]:
        """Get list of enabled markets."""
        markets = []
        if self.enable_us_stock:
            markets.append("us_stock")
        if self.enable_hk_stock:
            markets.append("hk_stock")
        if self.enable_a_stock:
            markets.append("a_stock")
        return markets
    
    # ============================================================
    # Validators
    # ============================================================
    @field_validator("score_weight_trend", "score_weight_momentum", 
                     "score_weight_volume", "score_weight_pattern")
    @classmethod
    def validate_weights(cls, v: float) -> float:
        """Ensure individual weights are valid."""
        return round(v, 2)
    
    def validate_weight_sum(self) -> bool:
        """Check if weights sum to approximately 1.0."""
        total = (self.score_weight_trend + self.score_weight_momentum + 
                 self.score_weight_volume + self.score_weight_pattern)
        return abs(total - 1.0) < 0.01


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
