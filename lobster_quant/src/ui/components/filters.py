"""
Lobster Quant - Filter Components
Reusable Streamlit filter components for the app.
"""

from typing import Optional, List
import streamlit as st


def market_filter(label: str = "Select Market", markets: Optional[List[str]] = None) -> str:
    """Streamlit selectbox for market selection.

    Args:
        label: Label for the selectbox
        markets: List of available markets (defaults to ["US Stocks", "HK Stocks", "A-Shares"])

    Returns:
        Selected market string
    """
    if markets is None:
        markets = ["US Stocks", "HK Stocks", "A-Shares"]

    selected = st.selectbox(label, markets)
    return selected


def score_range_filter(
    label: str = "Score Range",
    min_val: int = 0,
    max_val: int = 100,
    default_min: int = 0,
    default_max: int = 100
) -> tuple[int, int]:
    """Streamlit slider for min/max score range.

    Args:
        label: Label for the slider
        min_val: Minimum possible value
        max_val: Maximum possible value
        default_min: Default minimum value
        default_max: Default maximum value

    Returns:
        Tuple of (min_score, max_score)
    """
    col1, col2 = st.columns(2)

    with col1:
        min_score = st.number_input(
            f"{label} (Min)",
            min_value=min_val,
            max_value=max_val,
            value=default_min,
            step=1
        )

    with col2:
        max_score = st.number_input(
            f"{label} (Max)",
            min_value=min_val,
            max_value=max_val,
            value=default_max,
            step=1
        )

    # Ensure min <= max
    if min_score > max_score:
        min_score = max_score

    return (min_score, max_score)


def symbol_multiselect(
    label: str = "Select Symbols",
    available: Optional[List[str]] = None,
    default: Optional[List[str]] = None
) -> List[str]:
    """Streamlit multiselect for stock symbols.

    Args:
        label: Label for the multiselect
        available: List of available symbols to choose from
        default: Default selected symbols

    Returns:
        List of selected symbols
    """
    if available is None:
        available = []

    if default is None:
        default = []

    selected = st.multiselect(
        label,
        options=available,
        default=default
    )

    return selected