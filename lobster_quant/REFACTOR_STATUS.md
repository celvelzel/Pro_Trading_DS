# Lobster Quant - Refactoring Status & Remaining Plan

> 生成时间: 2026-04-29
> 用途: 给其他 agent 继续完成的清晰指南

---

## 一、已完成的工作

| 阶段 | 模块 | 文件 | 状态 |
|------|------|------|------|
| Phase 1 | 数据模型 | `src/data/models.py` | ✅ Pydantic v2 模型 (OHLCV, StockData, SignalResult, Trade, OFFStatus, OptionsData, MarketSnapshot, HealthStatus) |
| Phase 1 | 数据源抽象 | `src/data/providers/base.py` | ✅ DataProvider 抽象基类 + DataProviderFactory 工厂模式 |
| Phase 1 | yfinance 适配器 | `src/data/providers/yfinance_provider.py` | ✅ |
| Phase 1 | akshare 适配器 | `src/data/providers/akshare_provider.py` | ✅ |
| Phase 1 | Mock 适配器 | `src/data/providers/mock_provider.py` | ✅ |
| Phase 1 | 缓存系统 | `src/data/cache.py` | ✅ 内存+磁盘双缓存 |
| Phase 1 | 配置管理 | `src/config/settings.py` | ✅ Pydantic Settings + .env 支持 |
| Phase 1 | 结构化日志 | `src/utils/logging.py` | ✅ |
| Phase 1 | 异常体系 | `src/utils/exceptions.py` | ✅ 完整异常树 (LobsterQuantError → DataError/AnalysisError/RiskError/ConfigError 等) |
| Phase 1+2 | 指标计算引擎 | `src/core/indicator_engine.py` + `src/analysis/indicators/{base,trend,momentum,volume,volatility}.py` | ✅ IndicatorRegistry 注册表模式 |
| Phase 1+2 | 信号生成 | `src/analysis/signals/lobster_signal.py` | ✅ SignalGenerator 类 (趋势/动量/成交量/形态评分) |
| Phase 1+2 | 回测引擎 | `src/analysis/backtest/engine.py` | ✅ BacktestEngine (含滑点+手续费) |
| Phase 1+2 | 风控引擎 | `src/core/risk_engine.py` | ✅ OFF Filter 风控逻辑 |
| Phase 1+2 | 评分引擎 | `src/core/scoring_engine.py` | ✅ ScoringEngine 类 (趋势40%/动量20%/成交量15%/形态25%) |
| Phase 1+2 | 事件总线 | `src/core/events.py` | ✅ EventBus + EventType 枚举 |
| Phase 1+2 | 数据引擎 | `src/core/data_engine.py` | ✅ DataEngine (抽象层+缓存+异步批量) |
| Phase 1+2 | Quant Tool 页面 | `src/ui/pages/quant_tool.py` | ✅ 期权分析/ OFF 评估/期权链图表 (从旧 quant_tool_page.py 迁移) |
| Phase 1+2 | Quant Tool 指标 | `src/ui/pages/quant_tool_indicators.py` | ✅ 6个独立指标函数 (从旧 quant_tool_indicators.py 迁移) |
| Phase 1 | 兼容层 | `src/compat.py` | ✅ LegacyAdapter 向后兼容旧 API |
| Phase 2 | 主题管理 | `src/ui/theme.py` | ✅ ThemeManager (含 CSS + 图表配色) |
| Phase 2 | 页面组件 | `src/ui/pages/{dashboard,scanner,analyzer,backtest,settings}.py` | ✅ 5个 Streamlit 页面 |
| Phase 2 | UI 卡片组件 | `src/ui/components/cards.py` | ✅ |
| Phase 2 | 入口 | `app_v2.py` | ✅ 新的模块化入口 |

### 已修复的 Bug

| Bug | 位置 | 修复 |
|-----|------|------|
| ❌ 字符串损坏 | `risk_engine.py:78` | `checks['MA200恢复�?]` → `checks['MA200恢复']` |
| ❌ 字符串损坏 | `scanner.py:149` | `'Prob �?'` → `'Prob Up'` |
| ❌ 语法未闭合 | `backtest.py` | DataFrame 列表未闭合 → 补全缺失代码 |

---

## 二、剩余 Plan 1-2 缺口（按优先级）

### 🔴 优先级 1: Missing Core Modules

#### 1.1 `src/core/signal_engine.py` — 信号引擎
- **描述**: 从 `src/analysis/signals/lobster_signal.py` 的 SignalGenerator 中提取核心逻辑
- **职责**: 调用 IndicatorEngine → ScoringEngine → SignalGenerator 的编排层
- **参考**: `src/core/indicator_engine.py` 的 get_indicator_engine() 单例模式
- **代码模式**:
```python
class SignalEngine:
    def __init__(self):
        self.indicator_engine = get_indicator_engine()
        self.scoring_engine = get_scoring_engine()
    
    def generate_signal(self, stock_data: StockData) -> SignalResult:
        df = self.indicator_engine.compute_all(stock_data.daily)
        score = self.scoring_engine.compute_score(df)
        signal = self._classify_signal(score)
        return signal
    
    def _classify_signal(self, score: float) -> SignalResult: ...
```

#### 1.2 `src/ui/components/charts.py` — 图表组件
- **描述**: 可复用的 Plotly 图表组件
- **导出函数**: `candlestick_chart()`, `volume_chart()`, `indicator_chart()`, `equity_curve_chart()`
- **参考**: `src/ui/pages/analyzer.py` 中的图表代码 (约 100-213 行)
- **模式**: 接受 DataFrame + 参数 → 返回 go.Figure

#### 1.3 `src/ui/components/filters.py` — 过滤器组件
- **描述**: Streamlit 过滤器 UI 组件
- **导出函数**: `market_filter()`, `score_range_filter()`, `symbol_multiselect()`
- **参考**: `src/ui/pages/scanner.py` 中的过滤器逻辑

#### 1.4 `src/analysis/backtest/metrics.py` — 回测指标
- **描述**: 独立的回测指标计算函数
- **导出函数**: `calculate_sharpe_ratio()`, `calculate_sortino_ratio()`, `calculate_max_drawdown()`, `calculate_profit_factor()`, `calculate_win_rate()`
- **参考**: `src/analysis/backtest/engine.py` 中的指标计算逻辑

### 🟡 优先级 2: Config Layer

#### 2.1 `src/config/defaults.yaml` — 默认配置
- **描述**: 默认配置的 YAML 文件
- **内容**: 复制 `src/config/settings.py` 中的默认值到 YAML 格式

#### 2.2 `src/config/validation.py` — 配置校验
- **描述**: 配置校验工具
- **导出函数**: `validate_settings(settings)`, `validate_weight_sum(weights)`, `validate_market_config(markets)`
- **参考**: `src/config/settings.py` 中已有的 validators

### 🟡 优先级 3: Utils 补充

#### 3.1 `src/utils/validators.py` — 通用校验工具
- **描述**: 数据校验工具
- **导出函数**: `validate_symbol()`, `validate_date_range()`, `validate_dataframe_columns()`, `validate_timeframe()`

### 🟢 优先级 4: 信号系统补充

#### 4.1 `src/analysis/signals/composite_signal.py` — 复合信号
- **描述**: 综合多个信号源的复合信号生成器
- **职责**: 聚合 SignalGenerator + ScoringEngine + RiskEngine 的结果输出统一信号

---

## 三、已发现的 Pre-existing Bugs（需修复后测试通过）

### Bug 1: `src/ui/pages/backtest.py` — DataFrame 语法未闭合
- **位置**: 行 136-144
- **症状**: `pd.DataFrame([{...}]` 缺少 `for t in result.trades])` 和后续的 `st.dataframe()` 调用
- **修复**: 需要补全缺失代码：
```python
trades_df = pd.DataFrame([
    {
        'Buy Date': t.buy_date.strftime('%Y-%m-%d'),
        'Buy Price': f"${t.buy_price:.2f}",
        'Sell Date': t.sell_date.strftime('%Y-%m-%d') if t.sell_date else 'Open',
        'Sell Price': f"${t.sell_price:.2f}" if t.sell_price else 'Open',
        'Return': f"{t.return_pct*100:.2f}%" if t.return_pct else 'N/A',
        'Days': t.holding_days
    }
    for t in result.trades
])
st.dataframe(trades_df, use_container_width=True)
```

### Bug 2: `tests/integration/test_e2e.py` — 导入路径
- **修复完成**: 已经改为 `from src.*` 前缀导入
- `conftest.py` 的 `sys.path` 改为指向项目根目录

---

## 四、遗留根目录文件（不再引用的旧文件）

以下文件在 `app_v2.py` (新入口) 中不再引用，可以安全删除：

| 文件 | 替代 | 删除条件 |
|------|------|---------|
| `app.py` | `app_v2.py` | 确认无外部引用后删除 |
| `scoring.py` | `src/core/scoring_engine.py` | ✅ 可删除 |
| `quant_tool_page.py` | `src/ui/pages/quant_tool.py` | ✅ 可删除 |
| `quant_tool_data.py` | 内联到 `quant_tool.py` | ✅ 可删除 |
| `quant_tool_indicators.py` | `src/ui/pages/quant_tool_indicators.py` | ✅ 可删除 |
| `theme_manager.py` | `src/ui/theme.py` | ✅ 可删除 |
| `config.py` | `src/config/settings.py` | ⚠️ 需确认旧 app.py 已无引用 |
| `data_fetcher.py` | `src/data/providers/yfinance_provider.py` | ⚠️ 同上 |
| `indicators.py` | `src/analysis/indicators/` | ⚠️ 同上 |
| `off_filter.py` | `src/core/risk_engine.py` | ⚠️ 同上 |
| `lobster_off_filter.py` | `src/core/risk_engine.py` | ⚠️ 同上 |
| `lobster_signal.py` | `src/analysis/signals/lobster_signal.py` | ⚠️ 同上 |
| `backtest.py` | `src/analysis/backtest/engine.py` | ⚠️ 同上 |

---

## 五、测试状态

```
tests/
├── conftest.py                    # ✅ 配置 (已修复导入路径)
├── unit/
│   ├── test_models.py             # 存在
│   ├── test_indicators.py         # 存在
│   ├── test_signal_generator.py   # 存在
│   ├── test_backtest_engine.py    # 存在
│   └── test_risk_engine.py        # 存在
├── integration/
│   └── test_e2e.py                # ⚠️ 存在但可能因缺失依赖阻塞
├── fixtures/
│   └── __init__.py                # 存在
```

**当前阻塞测试的因素**:
1. `pydantic-settings` 模块缺失 → `pip install pydantic-settings`
2. `akshare` 模块缺失 → `pip install akshare` (可选，非关键)
3. `yfinance` 模块缺失 → `pip install yfinance`

---

## 六、目录树（当前 `src/` 结构）

```
lobster_quant/
├── app_v2.py            ← 新入口
├── src/
│   ├── __init__.py
│   ├── compat.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── data_engine.py
│   │   ├── indicator_engine.py
│   │   ├── risk_engine.py
│   │   ├── scoring_engine.py
│   │   ├── events.py
│   │   └── signal_engine.py        ← ❌ 需创建
│   ├── data/
│   │   ├── models.py
│   │   ├── cache.py
│   │   └── providers/
│   │       ├── base.py
│   │       ├── yfinance_provider.py
│   │       ├── akshare_provider.py
│   │       └── mock_provider.py
│   ├── analysis/
│   │   ├── indicators/
│   │   │   ├── base.py, trend.py, momentum.py, volume.py, volatility.py
│   │   ├── signals/
│   │   │   ├── lobster_signal.py
│   │   │   ├── composite_signal.py  ← ❌ 需创建
│   │   └── backtest/
│   │       ├── engine.py
│   │       └── metrics.py           ← ❌ 需创建
│   ├── config/
│   │   ├── settings.py
│   │   ├── defaults.yaml            ← ❌ 需创建
│   │   └── validation.py            ← ❌ 需创建
│   ├── ui/
│   │   ├── theme.py
│   │   ├── components/
│   │   │   ├── cards.py
│   │   │   ├── charts.py            ← ❌ 需创建
│   │   │   └── filters.py           ← ❌ 需创建
│   │   └── pages/
│   │       ├── dashboard.py, scanner.py, analyzer.py
│   │       ├── backtest.py, settings.py, quant_tool.py
│   │       └── quant_tool_indicators.py
│   └── utils/
│       ├── logging.py, exceptions.py
│       └── validators.py            ← ❌ 需创建
├── tests/ (...)
├── pyproject.toml
├── Makefile
├── REFACTOR_PLAN.md
├── ARCHITECTURE_REVIEW.md
└── REFACTOR_STATUS.md               ← 本文档
```