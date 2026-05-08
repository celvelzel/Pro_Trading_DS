"""
Lobster Quant - Card Components
Reusable card components for Streamlit UI.
"""

from typing import Optional
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
    with st.container():
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
    if signal_type in ["强烈推荐", "推荐"]:
        emoji = "🟢"
        delta = "positive"
    elif signal_type == "持有":
        emoji = "🟡"
        delta = "neutral"
    else:
        emoji = "⚪"
        delta = "negative"

    with st.container():
        st.markdown(f"### {emoji} {signal_type}")
        st.metric(
            label="评分 / 上涨概率",
            value=f"{score:.0f}/100",
            delta=f"概率 {probability:.0f}%",
            delta_color="normal" if probability >= 60 else "inverse",
        )
        if reasons:
            st.caption(" | ".join(reasons))


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
    emoji = "✅" if is_good else "❌"

    with st.container():
        st.markdown(f"#### {emoji} {title}")
        st.markdown(f"**{status}**")
        if details:
            st.caption(details)
