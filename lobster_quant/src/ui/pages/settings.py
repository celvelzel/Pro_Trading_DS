"""
Lobster Quant - Settings Page
Configuration management interface.
"""

import streamlit as st

from src.config.settings import get_settings, reload_settings
from src.utils.i18n import t, get_language
from src.utils.logging import get_logger

logger = get_logger()


def render_settings():
    """Render the settings page."""
    st.title(t("settings.title"))
    
    # Language selector at top
    lang = st.selectbox(t("settings.language"), ["zh", "en"], 
                         index=0 if get_language() == "zh" else 1,
                         key="settings_language")
    st.session_state.language = lang
    
    settings = get_settings()
    
    # Market settings
    st.header(t("settings.market_config"))
    col1, col2, col3 = st.columns(3)
    with col1:
        us_enabled = st.checkbox(t("settings.us_stocks"), value=settings.enable_us_stock)
    with col2:
        hk_enabled = st.checkbox(t("settings.hk_stocks"), value=settings.enable_hk_stock)
    with col3:
        a_enabled = st.checkbox(t("settings.a_shares"), value=settings.enable_a_stock)
    
    # Data settings
    st.header(t("settings.data_config"))
    col1, col2 = st.columns(2)
    with col1:
        data_years = st.slider(t("settings.data_years"), 1, 10, settings.data_years, help=t("help.data_years"))
    with col2:
        cache_ttl = st.slider(t("settings.cache_ttl"), 300, 7200, settings.data_cache_ttl)
    
    # Scoring weights
    st.header(t("settings.scoring_weights"))
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        trend_weight = st.slider(t("settings.trend"), 0.0, 1.0, settings.score_weight_trend, 0.05, help=t("help.trend_weight"))
    with col2:
        momentum_weight = st.slider(t("settings.momentum"), 0.0, 1.0, settings.score_weight_momentum, 0.05, help=t("help.momentum_weight"))
    with col3:
        volume_weight = st.slider(t("settings.volume"), 0.0, 1.0, settings.score_weight_volume, 0.05, help=t("help.volume_weight"))
    with col4:
        pattern_weight = st.slider(t("settings.pattern"), 0.0, 1.0, settings.score_weight_pattern, 0.05, help=t("help.pattern_weight"))
    
    # Signal legend expander
    with st.expander(t("help.signal_legend")):
        st.markdown(t("help.signal_legend"))
    
    # Validate weights
    total_weight = trend_weight + momentum_weight + volume_weight + pattern_weight
    if abs(total_weight - 1.0) > 0.01:
        st.warning(t("settings.weight_warning").format(total=total_weight))
    
    # Backtest settings
    st.header(t("settings.backtest_config"))
    col1, col2 = st.columns(2)
    with col1:
        holding_days = st.slider(t("settings.holding_days"), 5, 60, settings.backtest_holding_days, help=t("help.holding_days"))
    with col2:
        min_score = st.slider(t("settings.min_score"), 0, 100, settings.backtest_min_score, help=t("help.min_score"))
    
    # OFF Filter settings
    st.header(t("settings.off_filter"))
    col1, col2 = st.columns(2)
    with col1:
        atr_threshold = st.slider(t("settings.atr_threshold"), 0.01, 0.20, settings.off_atr_pct_threshold, 0.01)
    with col2:
        gap_threshold = st.slider(t("settings.gap_threshold"), 0.01, 0.30, settings.off_gap_threshold, 0.01)
    
    # Save button
    if st.button(t("settings.save"), type="primary"):
        st.success(t("settings.saved"))
        logger.info("Settings updated via UI")
