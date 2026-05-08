"""
Lobster Quant - Theme Manager
Centralized theme management for Streamlit UI.
"""

from typing import Dict
import streamlit as st


class ThemeManager:
    """Manage UI themes for Lobster Quant.

    Theme is persisted via query params to avoid cross-session state leakage.
    Uses only public Streamlit APIs.
    """

    THEMES = {
        'light': {
            'base': 'light',
            'primary_color': '#008000',
            'background_color': '#ffffff',
            'secondary_background_color': '#f0f2f6',
            'text_color': '#31333f',
        },
        'dark': {
            'base': 'dark',
            'primary_color': '#00ff00',
            'background_color': '#0e1117',
            'secondary_background_color': '#1e222a',
            'text_color': '#fafafa',
        },
        'minimal_light': {
            'base': 'light',
            'primary_color': '#006600',
            'background_color': '#ffffff',
            'secondary_background_color': '#f8f9fa',
            'text_color': '#1a1a1a',
        },
        'minimal_dark': {
            'base': 'dark',
            'primary_color': '#00ff00',
            'background_color': '#0a0a0a',
            'secondary_background_color': '#141414',
            'text_color': '#e0e0e0',
        },
    }

    CHART_COLORS = {
        'light': {
            'call_vol': '#008000',
            'put_vol': '#d32f2f',
            'call_oi': '#388e3c',
            'put_oi': '#c62828',
            'up': '#008000',
            'down': '#d32f2f',
            'neutral': '#757575',
        },
        'dark': {
            'call_vol': '#4CAF50',
            'put_vol': '#ff5252',
            'call_oi': '#66bb6a',
            'put_oi': '#ef5350',
            'up': '#4CAF50',
            'down': '#ff5252',
            'neutral': '#9e9e9e',
        },
    }

    def init_theme(self) -> None:
        """Initialize theme from query params. Defaults to 'light'."""
        params = st.query_params
        theme = params.get("theme", "light")
        if theme not in self.THEMES:
            theme = "light"
        st.session_state["theme"] = theme

    def apply_theme(self, theme_name: str) -> None:
        """Apply theme by updating session state and query params."""
        if theme_name not in self.THEMES:
            theme_name = "light"
        st.session_state["theme"] = theme_name
        st.query_params["theme"] = theme_name

    def toggle_theme(self) -> str:
        """Toggle between light and dark themes.

        Returns:
            New theme name
        """
        current = st.session_state.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self.apply_theme(new_theme)
        return new_theme

    @property
    def current_theme(self) -> str:
        """Get current theme name."""
        return st.session_state.get("theme", "light")

    def get_chart_colors(self) -> Dict[str, str]:
        """Get chart colors for current theme."""
        return self.CHART_COLORS.get(self.current_theme, self.CHART_COLORS['light'])

    def get_plotly_template(self) -> str:
        """Get Plotly template name for current theme."""
        if self.current_theme in ('dark', 'minimal_dark'):
            return 'plotly_dark'
        return 'plotly_white'

    def get_font_color(self) -> str:
        """Get font color for charts based on current theme."""
        if self.current_theme in ('dark', 'minimal_dark'):
            return '#ffffff'
        return '#31333f'


# Global theme manager instance
theme_manager = ThemeManager()
