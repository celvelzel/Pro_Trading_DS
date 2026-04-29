# Frontend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Streamlit frontend to support dynamic light/dark mode switching and unify the "Modern Trading" aesthetic.

**Architecture:** Introduce a centralized `theme_manager.py` for session-based `st.set_theme()` control. Refactor modular pages to use dynamic CSS injected from the theme manager.

**Tech Stack:** Streamlit, Plotly, Python.

---

### Task 1: Create Central Theme Manager

**Files:**
- Create: `theme_manager.py`
- Modify: `app.py`

- [ ] **Step 1: Implement `theme_manager.py`**

```python
import streamlit as st

def init_theme():
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    
    # Apply initial theme
    apply_theme(st.session_state.theme)

def apply_theme(theme_mode):
    if theme_mode == 'dark':
        st.set_theme(
            base="dark",
            primary_color="#00ff00", # Trading Green
            background_color="#0e1117",
            secondary_background_color="#1e222a",
            text_color="#fafafa"
        )
    else:
        st.set_theme(
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
```

- [ ] **Step 2: Update `app.py` to use Theme Manager**
Add `init_theme()` call at the top and the toggle in the sidebar.

```python
from theme_manager import init_theme, apply_theme
# ... after set_page_config
init_theme()

with st.sidebar:
    theme_toggle = st.toggle("Dark Mode", value=(st.session_state.theme == 'dark'))
    if theme_toggle:
        if st.session_state.theme != 'dark':
            st.session_state.theme = 'dark'
            apply_theme('dark')
            st.rerun()
    else:
        if st.session_state.theme != 'light':
            st.session_state.theme = 'light'
            apply_theme('light')
            st.rerun()
```

- [ ] **Step 3: Verify toggle state**
Expected: Toggling changes app background (except Quant Tool page which is still hardcoded).

### Task 2: Refactor Quant Tool Page for Dynamic Themes

**Files:**
- Modify: `quant_tool_page.py`
- Modify: `theme_manager.py` (add specific CSS helpers)

- [ ] **Step 1: Move custom CSS to `theme_manager.py`**
Extract the styles from `quant_tool_page.py` into a dynamic helper in `theme_manager.py`.

- [ ] **Step 2: Update `quant_tool_page.py`**
Replace the hardcoded style block with a call to `theme_manager.get_quant_tool_css()`.

- [ ] **Step 3: Verify Plotly charts in Quant Tool**
Ensure Plotly templates switch between `plotly_dark` and `plotly_white` based on `st.session_state.theme`.

### Task 3: Unify Aesthetic across all Tabs

**Files:**
- Modify: `app.py`
- Modify: `lobster_signal.py` (check if any UI strings need cleanup)

- [ ] **Step 1: Apply Card styling to metrics**
Wrap `st.metric` calls in `st.container()` to get the card look defined in Task 1.

- [ ] **Step 2: Final Verification**
Run `pytest` to ensure no logic was broken.
Manually verify light/dark consistency across all 5 tabs.
