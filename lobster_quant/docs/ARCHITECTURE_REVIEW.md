# Lobster Quant 架构诊断与优化方案

> 生成时间: 2026-04-29
> 基于代码审查 + REFACTOR_PLAN.md 现状评估

---

## 一、现状总览

### 1.1 项目定位
**Lobster Quant** 是一个基于 Streamlit 的量化交易研究工具，核心功能包括：
- **OFF Filter 风控**: 多维度市场状态判断（ATR、MA200、Gap、大盘风险）
- **股票扫描器**: 多市场（美股/港股/A股）评分筛选
- **个股深度分析**: K线+技术指标+回测
- **龙虾信号**: 多因子评分+信号生成（强烈推荐/推荐/持有/观望）
- **Quant Tool**: 期权分析（Max Pain、支撑阻力、Put/Call Ratio）

### 1.2 技术栈
- **前端**: Streamlit (Python UI 框架)
- **数据**: yfinance (美股/港股) + akshare (A股)
- **可视化**: Plotly
- **计算**: Pandas + NumPy
- **测试**: pytest

---

## 二、核心问题诊断

### 🔴 严重问题 (必须立即修复)

| # | 问题 | 影响 | 文件 |
|---|------|------|------|
| 1 | **app.py 600+ 行，所有页面逻辑堆在一起** | 维护困难、协作冲突、无法单元测试 | app.py |
| 2 | **数据/业务/展示层完全混合** | 无法独立测试、无法复用逻辑、修改一处影响全局 | app.py, quant_tool_page.py |
| 3 | **裸 try/except，无统一异常处理** | 错误被吞掉、调试困难、用户体验差 | data_fetcher.py, lobster_off_filter.py |
| 4 | **重复代码: slope() 在 indicators.py 和 lobster_signal.py 各有一份** | 维护双份、易不一致 | indicators.py, lobster_signal.py |
| 5 | **quant_tool_page 直接依赖 yfinance，未抽象** | 无法切换数据源、无法 mock 测试 | quant_tool_page.py, quant_tool_data.py |
| 6 | **纯内存缓存，重启即丢失** | 重复拉取数据、API 限流风险、启动慢 | app.py (st.cache_data) |
| 7 | **无日志系统，只有 print** | 生产环境无法排查问题 | 全局 |

### 🟡 中等问题 (短期改进)

| # | 问题 | 影响 | 文件 |
|---|------|------|------|
| 8 | **评分算法得分偏低（最高~25分）** | 回测交易稀少、信号质量差 | scoring.py |
| 9 | **配置分散，魔法数字散落各处** | 难以调参、无法热更新 | config.py, 多处 |
| 10 | **无类型注解，IDE 提示弱** | 开发效率低、易传错参数 | 全局 |
| 11 | **测试覆盖率低 (~15%)** | 回归风险高、重构阻力大 | tests/ |
| 12 | **requirements.txt 无版本锁定** | 依赖冲突、环境不一致 | requirements.txt |
| 13 | **回测逻辑简单，无滑点/手续费** | 回测结果过于乐观 | backtest.py |
| 14 | **OFF Filter 原因统计曾出 Bug** | 数据正确性风险 | off_filter.py |

### 🟢 轻微问题 (长期优化)

| # | 问题 | 影响 |
|---|------|------|
| 15 | 无 CI/CD | 手动部署、易出错 |
| 16 | 无代码格式化 (black/ruff) | 代码风格不一致 |
| 17 | 无类型检查 (mypy) | 运行时类型错误 |
| 18 | 主题管理 hacky (monkeypatch st.set_theme) | Streamlit 升级可能失效 |
| 19 | 无性能监控 | 不知道哪里慢 |
| 20 | 无用户权限/多用户支持 | 无法部署给团队使用 |

---

## 三、架构对比：当前 vs 目标

### 3.1 当前架构 (Big Ball of Mud)

```
┌─────────────────────────────────────┐
│           Streamlit UI              │
│  (app.py 600+ lines, 5 tabs)        │
├─────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │Data Fetch│ │Indicators│ │Scoring│ │
│  │(yfinance)│ │(重复代码)│ │(魔法数)│ │
│  └─────────┘ └─────────┘ └───────┘ │
├─────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │Backtest │ │OFF Filter│ │Signal │ │
│  │(简单)   │ │(曾出bug) │ │(硬编码)│ │
│  └─────────┘ └─────────┘ └───────┘ │
├─────────────────────────────────────┤
│  config.py (单一文件, 混合配置)      │
└─────────────────────────────────────┘
```

**问题**: 所有模块平铺，互相直接引用，无抽象层，无依赖注入。

### 3.2 目标架构 (分层 + 插件化)

```
┌─────────────────────────────────────────────┐
│              Presentation Layer              │
│  ┌─────────┐ ┌─────────┐ ┌───────────────┐ │
│  │Dashboard│ │ Scanner │ │ Analyzer      │ │
│  │(OFF状态)│ │(股票筛选)│ │(个股深度分析)  │ │
│  └─────────┘ └─────────┘ └───────────────┘ │
│  ┌─────────┐ ┌─────────┐ ┌───────────────┐ │
│  │Backtest │ │ Settings│ │ Quant Tool    │ │
│  │(回测)   │ │(配置)   │ │(期权分析)     │ │
│  └─────────┘ └─────────┘ └───────────────┘ │
├─────────────────────────────────────────────┤
│              Application Layer               │
│  ┌─────────────┐  ┌─────────────────────┐  │
│  │ SignalEngine │  │ BacktestEngine      │  │
│  │ (信号生成)   │  │ (回测引擎+滑点手续费) │  │
│  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────────────┐  │
│  │ RiskEngine   │  │ ScoringEngine       │  │
│  │ (OFF Filter) │  │ (评分算法+权重配置)  │  │
│  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────┤
│              Domain Layer                    │
│  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Indicators   │  │ Data Models         │  │
│  │ (技术指标库)  │  │ (Pydantic: OHLCV)   │  │
│  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────┤
│              Infrastructure Layer            │
│  ┌─────────────┐  ┌─────────┐ ┌─────────┐ │
│  │DataProvider │  │  Cache  │ │  Logger │ │
│  │(抽象+多源)  │  │(磁盘+内存)│ │(结构化) │ │
│  │- yfinance   │  └─────────┘ └─────────┘ │
│  │- akshare    │  ┌─────────────────────┐ │
│  │- mock       │  │   Event Bus         │ │
│  └─────────────┘  │   (事件驱动)         │ │
│                   └─────────────────────┘ │
├─────────────────────────────────────────────┤
│              Config Layer                    │
│  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Pydantic    │  │  Environment        │  │
│  │ Settings    │  │  (.env)             │  │
│  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## 四、改进方向与实施计划

### Phase 1: 基础重构 (1-2 周) — **立即可开始**

#### 4.1 目录结构重组

```
lobster_quant/
├── src/
│   ├── core/                    # 核心引擎
│   │   ├── __init__.py
│   │   ├── data_engine.py       # 数据获取抽象层
│   │   ├── indicator_engine.py  # 指标计算引擎
│   │   ├── signal_engine.py     # 信号生成引擎
│   │   ├── scoring_engine.py    # 评分引擎
│   │   └── risk_engine.py       # 风控引擎 (OFF Filter)
│   ├── data/                    # 数据层
│   │   ├── __init__.py
│   │   ├── providers/           # 数据源适配器
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # 抽象基类
│   │   │   ├── yfinance_provider.py
│   │   │   ├── akshare_provider.py
│   │   │   └── mock_provider.py # 测试用
│   │   ├── cache.py             # 缓存管理 (磁盘+内存)
│   │   └── models.py            # 数据模型 (Pydantic)
│   ├── analysis/                # 分析层
│   │   ├── __init__.py
│   │   ├── indicators/          # 技术指标库
│   │   │   ├── __init__.py
│   │   │   ├── trend.py         # 趋势类指标
│   │   │   ├── momentum.py      # 动量类指标
│   │   │   ├── volume.py        # 成交量指标
│   │   │   └── volatility.py    # 波动率指标
│   │   ├── signals/             # 信号系统
│   │   │   ├── __init__.py
│   │   │   ├── lobster_signal.py
│   │   │   └── composite_signal.py
│   │   └── backtest/            # 回测框架
│   │       ├── __init__.py
│   │       ├── engine.py
│   │       └── metrics.py
│   ├── config/                  # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py          # Pydantic Settings
│   │   ├── defaults.yaml        # 默认配置
│   │   └── validation.py        # 配置校验
│   ├── ui/                      # 展示层
│   │   ├── __init__.py
│   │   ├── app.py               # Streamlit 入口 (精简)
│   │   ├── pages/               # 页面组件
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py     # 仪表盘 (OFF Filter)
│   │   │   ├── scanner.py       # 扫描器
│   │   │   ├── analyzer.py      # 个股分析
│   │   │   ├── backtest.py      # 回测页面
│   │   │   └── settings.py      # 设置页面
│   │   ├── components/          # 可复用组件
│   │   │   ├── __init__.py
│   │   │   ├── charts.py        # 图表组件
│   │   │   ├── cards.py         # 卡片组件
│   │   │   └── filters.py       # 过滤器组件
│   │   └── theme.py             # 主题管理
│   └── utils/                   # 工具函数
│       ├── __init__.py
│       ├── logging.py           # 日志配置
│       ├── exceptions.py        # 自定义异常
│       └── validators.py        # 校验工具
├── tests/                       # 测试目录
│   ├── __init__.py
│   ├── conftest.py              # pytest 配置
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── fixtures/                # 测试数据
├── notebooks/                   # 研究笔记本
├── docs/                        # 文档
├── scripts/                     # 脚本工具
├── .env.example                 # 环境变量示例
├── pyproject.toml               # 现代 Python 项目配置
├── Makefile                     # 常用命令
└── README.md
```

#### 4.2 关键改进点

| 改进项 | 当前状态 | 目标状态 | 优先级 |
|--------|---------|---------|--------|
| **数据模型层** | 无，直接用 dict/DataFrame | Pydantic 模型 (OHLCV, SignalResult, BacktestResult) | 🔴 高 |
| **数据源抽象** | 直接调用 yfinance/akshare | Provider 抽象基类 + 工厂模式 | 🔴 高 |
| **统一配置** | 单一 config.py，魔法数字 | Pydantic Settings + .env + YAML | 🔴 高 |
| **结构化日志** | 只有 print | logging + 文件/控制台双输出 | 🟡 中 |
| **异常处理** | 裸 try/except | 自定义异常类 + 统一处理中间件 | 🔴 高 |
| **缓存持久化** | st.cache_data (内存) | 磁盘缓存 (SQLite/Parquet) + TTL | 🟡 中 |
| **类型注解** | 无 | 全模块类型注解 + mypy 检查 | 🟡 中 |
| **代码格式化** | 无 | black + ruff + pre-commit | 🟡 中 |

---

### Phase 2: 核心引擎升级 (2-3 周)

#### 4.3 指标计算引擎 (消除重复)

```python
# src/analysis/indicators/base.py
from abc import ABC, abstractmethod
import pandas as pd

class Indicator(ABC):
    """技术指标基类"""
    name: str = ""
    params: dict = {}
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        pass
    
    def validate(self, data: pd.DataFrame) -> bool:
        required = ['open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required)

# 注册表模式
class IndicatorRegistry:
    _indicators: dict[str, type[Indicator]] = {}
    
    @classmethod
    def register(cls, indicator_class: type[Indicator]):
        cls._indicators[indicator_class.name] = indicator_class
        return indicator_class
    
    @classmethod
    def get(cls, name: str) -> type[Indicator]:
        if name not in cls._indicators:
            raise KeyError(f"Indicator '{name}' not found")
        return cls._indicators[name]
```

#### 4.4 事件驱动架构 (解耦模块)

```python
# src/core/events.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from enum import Enum, auto

class EventType(Enum):
    DATA_UPDATED = auto()
    SIGNAL_GENERATED = auto()
    OFF_FILTER_TRIGGERED = auto()
    BACKTEST_COMPLETED = auto()
    ERROR_OCCURRED = auto()

@dataclass
class Event:
    type: EventType
    payload: Any
    timestamp: datetime
    source: str

class EventBus:
    """轻量级事件总线"""
    def __init__(self):
        self._subscribers: dict[EventType, list[Callable]] = {}
    
    def subscribe(self, event_type: EventType, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def publish(self, event: Event):
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {e}")
```

#### 4.5 异步数据获取 (提升性能)

```python
# src/core/data_engine.py
import asyncio
from typing import Optional
import pandas as pd

class AsyncDataEngine:
    """异步数据引擎"""
    
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.providers: dict[str, DataProvider] = {}
        self.cache = DataCache()
    
    async def fetch_batch(self, requests: list[DataRequest]) -> dict[str, Optional[pd.DataFrame]]:
        """批量获取数据，并发控制"""
        tasks = [self.fetch_single(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            req.symbol: res if not isinstance(res, Exception) else None
            for req, res in zip(requests, results)
        }
```

---

### Phase 3: 工程化建设 (1-2 周)

#### 4.6 现代化项目配置

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "lobster-quant"
version = "2.0.0"
description = "Quantitative Trading Research Tool"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "streamlit>=1.28",
    "pandas>=2.0",
    "numpy>=1.24",
    "yfinance>=0.2.18",
    "plotly>=5.15",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "akshare>=1.13",
    "aiohttp>=3.8",
    "structlog>=23.0",
    "tenacity>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1.0",
    "mypy>=1.5",
    "pre-commit>=3.0",
]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

#### 4.7 健康检查与监控

```python
# src/utils/health.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import psutil

@dataclass
class HealthStatus:
    status: str  # "healthy", "degraded", "unhealthy"
    checks: dict[str, bool]
    latency_ms: dict[str, float]
    timestamp: datetime
    memory_usage_mb: float
    cpu_percent: float

class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: dict[str, Callable] = {}
    
    def register(self, name: str, check_func: Callable):
        self.checks[name] = check_func
    
    async def check_all(self) -> HealthStatus:
        results = {}
        latencies = {}
        
        for name, check in self.checks.items():
            start = time.time()
            try:
                results[name] = await asyncio.to_thread(check)
            except Exception:
                results[name] = False
            latencies[name] = (time.time() - start) * 1000
        
        status = "healthy" if all(results.values()) else \
                 "degraded" if any(results.values()) else "unhealthy"
        
        return HealthStatus(
            status=status,
            checks=results,
            latency_ms=latencies,
            timestamp=datetime.now(),
            memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024,
            cpu_percent=psutil.cpu_percent()
        )
```

---

### Phase 4: 高级功能 (3-4 周)

#### 4.8 插件系统

```python
# src/core/plugins.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar('T')

class Plugin(ABC, Generic[T]):
    """插件基类"""
    name: str = ""
    version: str = "1.0.0"
    enabled: bool = True
    
    @abstractmethod
    def initialize(self, config: dict) -> None:
        pass
    
    @abstractmethod
    def execute(self, data: T) -> T:
        pass
    
    def shutdown(self) -> None:
        pass

class PluginManager:
    """插件管理器"""
    def __init__(self):
        self._plugins: list[Plugin] = []
        self._hooks: dict[str, list[Callable]] = {}
    
    def register(self, plugin: Plugin):
        self._plugins.append(plugin)
    
    def execute_hook(self, hook_name: str, data: T) -> T:
        for plugin in self._plugins:
            if plugin.enabled and hook_name in self._hooks:
                for handler in self._hooks[hook_name]:
                    data = handler(data)
        return data
```

#### 4.9 机器学习集成

```python
# src/ml/features.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

class FeatureEngineer:
    """特征工程"""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建机器学习特征"""
        features = pd.DataFrame(index=df.index)
        
        # 价格特征
        features['returns_1d'] = df['close'].pct_change()
        features['returns_5d'] = df['close'].pct_change(5)
        features['returns_20d'] = df['close'].pct_change(20)
        
        # 波动率特征
        features['volatility_20d'] = df['close'].pct_change().rolling(20).std()
        features['atr_ratio'] = self._calc_atr(df) / df['close']
        
        # 成交量特征
        features['volume_ma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # 技术指标特征
        features['rsi'] = self._calc_rsi(df['close'])
        features['macd_hist'] = self._calc_macd_hist(df['close'])
        features['bb_position'] = self._calc_bb_position(df)
        
        return features.dropna()
```

---

## 五、实施优先级矩阵

### 5.1 立即执行 (本周)

| 任务 | 工作量 | 收益 | 说明 |
|------|--------|------|------|
| 1. 创建新目录结构 | 2h | ⭐⭐⭐ | 为后续重构打基础 |
| 2. 提取配置到独立模块 | 4h | ⭐⭐⭐ | 消除魔法数字 |
| 3. 添加类型注解到核心函数 | 6h | ⭐⭐ | 提升开发体验 |
| 4. 统一异常处理 | 4h | ⭐⭐⭐ | 提升稳定性 |

### 5.2 短期 (2-4 周)

| 任务 | 工作量 | 收益 | 说明 |
|------|--------|------|------|
| 5. 实现数据提供者抽象层 | 8h | ⭐⭐⭐⭐ | 支持多源+mock测试 |
| 6. 重构指标计算 (消除重复) | 6h | ⭐⭐⭐ | 维护一份 slope/RSI/MACD |
| 7. 添加结构化日志 | 4h | ⭐⭐⭐ | 生产环境可排查 |
| 8. 编写核心单元测试 | 12h | ⭐⭐⭐⭐ | 覆盖率>80% |
| 9. 磁盘缓存替代内存缓存 | 6h | ⭐⭐⭐ | 重启不丢失 |

### 5.3 中期 (1-2 月)

| 任务 | 工作量 | 收益 | 说明 |
|------|--------|------|------|
| 10. 实现异步数据引擎 | 10h | ⭐⭐⭐⭐ | 5-10x 加载速度 |
| 11. 添加事件总线 | 8h | ⭐⭐⭐ | 模块解耦 |
| 12. 重构 Streamlit 页面组件化 | 12h | ⭐⭐⭐⭐ | 每页<200行 |
| 13. 添加健康检查 | 4h | ⭐⭐ | 运维友好 |
| 14. 回测引擎增强 (滑点/手续费) | 8h | ⭐⭐⭐ | 更真实的结果 |

### 5.4 长期 (3-6 月)

| 任务 | 工作量 | 收益 | 说明 |
|------|--------|------|------|
| 15. 插件系统 | 16h | ⭐⭐⭐ | 第三方扩展 |
| 16. 实时数据流 (WebSocket) | 12h | ⭐⭐⭐⭐ | 实时信号 |
| 17. ML 特征工程 | 16h | ⭐⭐⭐⭐ | 智能评分 |
| 18. 性能优化 (Cython/Numba) | 12h | ⭐⭐⭐ | 计算加速 |
| 19. 多用户/权限系统 | 16h | ⭐⭐⭐ | 团队部署 |

---

## 六、预期收益

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 代码复用率 | ~30% | >70% | +40% |
| 测试覆盖率 | ~15% | >80% | +65% |
| 数据加载速度 | 串行 | 并行 | 5-10x |
| 配置维护成本 | 高 | 低 | -70% |
| 新功能开发周期 | 2-3天 | <1天 | -60% |
| 故障定位时间 | 30min+ | <5min | -80% |
| 启动时间 (15只股票) | ~30s | ~5s | -83% |

---

## 七、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 重构引入 Bug | 高 | 保持旧代码并行运行，逐步切换；每步都有测试 |
| 开发时间超预期 | 中 | 分阶段交付，每阶段可独立使用；MVP 优先 |
| 性能退化 | 中 | 添加性能基准测试，监控回归；异步优化 |
| 团队学习成本 | 低 | 提供详细文档和示例；Pydantic/Streamlit 生态成熟 |
| 数据源变更 | 低 | Provider 抽象层隔离；mock 测试覆盖 |

---

## 八、下一步行动

1. **确认改进方向**: 你是否同意以上诊断和计划？
2. **选择切入点**: 建议从 **Phase 1 目录结构重组** 开始，风险最低
3. **并行工作**: 我可以同时开始：
   - 创建新目录结构
   - 编写数据模型 (Pydantic)
   - 提取配置到独立模块
   - 添加类型注解

是否需要我开始实施？或者你想先调整优先级？
