"""
Lobster Quant - Configuration Validation
"""

from .settings import Settings
from ..utils.exceptions import ConfigValidationError, ConfigError
from ..utils.logging import get_logger

logger = get_logger()


def validate_settings(settings: Settings) -> list[str]:
    """
    Run all validation checks on a Settings instance.

    Args:
        settings: Settings instance to validate

    Returns:
        List of warning/error strings. Empty list means fully valid.
        - Weight sum ~1.0
        - At least one market enabled
        - holding_days > 0
        - min_score >= 0
        - data_years 1-10
        - cache_ttl >= 300
    """
    warnings: list[str] = []

    # Check weight sum
    if not validate_weight_sum(settings.scoring_weights):
        warnings.append(
            f"Scoring weights do not sum to 1.0: "
            f"sum={sum(settings.scoring_weights.values()):.2f}"
        )

    # Check at least one market enabled
    market_warnings = validate_market_config(settings.enabled_markets)
    warnings.extend(market_warnings)

    # Check holding_days > 0
    if settings.backtest_holding_days <= 0:
        warnings.append(
            f"backtest_holding_days must be > 0, got {settings.backtest_holding_days}"
        )

    # Check min_score >= 0
    if settings.backtest_min_score < 0:
        warnings.append(
            f"backtest_min_score must be >= 0, got {settings.backtest_min_score}"
        )

    # Check data_years 1-10
    if not (1 <= settings.data_years <= 10):
        warnings.append(
            f"data_years must be 1-10, got {settings.data_years}"
        )

    # Check cache_ttl >= 300
    if settings.data_cache_ttl < 300:
        warnings.append(
            f"data_cache_ttl must be >= 300, got {settings.data_cache_ttl}"
        )

    return warnings


def validate_weight_sum(weights: dict[str, float]) -> bool:
    """
    Check if scoring weights sum to ~1.0 (tolerance 0.01).

    Args:
        weights: Dictionary of scoring weights

    Returns:
        True if weights sum to approximately 1.0, False otherwise
    """
    total = sum(weights.values())
    return abs(total - 1.0) <= 0.01


def validate_market_config(markets: list[str]) -> list[str]:
    """
    Check at least one market is enabled.

    Args:
        markets: List of enabled market identifiers

    Returns:
        List of warning strings (empty if valid)
    """
    warnings: list[str] = []

    if not markets:
        warnings.append(
            "No markets enabled. At least one of enable_us_stock, "
            "enable_hk_stock, or enable_a_stock must be True"
        )

    return warnings