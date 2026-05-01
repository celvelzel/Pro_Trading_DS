"""
Lobster Quant - Help Component
Reusable page help intro with expandable section.
"""

import streamlit as st

from ..help_content import PAGE_INTROS, PAGE_PARAMS


def render_page_help(page_key: str) -> None:
    """Render an expandable help section at the top of a page.

    Args:
        page_key: Key into PAGE_INTROS dict (e.g. "dashboard", "scanner").
    """
    intro = PAGE_INTROS.get(page_key)
    if not intro:
        return

    with st.expander("📖 使用说明", expanded=False):
        st.markdown(intro)


def get_param_help(page_key: str, param_key: str) -> str:
    """Get help text for a specific parameter.

    Args:
        page_key: Key into PAGE_PARAMS dict (e.g. "scanner").
        param_key: Key into the page's params dict (e.g. "min_score").

    Returns:
        Help text string, or empty string if not found.
    """
    params = PAGE_PARAMS.get(page_key, {})
    return params.get(param_key, "")
