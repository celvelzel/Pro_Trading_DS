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

## Module Architecture (Updated 2026-05-26)

### Core Modules

```
lobster_quant/src/
├── analysis/                    # 分析模块
│   ├── backtest/               # 回测模块 (统一)
│   │   ├── __init__.py         # 导出所有回测相关类和函数
│   │   ├── engine.py           # BacktestEngine (单股票回测)
│   │   ├── portfolio.py        # PortfolioBacktest (组合回测)
│   │   └── metrics.py          # 指标计算函数 (统一)
│   ├── indicators/             # 技术指标
│   └── signals/                # 信号生成
├── core/                        # 核心业务逻辑
│   ├── data_engine.py          # 数据引擎
│   ├── indicator_engine.py     # 指标引擎
│   ├── signal_engine.py        # 信号引擎
│   ├── scoring_engine.py       # 评分引擎
│   ├── risk_engine.py          # 风险引擎
│   ├── strategy_manager.py     # 策略管理
│   ├── trade_simulator.py      # 交易模拟
│   ├── scheduler.py            # 调度器
│   └── events.py               # 事件系统
├── data/                        # 数据层
├── storage/                     # 存储层
└── utils/                       # 工具函数
```

### Key Design Decisions

1. **回测模块统一**: 所有回测相关功能（单股票、组合回测、指标计算）统一到 `analysis/backtest/` 模块
2. **指标计算统一**: 所有指标计算函数统一到 `analysis/backtest/metrics.py`
3. **职责清晰**: 
   - `analysis/backtest/` 负责回测逻辑
   - `core/` 负责业务逻辑和引擎
   - `data/` 负责数据获取和缓存
   - `storage/` 负责持久化存储
