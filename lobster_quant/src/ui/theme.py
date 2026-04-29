"""
Lobster Quant - Theme Manager
Centralized theme management for Streamlit UI.
"""

from typing import Dict, Any
import streamlit as st


# Monkeypatch st.set_theme if not available
if not hasattr(st, 'set_theme'):
    def _set_theme(base, primary_color, background_color, 
                   secondary_background_color, text_color):
        st._config.set_option("theme.base", base)
        st._config.set_option("theme.primaryColor", primary_color)
        st._config.set_option("theme.backgroundColor", background_color)
        st._config.set_option("theme.secondaryBackgroundColor", secondary_background_color)
        st._config.set_option("theme.textColor", text_color)
    st.set_theme = _set_theme


class ThemeManager:
    """Manage UI themes for Lobster Quant."""
    
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
        }
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
        }
    }
    
    def __init__(self):
        self._current_theme = 'light'
    
    def init_theme(self) -> None:
        """Initialize theme in session state."""
        if 'theme' not in st.session_state:
            st.session_state.theme = 'light'
        self.apply_theme(st.session_state.theme)
    
    def apply_theme(self, theme_name: str) -> None:
        """Apply theme to Streamlit.
        
        Args:
            theme_name: 'light' or 'dark'
        """
        if theme_name not in self.THEMES:
            theme_name = 'light'
        
        theme = self.THEMES[theme_name]
        st.set_theme(
            base=theme['base'],
            primary_color=theme['primary_color'],
            background_color=theme['background_color'],
            secondary_background_color=theme['secondary_background_color'],
            text_color=theme['text_color']
        )
        self._current_theme = theme_name
        st.session_state.theme = theme_name
    
    def toggle_theme(self) -> str:
        """Toggle between light and dark themes.
        
        Returns:
            New theme name
        """
        current = st.session_state.get('theme', 'light')
        new_theme = 'dark' if current == 'light' else 'light'
        self.apply_theme(new_theme)
        return new_theme
    
    @property
    def current_theme(self) -> str:
        """Get current theme name."""
        return st.session_state.get('theme', 'light')
    
    def get_chart_colors(self) -> Dict[str, str]:
        """Get chart colors for current theme."""
        return self.CHART_COLORS.get(self.current_theme, self.CHART_COLORS['light'])
    
    def get_card_style(self) -> str:
        """Get CSS for card components."""
        if self.current_theme == 'dark':
            return """
            <style>
            .stContainer {
                background-color: #1e222a;
                border: 1px solid #4a5568;
                border-radius: 8px;
                padding: 1rem;
            }
            </style>
            """
        return """
        <style>
        .stContainer {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }
        </style>
        """
    
    def get_css(self) -> str:
        """Get full CSS for Quant Tool page."""
        if self.current_theme == 'dark':
            return """
            <style>
            .green-text { color: #4CAF50; font-weight: bold; }
            .orange-text { color: #ff9800; font-weight: bold; }
            .stTextInput > div > div > input {
                background-color: #282e38;
                color: #ffffff;
                border-radius: 8px;
                border: 1px solid #4a5568;
            }
            .stTextInput > div > div > input:focus { border-color: #00ff00; }
            .stButton > button { border-radius: 8px; }
            [data-testid="stMetric"] {
                background-color: #1e222a;
                border: 1px solid #4a5568;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
            }
            </style>
            """
        return """
        <style>
        .green-text { color: #008000; font-weight: bold; }
        .orange-text { color: #ff8c00; font-weight: bold; }
        .stTextInput > div > div > input {
            background-color: #ffffff;
            color: #31333f;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .stTextInput > div > div > input:focus { border-color: #008000; }
        .stButton > button { border-radius: 8px; }
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        </style>
        """


# Global theme manager instance
theme_manager = ThemeManager()
