"""
Lobster Quant - Card Components
Reusable card components for Streamlit UI.
"""

from typing import Optional, Any
import streamlit as st

from ..theme import theme_manager


def metric_card(label: str, 
                value: str, 
                delta: Optional[str] = None,
                delta_color: str = "normal") -> None:
    """Display a metric in a styled card.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta value
        delta_color: 'normal', 'inverse', or 'off'
    """
    st.markdown(theme_manager.get_card_style(), unsafe_allow_html=True)
    
    if delta:
        st.metric(label=label, value=value, delta=delta, delta_color=delta_color)
    else:
        st.metric(label=label, value=value)


def signal_card(signal_type: str, 
                score: float, 
                probability: float,
                reasons: list[str]) -> None:
    """Display a trading signal card.
    
    Args:
        signal_type: Signal classification
        score: Signal score (0-100)
        probability: Up probability (0-100)
        reasons: List of signal reasons
    """
    # Determine color based on signal
    if signal_type in ["强烈推荐", "推荐"]:
        color = "green"
        emoji = "🟢"
    elif signal_type == "持有":
        color = "yellow"
        emoji = "🟡"
    else:
        color = "gray"
        emoji = "⚪"
    
    st.markdown(f"""
    <div style="
        background-color: {'#1e222a' if theme_manager.current_theme == 'dark' else '#ffffff'};
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    ">
        <h3 style="margin: 0;">{emoji} {signal_type}</h3>
        <p style="margin: 0.5rem 0;">
            <strong>评分:</strong> {score:.0f}/100 | 
            <strong>上涨概率:</strong> {probability:.0f}%
        </p>
        <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">
            {' | '.join(reasons)}
        </p>
    </div>
    """, unsafe_allow_html=True)


def status_card(title: str, 
                status: str, 
                is_good: bool,
                details: Optional[str] = None) -> None:
    """Display a status card.
    
    Args:
        title: Card title
        status: Status text
        is_good: Whether the status is positive
        details: Optional details
    """
    color = "#4CAF50" if is_good else "#ff5252"
    emoji = "✅" if is_good else "❌"
    
    st.markdown(f"""
    <div style="
        background-color: {'#1e222a' if theme_manager.current_theme == 'dark' else '#ffffff'};
        border: 1px solid {color};
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    ">
        <h4 style="margin: 0; color: {color};">{emoji} {title}</h4>
        <p style="margin: 0.5rem 0; font-size: 1.2rem; font-weight: bold;">
            {status}
        </p>
        {f'<p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">{details}</p>' if details else ''}
    </div>
    """, unsafe_allow_html=True)
