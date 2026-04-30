"""
Tests for Settings configuration.
"""

import pytest
from src.config.settings import Settings, get_settings, reload_settings
from src.config.validation import validate_settings, validate_weight_sum, validate_market_config


class TestSettings:
    def test_default_values(self):
        s = Settings(debug=False)
        assert s.app_name == "Lobster Quant"
        assert s.app_version == "2.0.0"
        assert s.debug is False
        assert s.data_years == 3
        assert s.data_cache_ttl == 3600

    def test_scoring_weights_property(self):
        s = Settings()
        weights = s.scoring_weights
        assert isinstance(weights, dict)
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_enabled_markets_default(self):
        s = Settings(enable_us_stock=True, enable_hk_stock=True, enable_a_stock=False)
        markets = s.enabled_markets
        assert "us_stock" in markets
        assert "hk_stock" in markets
        assert "a_stock" not in markets

    def test_is_debug_property(self):
        s = Settings(debug=False)
        assert s.is_debug is False

    def test_validate_weight_sum_valid(self):
        s = Settings()
        assert s.validate_weight_sum() is True


class TestGetSettings:
    def test_returns_settings(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_singleton(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reload(self):
        s1 = get_settings()
        s2 = reload_settings()
        s3 = get_settings()
        assert s3 is s2


class TestValidation:
    def test_validate_weight_sum_valid(self):
        assert validate_weight_sum({"trend": 0.4, "momentum": 0.2, "volume": 0.15, "pattern": 0.25}) is True

    def test_validate_weight_sum_invalid(self):
        assert validate_weight_sum({"trend": 0.5, "momentum": 0.5, "volume": 0.5, "pattern": 0.5}) is False

    def test_validate_market_config_valid(self):
        warnings = validate_market_config(["us_stock", "hk_stock"])
        assert warnings == []

    def test_validate_market_config_empty(self):
        warnings = validate_market_config([])
        assert len(warnings) == 1

    def test_validate_settings_valid(self):
        s = Settings(enable_us_stock=True)
        warnings = validate_settings(s)
        assert warnings == []

    def test_validate_settings_no_markets(self):
        s = Settings(enable_us_stock=False, enable_hk_stock=False, enable_a_stock=False)
        warnings = validate_settings(s)
        assert any("No markets enabled" in w for w in warnings)
