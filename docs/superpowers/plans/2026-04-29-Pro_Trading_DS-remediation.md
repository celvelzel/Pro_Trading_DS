# Pro_Trading_DS Remediation Implementation Plan

> **Status:** COMPLETED (all tasks done)
> **Completed:** 2026-05-08

**Goal:** Fix security vulnerabilities, improve code quality, unify design system, and ensure robust theming across the Pro_Trading_DS Streamlit application.

**Architecture:** This plan addresses 5 categories of issues identified by 5 parallel review agents. Priority is: Security (P0) → Correctness (P1) → Code Quality (P2) → Context/Gaps (P3) → Hardening (P4).

**Tech Stack:** Python, Streamlit, Plotly, yfinance

> **Note:** The codebase was refactored during implementation. Original file paths (`app.py`, `theme_manager.py`, `quant_tool_page.py`) no longer exist. Actual paths are used below.

---

## Category 1: Security Issues (P0 - CRITICAL)

### Task 1.1: Fix Critical XSS via unsafe_allow_html

**Files:**
- Modify: `lobster_quant/src/ui/pages/quant_tool.py:33,103-106,111-113`
- Modify: `lobster_quant/src/ui/components/cards.py:24,55-72,90-104`
- Test: `grep -r "unsafe_allow_html" lobster_quant/` → No results

- [x] **Step 1:** Removed all `unsafe_allow_html=True` from `quant_tool.py` (CSS injection at line 33, colored HTML text at lines 103-106, 111-113)
- [x] **Step 2:** Replaced HTML card components in `cards.py` with native `st.metric()` and `st.container()`
- [x] **Step 3:** Verified no XSS vectors remain

---

### Task 1.2: Fix Cross-Session State Leakage from Monkeypatching

**Files:**
- Modify: `lobster_quant/src/ui/theme.py:10-19`
- Test: Theme persisted via query params → session isolation

- [x] **Step 1:** Removed monkeypatch (`if not hasattr(st, 'set_theme')`) entirely
- [x] **Step 2:** Theme now persists via `st.query_params` instead of monkeypatched `st.set_theme`
- [x] **Step 3:** Verified session isolation (query params are per-URL, not per-session)

---

## Category 2: Code Quality Issues (P1 - HIGH)

### Task 2.1: Remove Private Streamlit API Usage

**Files:**
- Modify: `lobster_quant/src/ui/theme.py`
- Test: Theme still works

- [x] **Step 1:** Removed all `st._config.set_option()` calls
- [x] **Step 2:** No private APIs remain in codebase

---

### Task 2.2: Remove Global [data-testid="stMetric"] Styling

**Files:**
- Modify: `lobster_quant/src/ui/theme.py`
- Test: Metrics display OK

- [x] **Step 1:** Removed `get_css()` method containing global `[data-testid="stMetric"]` selector
- [x] **Step 2:** Removed `get_card_style()` method containing global `.stContainer` override
- [x] **Step 3:** All custom CSS classes (`green-text`, `orange-text`) removed from theme.py

---

## Category 3: Context/Gaps (P2 - MEDIUM)

### Task 3.1: Consolidate CSS Injection Points

**Files:**
- Modify: `lobster_quant/src/ui/theme.py`
- Test: No CSS injection via `unsafe_allow_html`

- [x] **Step 1:** Removed `get_card_style()` and `get_css()` from `ThemeManager`
- [x] **Step 2:** CSS is now handled by Streamlit's native theming (Plotly templates) + native components
- [x] **Step 3:** Zero `unsafe_allow_html` calls in entire codebase

---

### Task 3.2: Fix Toggle UX - Bidirectional Label

**Files:**
- Modify: `lobster_quant/app_v2.py:43-45`
- Test: Toggle label reflects current state

- [x] **Step 1:** Changed button label from static "Toggle Theme" to dynamic "🌙 Dark Mode" / "☀️ Light Mode"

---

### Task 3.3: Add "Modern Trading (Minimal)" Style

**Files:**
- Modify: `lobster_quant/src/ui/theme.py:25-50`
- Test: Four themes available

- [x] **Step 1:** Added `minimal_light` and `minimal_dark` theme definitions to `ThemeManager.THEMES`
- [x] **Step 2:** Themes use distinct colors: minimal_light (#006600 primary, #f8f9fa card), minimal_dark (#0a0a0a background, #141414 card)

---

### Task 3.4: Create Design Document

**Files:**
- Create: `docs/DESIGN.md`

- [x] **Step 1:** Created `docs/DESIGN.md` with color palettes, chart colors, typography, component standards, and architecture overview

---

## Category 4: Goal Verification Issues (P3 - MEDIUM)

### Task 4.1: Verify Strict Light-Mode Default

**Files:**
- Modify: `lobster_quant/src/ui/theme.py:66-71`
- Test: Fresh session defaults to light

- [x] **Step 1:** `init_theme()` defaults to `'light'` when no query param exists
- [x] **Step 2:** Verified default behavior

---

### Task 4.2: Prevent Theme Flicker

**Files:**
- Modify: `lobster_quant/src/ui/theme.py`
- Test: No flash on reload

- [x] **Step 1:** Theme loaded from `st.query_params` (URL-based) on first render - no JavaScript flicker
- [x] **Step 2:** No CSS pre-load injection needed since query params resolve immediately

---

### Task 4.3: Audit Chart Objects for Dynamic Theme Reading

**Files:**
- Modify: `lobster_quant/src/ui/components/charts.py:93-99,129-137,266-274,302-310`
- Modify: `lobster_quant/src/ui/pages/quant_tool.py:258-261`
- Test: Charts update on theme switch

- [x] **Step 1:** Audited all `plotly_chart` calls (5 locations: quant_tool x2, analyzer x2, backtest x1)
- [x] **Step 2:** Added `theme_manager.get_plotly_template()` and `theme_manager.get_font_color()` to all chart functions in `charts.py`
- [x] **Step 3:** Simplified `quant_tool.py` inline theme logic to use new helper methods

---

## Category 5: Hardening - Build on QA Success (P4 - LOW)

### Task 5.1: Add Error Boundaries

**Files:**
- All page modules already have try-except blocks

- [x] **Step 1:** All pages (dashboard, scanner, analyzer, backtest, quant_tool) already wrapped in try-except with `st.error()` fallback

---

### Task 5.2: Add Performance Optimizations

- [x] **Step 1:** Caching already implemented via `src/data/cache.py` with TTL support
- [x] **Step 2:** Quant tool data already lazy-loaded (only fetches on button click)

---

### Task 5.3: Logging and Monitoring

**Files:**
- `lobster_quant/src/utils/logging.py` - already implemented

- [x] **Step 1:** Structured logging with `ColoredFormatter`, file + console output, daily log rotation already in place

---

## Summary Table

| Task | Priority | Status | Files Modified |
|------|----------|--------|----------------|
| 1.1 XSS Fix | P0 | ✅ Done | quant_tool.py, cards.py |
| 1.2 State Leak | P0 | ✅ Done | theme.py |
| 2.1 Private API | P1 | ✅ Done | theme.py |
| 2.2 Global CSS | P1 | ✅ Done | theme.py |
| 3.1 CSS Unify | P2 | ✅ Done | theme.py, cards.py |
| 3.2 Toggle UX | P2 | ✅ Done | app_v2.py |
| 3.3 Minimal Style | P2 | ✅ Done | theme.py |
| 3.4 Design Doc | P2 | ✅ Done | docs/DESIGN.md |
| 4.1 Light Default | P3 | ✅ Done | theme.py |
| 4.2 Prevent Flicker | P3 | ✅ Done | theme.py |
| 4.3 Chart Audit | P3 | ✅ Done | charts.py, quant_tool.py |
| 5.1 Error Boundaries | P4 | ✅ Already done | - |
| 5.2 Performance | P4 | ✅ Already done | - |
| 5.3 Logging | P4 | ✅ Already done | - |

---

## Breaking Changes to Avoid

1. **DO NOT** change public API of `compute_score()`, `compute_off_filter()` - used externally
2. **DO NOT** rename files in `lobster_quant/` - may break imports
3. **DO NOT** remove any stock symbols from config without discussion
4. **DO NOT** change theme color values significantly - user expectations

---

## Verification Results

```bash
# Security - PASS (0 results)
grep -r "unsafe_allow_html" lobster_quant/
# → No matches found

# Quality - PASS (all compile)
python -m py_compile lobster_quant/src/ui/theme.py
python -m py_compile lobster_quant/src/ui/components/cards.py
python -m py_compile lobster_quant/src/ui/components/charts.py
python -m py_compile lobster_quant/src/ui/pages/quant_tool.py
python -m py_compile lobster_quant/app_v2.py

# Tests - PASS (153/153)
python -m pytest lobster_quant/tests/ -v
# → 153 passed, 1 warning

# Context - PASS
ls -la docs/DESIGN.md
# → File exists
```

---

## Plan Complete

**Execution method:** Inline execution in current session.
