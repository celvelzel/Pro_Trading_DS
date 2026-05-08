# Pro_Trading_DS Design Document

## Visual Styles

| Style | Description |
|-------|-------------|
| Classic Light | Default. Clean, professional trading interface |
| Classic Dark | High-contrast dark theme for low-light environments |
| Modern Trading (Minimal) Light | Distraction-free, minimal chrome |
| Modern Trading (Minimal) Dark | Ultra-clean dark theme with subtle accents |

## Color Palette

| Theme | Primary | Background | Card | Text |
|-------|---------|------------|------|------|
| Light | #008000 | #ffffff | #f0f2f6 | #31333f |
| Dark | #00ff00 | #0e1117 | #1e222a | #fafafa |
| Minimal Light | #006600 | #ffffff | #f8f9fa | #1a1a1a |
| Minimal Dark | #00ff00 | #0a0a0a | #141414 | #e0e0e0 |

## Chart Colors

| Element | Light | Dark |
|---------|-------|------|
| Call Volume | #008000 | #4CAF50 |
| Put Volume | #d32f2f | #ff5252 |
| Call OI | #388e3c | #66bb6a |
| Put OI | #c62828 | #ef5350 |
| Up | #008000 | #4CAF50 |
| Down | #d32f2f | #ff5252 |

## Typography

- Font: System default (Streamlit-managed)
- Headings: Bold, theme-adaptive via Plotly template

## Component Standards

- All metrics use native `st.metric()` - no HTML injection
- Cards use native `st.container()` - no custom CSS classes
- Charts use Plotly templates (`plotly_dark` / `plotly_white`)
- Theme persisted via query params (`?theme=dark`)
- Default theme: light (strict)
- No monkeypatching of Streamlit internals

## Architecture

```
src/ui/
  theme.py          - ThemeManager singleton (themes, chart colors, Plotly templates)
  components/
    cards.py        - metric_card(), signal_card(), status_card() using native Streamlit
    charts.py       - candlestick_chart(), volume_chart(), indicator_chart(), equity_curve_chart()
  pages/
    dashboard.py    - Main dashboard
    scanner.py      - Stock scanner
    analyzer.py     - Stock analyzer
    backtest.py     - Backtesting engine
    quant_tool.py   - Quantitative analysis tool
    settings.py     - App settings
```
