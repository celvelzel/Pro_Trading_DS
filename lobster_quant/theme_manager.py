import streamlit as st

# Monkeypatch st.set_theme to support dynamic theme switching
if not hasattr(st, 'set_theme'):
    def _set_theme(base, primary_color, background_color, secondary_background_color, text_color):
        st._config.set_option("theme.base", base)  # type: ignore
        st._config.set_option("theme.primaryColor", primary_color)  # type: ignore
        st._config.set_option("theme.backgroundColor", background_color)  # type: ignore
        st._config.set_option("theme.secondaryBackgroundColor", secondary_background_color)  # type: ignore
        st._config.set_option("theme.textColor", text_color)  # type: ignore
    st.set_theme = _set_theme  # type: ignore

def init_theme():
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    
    # Apply initial theme
    apply_theme(st.session_state.theme)

def apply_theme(theme_mode):
    if theme_mode == 'dark':
        st.set_theme(  # type: ignore
            base="dark",
            primary_color="#00ff00", # Trading Green
            background_color="#0e1117",
            secondary_background_color="#1e222a",
            text_color="#fafafa"
        )
    else:
        st.set_theme(  # type: ignore
            base="light",
            primary_color="#008000",
            background_color="#ffffff",
            secondary_background_color="#f0f2f6",
            text_color="#31333f"
        )

def get_card_style():
    theme = st.session_state.get('theme', 'light')
    if theme == 'dark':
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
    else:
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

def get_chart_colors():
    theme = st.session_state.get('theme', 'light')
    if theme == 'dark':
        return {
            'call_vol': '#4CAF50',
            'put_vol': '#ff5252',
            'call_oi': '#66bb6a',
            'put_oi': '#ef5350'
        }
    else:
        return {
            'call_vol': '#008000',
            'put_vol': '#d32f2f',
            'call_oi': '#388e3c',
            'put_oi': '#c62828'
        }

def get_quant_tool_css():
    theme = st.session_state.get('theme', 'light')
    if theme == 'dark':
        return """
        <style>
        /* Green accent for positive/profit */
        .green-text { color: #4CAF50; font-weight: bold; }
        /* Orange accent for warnings/risk */
        .orange-text { color: #ff9800; font-weight: bold; }
        
        /* Input and buttons styling */
        .stTextInput > div > div > input {
            background-color: #282e38;
            color: #ffffff;
            border-radius: 8px;
            border: 1px solid #4a5568;
        }
        .stTextInput > div > div > input:focus { border-color: #00ff00; }
        
        .stButton > button {
            border-radius: 8px;
        }
        
        /* Metrics styling to look like cards */
        [data-testid="stMetric"] {
            background-color: #1e222a;
            border: 1px solid #4a5568;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        }
        </style>
        """
    else:
        return """
        <style>
        /* Green accent for positive/profit */
        .green-text { color: #008000; font-weight: bold; }
        /* Orange accent for warnings/risk */
        .orange-text { color: #ff8c00; font-weight: bold; }
        
        /* Input and buttons styling */
        .stTextInput > div > div > input {
            background-color: #ffffff;
            color: #31333f;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .stTextInput > div > div > input:focus { border-color: #008000; }
        
        .stButton > button {
            border-radius: 8px;
        }
        
        /* Metrics styling to look like cards */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        </style>
        """
