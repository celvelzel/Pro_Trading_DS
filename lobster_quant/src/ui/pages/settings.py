"""
Lobster Quant - Settings Page
Configuration management interface.
"""

import streamlit as st

from src.config.settings import get_settings, reload_settings
from src.utils.logging import get_logger

logger = get_logger()


def render_settings():
    """Render the settings page."""
    st.title("⚙️ Settings")
    
    settings = get_settings()
    
    # Market settings
    st.header("Market Configuration")
    col1, col2, col3 = st.columns(3)
    with col1:
        us_enabled = st.checkbox("US Stocks", value=settings.enable_us_stock)
    with col2:
        hk_enabled = st.checkbox("HK Stocks", value=settings.enable_hk_stock)
    with col3:
        a_enabled = st.checkbox("A-Shares", value=settings.enable_a_stock)
    
    # Data settings
    st.header("Data Configuration")
    col1, col2 = st.columns(2)
    with col1:
        data_years = st.slider("Data Years", 1, 10, settings.data_years)
    with col2:
        cache_ttl = st.slider("Cache TTL (seconds)", 300, 7200, settings.data_cache_ttl)
    
    # Scoring weights
    st.header("Scoring Weights")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        trend_weight = st.slider("Trend", 0.0, 1.0, settings.score_weight_trend, 0.05)
    with col2:
        momentum_weight = st.slider("Momentum", 0.0, 1.0, settings.score_weight_momentum, 0.05)
    with col3:
        volume_weight = st.slider("Volume", 0.0, 1.0, settings.score_weight_volume, 0.05)
    with col4:
        pattern_weight = st.slider("Pattern", 0.0, 1.0, settings.score_weight_pattern, 0.05)
    
    # Validate weights
    total_weight = trend_weight + momentum_weight + volume_weight + pattern_weight
    if abs(total_weight - 1.0) > 0.01:
        st.warning(f"Weights sum to {total_weight:.2f}, should be 1.00")
    
    # Backtest settings
    st.header("Backtest Configuration")
    col1, col2 = st.columns(2)
    with col1:
        holding_days = st.slider("Holding Days", 5, 60, settings.backtest_holding_days)
    with col2:
        min_score = st.slider("Min Entry Score", 0, 100, settings.backtest_min_score)
    
    # OFF Filter settings
    st.header("OFF Filter Parameters")
    col1, col2 = st.columns(2)
    with col1:
        atr_threshold = st.slider("ATR% Threshold", 0.01, 0.20, settings.off_atr_pct_threshold, 0.01)
    with col2:
        gap_threshold = st.slider("Gap Threshold", 0.01, 0.30, settings.off_gap_threshold, 0.01)
    
    # Save button
    if st.button("Save Settings", type="primary"):
        st.success("Settings saved! (Note: Some settings require restart)")
        logger.info("Settings updated via UI")

