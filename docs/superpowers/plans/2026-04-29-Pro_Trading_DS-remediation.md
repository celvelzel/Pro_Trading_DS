# Pro_Trading_DS Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix security vulnerabilities, improve code quality, unify design system, and ensure robust theming across the Pro_Trading_DS Streamlit application.

**Architecture:** This plan addresses 5 categories of issues identified by 5 parallel review agents. Priority is: Security (P0) → Correctness (P1) → Code Quality (P2) → Context/Gaps (P3) → Hardening (P4).

**Tech Stack:** Python, Streamlit, Plotly, yfinance

---

## Category 1: Security Issues (P0 - CRITICAL)

### Task 1.1: Fix Critical XSS via unsafe_allow_html

**Files:**
- Modify: `lobster_quant/app.py:137,141,254-261,306-316,356-362,451-462`
- Modify: `lobster_quant/quant_tool_page.py:102-108`
- Test: Manual verification required

**Issue:** The application uses `st.markdown(..., unsafe_allow_html=True)` with data from dynamic sources (stock data, user inputs). This allows potential XSS attacks.

**Fix Approach:**
1. Replace all `unsafe_allow_html=True` with explicit component rendering
2. Use `st.container()` with `st.metric()` instead of HTML injection
3. For colored text, use Streamlit's native `st.markdown()` with `help` parameter or delta colors

- [ ] **Step 1: Identify all unsafe_allow_html usage**

Run: `grep -r "unsafe_allow_html" lobster_quant/`
Document all locations that use this pattern.

- [ ] **Step 2: Replace HTML card style in app.py**

Replace pattern:
```python
# OLD (lines 136-141):
with col1.container():
    st.markdown(get_card_style(), unsafe_allow_html=True)
    st.metric("ON (Allowed)", f"{on_pct:.1f}%")

# NEW:
with col1.container():
    st.metric("ON (Allowed)", f"{on_pct:.1f}%")
```

- [ ] **Step 3: Replace CSS injection with Streamlit-native styling**

All `get_card_style()` calls should be removed. Use Streamlit's native container styling.

- [ ] **Step 4: Fix quant_tool_page.py colored text**

Replace:
```python
# OLD:
st.markdown(f'<p class="green-text">{on_probability:.0%}</p>', unsafe_allow_html=True)

# NEW:
st.markdown(f"**ON Probability:** {on_probability:.0%}")
```

- [ ] **Step 5: Verify no XSS vectors remain**

Run: `grep -r "unsafe_allow_html" lobster_quant/`
Expected: No results

---

### Task 1.2: Fix Cross-Session State Leakage from Monkeypatching

**Files:**
- Modify: `lobster_quant/theme_manager.py:1-12`
- Test: Verify theme isolation between sessions

**Issue:** The monkeypatch of `st.set_theme` modifies Streamlit's global `_config` object, causing state to leak across sessions.

**Fix Approach:**
1. Remove the monkeypatch entirely
2. Use Streamlit's `st._config.set_option()` directly (if required) with proper session state isolation
3. Alternative: Use query params or URL-based theme selection

- [ ] **Step 1: Remove unsafe monkeypatch**

```python
# REMOVE from theme_manager.py lines 3-11:
# Monkeypatch st.set_theme to support dynamic theme switching
if not hasattr(st, 'set_theme'):
    def _set_theme(base, primary_color, background_color, secondary_background_color, text_color):
        st._config.set_option("theme.base", base)
        ...
    st.set_theme = _set_theme
```

- [ ] **Step 2: Use query params for theme persistence**

Replace theme toggle logic in app.py with query parameter approach:
```python
# In app.py - use query params instead of session state
query_params = st.query_params
if 'theme' not in query_params:
    query_params['theme'] = 'light'

current_theme = query_params['theme']
# Toggle updates query params instead of session state
```

- [ ] **Step 3: Test session isolation**

Open two different browser sessions with different themes - verify no cross-contamination.

---

## Category 2: Code Quality Issues (P1 - HIGH)

### Task 2.1: Remove Private Streamlit API Usage

**Files:**
- Modify: `lobster_quant/theme_manager.py:6-10`
- Test: Verify theme still works

**Issue:** `st._config.set_option()` is a private API that may break in future Streamlit versions.

**Fix Approach:** Use only public Streamlit APIs or accept that theme switching has limitations.

- [ ] **Step 1: Document limitation or find public alternative**

Check Streamlit 1.40+ public theme APIs. If none exists, document the risk.

- [ ] **Step 2: Add warning comment**

```python
# WARNING: Using private API - may break in future Streamlit versions
# tracked in: https://github.com/streamlit/streamlit/issues/XXXX
st._config.set_option("theme.base", base)  # type: ignore
```

- [ ] **Step 3: Add to technical debt log**

Document this in `docs/technical-debt.md` for future migration.

---

### Task 2.2: Remove Global [data-testid="stMetric"] Styling

**Files:**
- Modify: `lobster_quant/theme_manager.py:105-111,136-142`
- Test: Verify metric display works

**Issue:** Global CSS selector `[data-testid="stMetric"]` affects ALL metrics in the app unintentionally.

**Fix Approach:** Use more specific selectors or Streamlit-native styling.

- [ ] **Step 1: Replace global selector with scoped class**

```python
# OLD:
[data-testid="stMetric"] {
    background-color: #1e222a;
    ...
}

# NEW:
.stCustomMetric {
    background-color: #1e222a;
    ...
}
```

- [ ] **Step 2: Add scoped CSS only where needed**

Apply the class only to specific containers in app.py.

---

## Category 3: Context/Gaps (P2 - MEDIUM)

### Task 3.1: Consolidate CSS Injection Points

**Files:**
- Modify: `lobster_quant/theme_manager.py`
- Create: `lobster_quant/styles.py`
- Test: Verify all styling still works

**Issue:** CSS is injected in multiple places (get_card_style, get_quant_tool_css), causing fragmentation.

**Fix Approach:** Create single unified style injection system.

- [ ] **Step 1: Create unified style manager**

```python
# lobster_quant/styles.py
def get_unified_css():
    """Returns all CSS in single injection point"""
    theme = st.session_state.get('theme', 'light')
    if theme == 'dark':
        return """
        <style>
        /* All styles consolidated here */
        .stContainer { ... }
        .green-text { ... }
        .custom-metric { ... }
        </style>
        """
    else:
        return ...
```

- [ ] **Step 2: Replace all CSS calls**

Replace:
- `get_card_style()` → `get_unified_css()` (one-time at app start)
- `get_quant_tool_css()` → removed (consolidated)

- [ ] **Step 3: Single injection point**

In app.py, inject once at startup:
```python
st.markdown(get_unified_css(), unsafe_allow_html=True)
```

---

### Task 3.2: Fix Toggle UX - Bidirectional Label

**Files:**
- Modify: `lobster_quant/app.py:26`
- Test: Verify toggle behavior

**Issue:** Toggle says "Dark Mode" but toggles OFF (unchecked = light, checked = dark). Confusing UX.

**Fix Approach:** Use clear label or two-way toggle.

- [ ] **Step 1: Update toggle label**

```python
# OLD:
theme_toggle = st.toggle("Dark Mode", value=(st.session_state.theme == 'dark'))

# NEW:
theme_toggle = st.toggle("🌙 Dark Mode", value=(st.session_state.theme == 'dark'))
st.caption("Toggle between light and dark themes")
```

Or use radio button for clarity:
```python
theme_mode = st.radio("Theme", ["light", "dark"], horizontal=True)
```

---

### Task 3.3: Add "Modern Trading (Minimal)" Style

**Files:**
- Extend: `lobster_quant/theme_manager.py`
- Test: Visual verification

**Issue:** User requested "Modern Trading (Minimal)" style is missing.

**Fix Approach:** Add this style definition alongside existing styles.

- [ ] **Step 1: Add minimal style definition**

```python
def apply_minimal_theme():
    """Minimal trading theme - clean, distraction-free"""
    theme = st.session_state.get('theme', 'light')
    if theme == 'dark':
        return {
            'primary': '#00ff00',
            'background': '#0a0a0a',
            'card_bg': '#141414',
            'text': '#e0e0e0'
        }
    else:
        return {
            'primary': '#006600',
            'background': '#ffffff',
            'card_bg': '#f8f9fa',
            'text': '#1a1a1a'
        }
```

- [ ] **Step 2: Add style selector to UI**

In sidebar:
```python
style_choice = st.selectbox(
    "Visual Style",
    ["Classic", "Modern Trading (Minimal)", "Trading Pro"]
)
```

---

### Task 3.4: Create Design Document

**Files:**
- Create: `docs/DESIGN.md`
- Test: Document exists

**Issue:** No explicit design document.

- [ ] **Step 1: Create DESIGN.md**

```markdown
# Pro_Trading_DS Design Document

## Visual Styles
- Classic: Original styling
- Modern Trading (Minimal): Clean, distraction-free
- Trading Pro: Full-featured trading terminal aesthetic

## Color Palette
| Theme | Primary | Background | Card | Text |
|-------|---------|------------|------|------|
| Dark | #00ff00 | #0e1117 | #1e222a | #fafafa |
| Light | #008000 | #ffffff | #f0f2f6 | #31333f |

## Typography
- Font: System default (Streamlit-managed)
- Headings: Bold, theme-adaptive

## Component Standards
- All metrics use native st.metric()
- No HTML injection except for Plotly charts
- Theme switch via query params
```

---

## Category 4: Goal Verification Issues (P3 - MEDIUM)

### Task 4.1: Verify Strict Light-Mode Default

**Files:**
- Modify: `lobster_quant/app.py:23`
- Test: Fresh session loads in light mode

**Issue:** Need to verify app defaults to light mode even if system preference is dark.

- [ ] **Step 1: Force light default**

```python
# Force light mode as default
if 'theme' not in st.query_params:
    st.query_params['theme'] = 'light'
```

- [ ] **Step 2: Verify default**

Open incognito window - verify light theme loads first.

---

### Task 4.2: Prevent Theme Flicker

**Files:**
- Modify: `lobster_quant/app.py:21-36`
- Test: No flash on reload

**Issue:** Theme flickers on page load before JavaScript executes.

**Fix Approach:** CSS-based theme pre-load.

- [ ] **Step 1: Add theme_preload.css**

```css
[data-theme="dark"] {
    /* Preload dark theme immediately via CSS */
}
```

- [ ] **Step 2: Inject in app.py before any content**

```python
st.set_page_config(layout="wide", page_title="Pro_Trading_DS")
# Inject CSS immediately after page config
st.markdown(get_theme_preload_css(), unsafe_allow_html=True)
```

---

### Task 4.3: Audit Chart Objects for Dynamic Theme Reading

**Files:**
- Modify: `lobster_quant/quant_tool_page.py:227-230`
- Test: Charts update on theme switch

**Issue:** Need to verify all Plotly charts read dynamic theme.

- [ ] **Step 1: Audit all plotly_chart calls**

Run: `grep -r "plotly_chart" lobster_quant/`
List all chart creation locations.

- [ ] **Step 2: Ensure theme-aware color scheme**

```python
# For each chart:
plotly_template = "plotly_dark" if theme == 'dark' else "plotly_white"
fig.update_layout(template=plotly_template)
```

- [ ] **Step 3: Test theme switch**

Toggle theme - verify charts update without page reload issues.

---

## Category 5: Hardening - Build on QA Success (P4 - LOW)

### Task 5.1: Add Error Boundaries

**Files:**
- Modify: All page modules
- Test: Graceful degradation

- [ ] **Step 1: Wrap data fetching in try-except**

```python
try:
    data = fetch_stock_data(code)
except Exception as e:
    st.error(f"Failed to load {code}: {e}")
    return
```

- [ ] **Step 2: Add fallback UI for empty data**

```python
if not stock_dict:
    st.warning("No data available")
    st.stop()
```

---

### Task 5.2: Add Performance Optimizations

- [ ] **Step 1: Cache expensive computations**

```python
@st.cache_data(ttl=3600)
def compute_expensive_metrics(...):
    ...
```

- [ ] **Step 2: Lazy load quant tool data**

Only fetch when user enters symbol.

---

### Task 5.3: Logging and Monitoring

**Files:**
- Modify: `lobster_quant/config.py`
- Test: Logs appear

- [ ] **Step 1: Add structured logging**

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Loaded {len(stock_dict)} stocks")
```

---

## Summary Table

| Task | Priority | Files | Effort | Verification |
|------|----------|-------|--------|--------------|
| 1.1 XSS Fix | P0 | app.py, quant_tool_page.py | 2h | No unsafe_allow_html |
| 1.2 State Leak | P0 | theme_manager.py | 1h | Session isolation test |
| 2.1 Private API | P1 | theme_manager.py | 0.5h | Theme still works |
| 2.2 Global CSS | P1 | theme_manager.py | 1h | Metrics display OK |
| 3.1 CSS Unify | P2 | theme_manager.py | 2h | Visual test |
| 3.2 Toggle UX | P2 | app.py | 0.5h | User testing |
| 3.3 Minimal Style | P2 | theme_manager.py | 2h | Visual test |
| 3.4 Design Doc | P2 | docs/DESIGN.md | 1h | Document exists |
| 4.1 Light Default | P3 | app.py | 0.5h | Fresh session test |
| 4.2 Prevent Flicker | P3 | app.py | 1h | No flash |
| 4.3 Chart Audit | P3 | quant_tool_page.py | 1h | Theme toggle test |
| 5.1 Error Boundaries | P4 | All pages | 2h | Error handling |
| 5.2 Performance | P4 | Various | 2h | Load time |
| 5.3 Logging | P4 | config.py | 1h | Log output |

**Total Estimated Effort:** ~16 hours

---

## Breaking Changes to Avoid

1. **DO NOT** change public API of `compute_score()`, `compute_off_filter()` - used externally
2. **DO NOT** rename files in `lobster_quant/` - may break imports
3. **DO NOT** remove any stock symbols from config without discussion
4. **DO NOT** change theme color values significantly - user expectations

---

## Verification Commands

```bash
# Security
grep -r "unsafe_allow_html" lobster_quant/

# Quality
python -m py_compile lobster_quant/*.py

# Context
ls -la docs/DESIGN.md

# Functional
streamlit run lobster_quant/app.py
```

---

## Plan Complete

**Two execution options:**

**1. Subagent-Driven (recommended)** - Dispatch fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**