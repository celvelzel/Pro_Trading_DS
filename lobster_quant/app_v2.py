"""
Lobster Quant v2.0 - Streamlit Application Entry Point
Modern, modular Streamlit app with multi-page support.
"""

import streamlit as st

# Configure page
st.set_page_config(
    page_title="Lobster Quant",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import after page config
from src.ui.pages import (
    render_dashboard,
    render_scanner,
    render_analyzer,
    render_backtest,
    render_settings,
)
from src.ui.theme import theme_manager
from src.utils.logging import setup_logging, get_logger

# Initialize
setup_logging(level="INFO")
logger = get_logger()
theme_manager.init_theme()


def main():
    """Main application entry point."""
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🦞 Lobster Quant")
        st.caption("v2.0.0 - Modular Architecture")
        
        # Theme toggle
        if st.button("🌓 Toggle Theme"):
            theme_manager.toggle_theme()
            st.rerun()
        
        st.divider()
        
        # Navigation
        page = st.radio(
            "Navigation",
            options=[
                "📊 Dashboard",
                "🔍 Scanner",
                "📈 Analyzer",
                "🧪 Backtest",
                "⚙️ Settings",
            ],
            index=0,
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Info
        st.caption("Built with modern architecture")
        st.caption("Phase 1 & 2 Complete")

    # Route to page
    page_map = {
        "📊 Dashboard": render_dashboard,
        "🔍 Scanner": render_scanner,
        "📈 Analyzer": render_analyzer,
        "🧪 Backtest": render_backtest,
        "⚙️ Settings": render_settings,
    }
    
    page_func = page_map.get(page, render_dashboard)
    page_func()


if __name__ == "__main__":
    main()