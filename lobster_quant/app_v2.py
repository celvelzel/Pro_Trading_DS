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
    render_quant_tool,
)
from src.ui.theme import theme_manager
from src.utils.i18n import t, get_language
from src.utils.logging import setup_logging, get_logger

# Initialize
setup_logging(level="INFO")
logger = get_logger()
theme_manager.init_theme()


def main():
    """Main application entry point."""
    
    # Sidebar navigation
    with st.sidebar:
        st.title(t("app.title"))
        st.caption(t("app.version"))
        st.caption(t("app.subtitle"))
        
        # Language selector
        lang = st.selectbox("Language / 语言", ["zh", "en"], 
                             index=0 if get_language() == "zh" else 1,
                             key="language_selector")
        st.session_state.language = lang
        
        # Theme toggle
        if st.button("🌓 Toggle Theme"):
            theme_manager.toggle_theme()
            st.rerun()
        
        st.divider()
        
        # Navigation
        page = st.radio(
            "Navigation",
            options=[
                t("nav.dashboard"),
                t("nav.scanner"),
                t("nav.analyzer"),
                t("nav.backtest"),
                t("nav.quant_tool"),
                t("nav.settings"),
            ],
            index=0,
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Info
        st.caption(t("app.built_with"))
        st.caption(t("app.phase_complete"))

    # Route to page
    page_map = {
        t("nav.dashboard"): render_dashboard,
        t("nav.scanner"): render_scanner,
        t("nav.analyzer"): render_analyzer,
        t("nav.backtest"): render_backtest,
        t("nav.quant_tool"): render_quant_tool,
        t("nav.settings"): render_settings,
    }
    
    page_func = page_map.get(page, render_dashboard)
    page_func()


if __name__ == "__main__":
    main()