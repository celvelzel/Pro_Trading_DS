"""
Lobster Quant - Dashboard Page
OFF Filter status and market overview.
"""

import streamlit as st
import pandas as pd

from ...core.data_engine import get_data_engine
from ...core.risk_engine import RiskEngine
from ...core.indicator_engine import get_indicator_engine
from ...analysis.signals import SignalGenerator
from ...config.settings import get_settings
from ...utils.logging import get_logger
from ..components.cards import status_card, metric_card
from ..theme import theme_manager

logger = get_logger()


def render_dashboard():
    """Render the main dashboard page."""
    st.title("📊 Lobster Quant Dashboard")
    
    settings = get_settings()
    engine = get_data_engine()
    
    # Theme toggle
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🌓 Theme"):
            theme_manager.toggle_theme()
            st.rerun()
    
    # Market status section
    st.header("Market Status")
    
    try:
        # Fetch benchmark
        benchmark = engine.fetch_benchmark()
        if benchmark is None:
            st.error("Failed to fetch benchmark data")
            return
        
        # Compute indicators
        indicator_engine = get_indicator_engine()
        bench_with_indicators = indicator_engine.compute_all(benchmark.daily)
        
        # OFF Filter assessment
        risk_engine = RiskEngine()
        off_results = risk_engine.assess(bench_with_indicators)
        latest_status = risk_engine.get_latest_status(bench_with_indicators)
        
        # Display status
        col1, col2, col3 = st.columns(3)
        with col1:
            status_card(
                title="Market Condition",
                status=latest_status.status_text,
                is_good=latest_status.is_on,
                details=f"Reasons: {', '.join(latest_status.reasons) if latest_status.reasons else 'None'}"
            )
        
        with col2:
            latest_price = benchmark.get_latest_price()
            if latest_price:
                metric_card(
                    label=f"{settings.benchmark_symbol} Price",
                    value=f"${latest_price:.2f}"
                )
        
        with col3:
            stats = risk_engine.get_stats(bench_with_indicators, off_results)
            metric_card(
                label="ON/OFF Ratio",
                value=f"{stats['on_pct']:.1f}% / {stats['off_pct']:.1f}%"
            )
        
        # Historical OFF status chart
        st.subheader("Historical OFF Status")
        off_history = pd.DataFrame({
            'Date': bench_with_indicators.index,
            'OFF': off_results['is_off'].astype(int)
        })
        st.line_chart(off_history.set_index('Date'))
        
        # Reason distribution
        if latest_status.reasons:
            st.subheader("Current Risk Factors")
            for reason in latest_status.reasons:
                st.warning(f"⚠️ {reason}")
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        st.error(f"Error loading dashboard: {e}")
