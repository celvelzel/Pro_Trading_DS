# Lobster Quant 架构优化计划

## 一、现状诊断

### 1.1 架构问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| 单文件臃肿 | 🔴 高 | app.py 600+ 行，所有页面逻辑堆在一起 |
| 缺乏分层 | 🔴 高 | 数据/业务/展示层混合，无清晰边界 |
| 配置分散 | 🟡 中 | config.py 包含所有配置，但运行时硬编码仍多 |
| 错误处理弱 | 🔴 高 | 大量裸 try/except，无统一异常处理 |
| 无日志系统 | 🟡 中 | 只有 print，无结构化日志 |
| 测试覆盖低 | 🟡 中 | 测试文件存在但不成体系 |
| 无数据持久化 | 🟡 中 | 纯内存缓存，重启即丢失 |
| 模块耦合高 | 🔴 高 | quant_tool_page 直接依赖 yfinance，未抽象 |

### 1.2 代码质量问题

- **重复代码**: `slope()` 在 indicators.py 和 lobster_signal.py 中各有一份
- **魔法数字**: 评分阈值、窗口大小等散落各处
- **类型缺失**: 无类型注解，IDE 提示弱
- **文档缺失**: 核心算法无 docstring

### 1.3 工程化缺失

- 无 CI/CD
- 无代码格式化 (black/ruff)
- 无类型检查 (mypy)
- 无依赖锁定 (requirements.txt 无版本锁定)

---

## 二、改进方向 (Roadmap)

### Phase 1: 基础重构 (1-2 周)

#### 2.1 目录结构重组

```
lobster_quant/
├── 📁 src/                          # 源码目录
│   ├── 📁 core/                     # 核心引擎
│   │   ├── __init__.py
│   │   ├── data_engine.py           # 数据获取抽象层
│   │   ├── indicator_engine.py      # 指标计算引擎
│   │   ├── signal_engine.py         # 信号生成引擎
│   │   ├── scoring_engine.py        # 评分引擎
│   │   └── risk_engine.py           # 风控引擎 (OFF Filter)
│   ├── 📁 data/                     # 数据层
│   │   ├── __init__.py
│   │   ├── providers/               # 数据源适配器
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # 抽象基类
│   │   │   ├── yfinance_provider.py
│   │   │   ├── akshare_provider.py
│   │   │   └── mock_provider.py     # 测试用
│   │   ├── cache.py                 # 缓存管理 (磁盘+内存)
│   │   └── models.py                # 数据模型 (Pydantic)
│   ├── 📁 analysis/                 # 分析层
│   │   ├── __init__.py
│   │   ├── indicators/              # 技术指标库
│   │   │   ├── __init__.py
│   │   │   ├── trend.py             # 趋势类指标
│   │   │   ├── momentum.py          # 动量类指标
│   │   │   ├── volume.py            # 成交量指标
│   │   │   └── volatility.py        # 波动率指标
│   │   ├── signals/                 # 信号系统
│   │   │   ├── __init__.py
│   │   │   ├── lobster_signal.py    # 龙虾信号
│   │   │   └── composite_signal.py  # 复合信号
│   │   └── backtest/                # 回测框架
│   │       ├── __init__.py
│   │       ├── engine.py
│   │       └── metrics.py
│   ├── 📁 config/                   # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py              # Pydantic Settings
│   │   ├── defaults.yaml            # 默认配置
│   │   └── validation.py            # 配置校验
│   ├── 📁 ui/                       # 展示层
│   │   ├── __init__.py
│   │   ├── app.py                   # Streamlit 入口
│   │   ├── pages/                   # 页面组件
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py         # 仪表盘
│   │   │   ├── scanner.py           # 扫描器
│   │   │   ├── analyzer.py          # 个股分析
│   │   │   ├── backtest.py          # 回测页面
│   │   │   └── settings.py          # 设置页面
│   │   ├── components/              # 可复用组件
│   │   │   ├── __init__.py
│   │   │   ├── charts.py            # 图表组件
│   │   │   ├── cards.py             # 卡片组件
│   │   │   └── filters.py           # 过滤器组件
│   │   └── theme.py                 # 主题管理
│   └── 📁 utils/                    # 工具函数
│       ├── __init__.py
│       ├── logging.py               # 日志配置
│       ├── exceptions.py            # 自定义异常
│       └── validators.py            # 校验工具
├── 📁 tests/                        # 测试目录
│   ├── __init__.py
│   ├── conftest.py                  # pytest 配置
│   ├── unit/                        # 单元测试
│   ├── integration/                 # 集成测试
│   └── fixtures/                    # 测试数据
├── 📁 notebooks/                    # 研究笔记本
├── 📁 docs/                         # 文档
├── 📁 scripts/                      # 脚本工具
├── .env.example                     # 环境变量示例
├── pyproject.toml                   # 现代 Python 项目配置
├── Makefile                         # 常用命令
└── README.md
```

#### 2.2 引入数据模型层 (Pydantic)

```python
# src/data/models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
import pandas as pd

class OHLCV(BaseModel):
    """标准化 K 线数据"""
    symbol: str
    timeframe: Literal["1d", "1w", "1m"]
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime

class StockData(BaseModel):
    """股票完整数据容器"""
    symbol: str
    daily: pd.DataFrame
    weekly: Optional[pd.DataFrame] = None
    monthly: Optional[pd.DataFrame] = None
    last_update: datetime
    source: str
    
    class Config:
        arbitrary_types_allowed = True

class SignalResult(BaseModel):
    """信号结果"""
    symbol: str
    signal_type: Literal["强烈推荐", "推荐", "持有", "观望"]
    score: float = Field(..., ge=0, le=100)
    probability_up: float = Field(..., ge=0, le=100)
    reasons: list[str]
    timestamp: datetime

class BacktestResult(BaseModel):
    """回测结果"""
    symbol: str
    trades: int
    win_rate: float
    avg_return: float
    profit_factor: float
    max_drawdown: float
    equity_curve: list[float]
```

#### 2.3 数据源抽象层

```python
# src/data/providers/base.py
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd

class DataProvider(ABC):
    """数据源抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def fetch_daily(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        pass
    
    @abstractmethod
    def fetch_options(self, symbol: str) -> Optional[dict]:
        """获取期权数据"""
        pass
    
    def health_check(self) -> bool:
        """健康检查"""
        return True

# 使用工厂模式
class DataProviderFactory:
    _providers = {}
    
    @classmethod
    def register(cls, name: str, provider_class: type):
        cls._providers[name] = provider_class
    
    @classmethod
    def create(cls, name: str, **kwargs) -> DataProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")
        return cls._providers[name](**kwargs)
```

#### 2.4 统一配置管理

```python
# src/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal

class Settings(BaseSettings):
    """统一配置类"""
    
    # 应用配置
    app_name: str = "Lobster Quant"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # 数据配置
    data_cache_dir: str = Field(default="./data/cache", env="CACHE_DIR")
    data_cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    data_years: int = 3
    
    # 市场配置
    enable_a_stock: bool = False
    enable_hk_stock: bool = True
    enable_us_stock: bool = True
    
    # 风控参数
    off_filter_vix_threshold: float = 35.0
    off_filter_atr_pct: float = 0.05
    off_filter_gap_std: float = 2.0
    
    # 评分参数
    score_weights: dict = {
        "trend": 0.40,
        "momentum": 0.20,
        "volume": 0.15,
        "pattern": 0.25,
    }
    
    # 回测参数
    backtest_holding_days: int = 20
    backtest_min_score: int = 20
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局配置实例
settings = Settings()
```

#### 2.5 结构化日志系统

```python
# src/utils/logging.py
import logging
import sys
from pathlib import Path
from datetime import datetime

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)

def setup_logging(
    level: str = "INFO",
    log_dir: str = "./logs",
    console: bool = True,
    file: bool = True
) -> logging.Logger:
    """配置日志系统"""
    
    logger = logging.getLogger("lobster_quant")
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers = []
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)
    
    if file:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = Path(log_dir) / f"{datetime.now():%Y%m%d}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
```

---

### Phase 2: 核心引擎升级 (2-3 周)

#### 2.6 指标计算引擎

```python
# src/analysis/indicators/base.py
from abc import ABC, abstractmethod
import pandas as pd
from typing import Any

class Indicator(ABC):
    """技术指标基类"""
    
    name: str = ""
    params: dict = {}
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        pass
    
    def validate(self, data: pd.DataFrame) -> bool:
        """验证输入数据"""
        required = ['open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required)

# 具体指标实现
class RSIIndicator(Indicator):
    name = "RSI"
    params = {"period": 14}
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(self.params['period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.params['period']).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

class MACDIndicator(Indicator):
    name = "MACD"
    params = {"fast": 12, "slow": 26, "signal": 9}
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        exp1 = data['close'].ewm(span=self.params['fast'], adjust=False).mean()
        exp2 = data['close'].ewm(span=self.params['slow'], adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=self.params['signal'], adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        })

# 指标注册表
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
    
    @classmethod
    def list(cls) -> list[str]:
        return list(cls._indicators.keys())
```

#### 2.7 事件驱动架构

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
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

# 全局事件总线
event_bus = EventBus()
```

#### 2.8 异步数据获取

```python
# src/core/data_engine.py
import asyncio
import aiohttp
from typing import Optional
import pandas as pd
from dataclasses import dataclass

@dataclass
class DataRequest:
    symbol: str
    provider: str
    timeframe: str
    years: int = 3

class AsyncDataEngine:
    """异步数据引擎"""
    
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.providers: dict[str, DataProvider] = {}
        self.cache = DataCache()
    
    def register_provider(self, name: str, provider: DataProvider):
        self.providers[name] = provider
    
    async def fetch_single(self, request: DataRequest) -> Optional[pd.DataFrame]:
        """获取单只股票数据"""
        async with self.semaphore:
            # 检查缓存
            cache_key = f"{request.symbol}_{request.timeframe}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached
            
            # 获取数据
            provider = self.providers.get(request.provider)
            if not provider:
                raise ValueError(f"Provider not found: {request.provider}")
            
            try:
                data = await asyncio.to_thread(
                    provider.fetch_daily,
                    request.symbol,
                    request.years
                )
                
                if data is not None:
                    self.cache.set(cache_key, data, ttl=3600)
                
                return data
            except Exception as e:
                logger.error(f"Failed to fetch {request.symbol}: {e}")
                return None
    
    async def fetch_batch(self, requests: list[DataRequest]) -> dict[str, Optional[pd.DataFrame]]:
        """批量获取数据"""
        tasks = [self.fetch_single(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            req.symbol: res if not isinstance(res, Exception) else None
            for req, res in zip(requests, results)
        }
```

---

### Phase 3: 工程化建设 (1-2 周)

#### 2.9 现代化项目配置

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

#### 2.10 健康检查与监控

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

# 使用
health = HealthChecker()
health.register("yfinance", lambda: yfinance_provider.health_check())
health.register("akshare", lambda: akshare_provider.health_check())
health.register("disk_space", lambda: psutil.disk_usage("/").percent < 90)
```

---

### Phase 4: 高级功能 (3-4 周)

#### 2.11 插件系统

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

#### 2.12 实时数据流 (WebSocket)

```python
# src/data/streaming.py
import websockets
import json
from typing import Callable

class StreamingDataClient:
    """实时数据流客户端"""
    
    def __init__(self, uri: str):
        self.uri = uri
        self.subscribers: dict[str, list[Callable]] = {}
        self.ws = None
    
    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        asyncio.create_task(self._listen())
    
    async def _listen(self):
        async for message in self.ws:
            data = json.loads(message)
            symbol = data.get('symbol')
            if symbol in self.subscribers:
                for callback in self.subscribers[symbol]:
                    callback(data)
    
    def subscribe(self, symbol: str, callback: Callable):
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
```

#### 2.13 机器学习集成

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
        features['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
        
        # 技术指标特征
        features['rsi'] = self._calc_rsi(df['close'])
        features['macd_hist'] = self._calc_macd_hist(df['close'])
        features['bb_position'] = self._calc_bb_position(df)
        
        return features.dropna()
    
    def _calc_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()
```

---

## 三、实施优先级

### 立即执行 (本周)
1. ✅ 创建 REFACTOR_PLAN.md (已完成)
2. 初始化新目录结构
3. 提取配置到独立模块
4. 添加类型注解到核心函数

### 短期 (2-4 周)
5. 实现数据提供者抽象层
6. 重构指标计算 (消除重复)
7. 添加结构化日志
8. 编写核心单元测试

### 中期 (1-2 月)
9. 实现异步数据引擎
10. 添加事件总线
11. 重构 Streamlit 页面组件化
12. 添加健康检查

### 长期 (3-6 月)
13. 插件系统
14. 实时数据流
15. ML 特征工程
16. 性能优化 (Cython/Numba)

---

## 四、预期收益

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 代码复用率 | ~30% | >70% | +40% |
| 测试覆盖率 | ~15% | >80% | +65% |
| 数据加载速度 | 串行 | 并行 | 5-10x |
| 配置维护成本 | 高 | 低 | -70% |
| 新功能开发周期 | 2-3天 | <1天 | -60% |
| 故障定位时间 | 30min+ | <5min | -80% |

---

## 五、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 重构引入 Bug | 高 | 保持旧代码并行运行，逐步切换 |
| 开发时间超预期 | 中 | 分阶段交付，每阶段可独立使用 |
| 性能退化 | 中 | 添加性能基准测试，监控回归 |
| 团队学习成本 | 低 | 提供详细文档和示例 |

---

## 六、实施检查清单

### Phase 1: 基础重构 (1-2 周)

#### 6.1 目录结构重组
- [ ] 创建 `src/` 根目录
- [ ] 创建 `src/core/` 并添加 `__init__.py`
- [ ] 创建 `src/data/` 并添加 `__init__.py`
- [ ] 创建 `src/data/providers/` 并添加 `__init__.py`
- [ ] 创建 `src/analysis/` 并添加 `__init__.py`
- [ ] 创建 `src/analysis/indicators/` 并添加 `__init__.py`
- [ ] 创建 `src/analysis/signals/` 并添加 `__init__.py`
- [ ] 创建 `src/analysis/backtest/` 并添加 `__init__.py`
- [ ] 创建 `src/config/` 并添加 `__init__.py`
- [ ] 创建 `src/ui/` 并添加 `__init__.py`
- [ ] 创建 `src/ui/pages/` 并添加 `__init__.py`
- [ ] 创建 `src/ui/components/` 并添加 `__init__.py`
- [ ] 创建 `src/utils/` 并添加 `__init__.py`
- [ ] 创建 `tests/` 并添加 `__init__.py`
- [ ] 创建 `tests/unit/` 并添加 `__init__.py`
- [ ] 创建 `tests/integration/` 并添加 `__init__.py`
- [ ] 创建 `tests/fixtures/`

#### 6.2 数据模型层 (Pydantic)
- [ ] 定义 `OHLCV` 数据模型
- [ ] 定义 `StockData` 数据模型
- [ ] 定义 `SignalResult` 数据模型
- [ ] 定义 `BacktestResult` 数据模型
- [ ] 定义 `IndicatorResult` 数据模型
- [ ] 添加模型验证逻辑
- [ ] 编写模型单元测试

#### 6.3 数据源抽象层
- [ ] 定义 `DataProvider` 抽象基类
- [ ] 实现 `YFinanceProvider`
- [ ] 实现 `AkShareProvider`
- [ ] 实现 `MockProvider` (测试用)
- [ ] 实现 `DataProviderFactory` 工厂类
- [ ] 添加数据源注册机制
- [ ] 编写数据源单元测试

#### 6.4 配置管理
- [ ] 定义 `Settings` 基类 (Pydantic Settings)
- [ ] 创建 `.env.example` 文件
- [ ] 创建 `defaults.yaml` 配置文件
- [ ] 实现配置加载逻辑
- [ ] 实现配置校验逻辑
- [ ] 迁移现有硬编码配置到 Settings
- [ ] 编写配置管理单元测试

#### 6.5 日志系统
- [ ] 实现 `ColoredFormatter` 格式化器
- [ ] 实现 `setup_logging` 初始化函数
- [ ] 配置控制台日志输出
- [ ] 配置文件日志输出
- [ ] 替换现有 `print` 语句为日志调用
- [ ] 添加日志级别配置
- [ ] 编写日志系统单元测试

---

### Phase 2: 核心引擎升级 (2-3 周)

#### 6.6 指标计算引擎
- [ ] 定义 `Indicator` 抽象基类
- [ ] 实现 `RSIIndicator` 类
- [ ] 实现 `MACDIndicator` 类
- [ ] 实现 `BollingerIndicator` 类
- [ ] 实现 `ATRIndicator` 类
- [ ] 实现 `VolumeIndicator` 类
- [ ] 实现 `IndicatorRegistry` 注册表
- [ ] 迁移 `indicators.py` 中现有指标
- [ ] 消除 `slope()` 重复定义
- [ ] 编写指标引擎单元测试

#### 6.7 信号系统重构
- [ ] 定义 `SignalEngine` 基类
- [ ] 重构 `lobster_signal.py` 为信号引擎
- [ ] 实现 `CompositeSignal` 复合信号
- [ ] 添加信号权重配置
- [ ] 实现信号缓存机制
- [ ] 编写信号系统单元测试

#### 6.8 评分引擎
- [ ] 定义 `ScoringEngine` 类
- [ ] 迁移现有评分逻辑
- [ ] 将评分阈值移至配置
- [ ] 实现评分结果缓存
- [ ] 添加评分结果持久化
- [ ] 编写评分引擎单元测试

#### 6.9 风控引擎 (OFF Filter)
- [ ] 定义 `RiskEngine` 类
- [ ] 迁移 OFF Filter 逻辑
- [ ] 将风控参数移至配置
- [ ] 实现风控事件发布
- [ ] 编写风控引擎单元测试

#### 6.10 事件驱动架构
- [ ] 定义 `EventType` 枚举
- [ ] 定义 `Event` 数据类
- [ ] 实现 `EventBus` 事件总线
- [ ] 添加事件订阅/发布机制
- [ ] 实现事件日志记录
- [ ] 集成到各引擎模块
- [ ] 编写事件系统单元测试

#### 6.11 异步数据引擎
- [ ] 定义 `DataRequest` 数据类
- [ ] 实现 `AsyncDataEngine` 类
- [ ] 实现并发控制 (Semaphore)
- [ ] 集成数据缓存机制
- [ ] 实现批量数据获取
- [ ] 添加数据获取重试机制
- [ ] 编写异步数据引擎单元测试

---

### Phase 3: 工程化建设 (1-2 周)

#### 6.12 项目配置现代化
- [ ] 创建 `pyproject.toml`
- [ ] 配置构建系统 (hatchling)
- [ ] 定义项目依赖
- [ ] 定义开发依赖
- [ ] 配置 Black 格式化
- [ ] 配置 Ruff 代码检查
- [ ] 配置 MyPy 类型检查
- [ ] 配置 Pytest 测试框架
- [ ] 创建 `Makefile` 常用命令
- [ ] 删除旧的 `requirements.txt`

#### 6.13 代码质量工具
- [ ] 配置 pre-commit hooks
- [ ] 添加 Black 自动格式化
- [ ] 添加 Ruff 代码检查
- [ ] 添加 MyPy 类型检查
- [ ] 配置 CI 前的本地检查流程
- [ ] 添加代码覆盖率配置

#### 6.14 测试体系建设
- [ ] 创建 `tests/conftest.py` pytest 配置
- [ ] 添加测试 fixtures (模拟数据)
- [ ] 编写核心模块单元测试
- [ ] 编写数据提供者测试
- [ ] 编写指标计算测试
- [ ] 编写信号系统测试
- [ ] 编写配置管理测试
- [ ] 配置测试覆盖率报告
- [ ] 目标: 覆盖率 > 80%

#### 6.15 健康检查与监控
- [ ] 定义 `HealthStatus` 数据类
- [ ] 实现 `HealthChecker` 健康检查器
- [ ] 添加数据源健康检查
- [ ] 添加磁盘空间检查
- [ ] 添加内存使用监控
- [ ] 实现健康检查端点
- [ ] 编写健康检查单元测试

#### 6.16 文档建设
- [ ] 更新 `README.md` 项目说明
- [ ] 添加架构设计文档
- [ ] 添加 API 接口文档
- [ ] 添加配置说明文档
- [ ] 添加开发者指南
- [ ] 添加部署指南

---

### Phase 4: 高级功能 (3-4 周)

#### 6.17 插件系统
- [ ] 定义 `Plugin` 抽象基类
- [ ] 实现 `PluginManager` 管理器
- [ ] 添加插件加载机制
- [ ] 添加插件生命周期管理
- [ ] 实现插件配置集成
- [ ] 编写插件系统单元测试

#### 6.18 实时数据流
- [ ] 实现 `StreamingDataClient` 客户端
- [ ] 添加 WebSocket 连接管理
- [ ] 实现订阅/取消订阅机制
- [ ] 添加数据流错误处理
- [ ] 实现重连机制
- [ ] 编写数据流单元测试

#### 6.19 机器学习集成
- [ ] 实现 `FeatureEngineer` 特征工程类
- [ ] 添加价格特征计算
- [ ] 添加波动率特征计算
- [ ] 添加成交量特征计算
- [ ] 添加技术指标特征
- [ ] 实现特征标准化
- [ ] 编写特征工程单元测试

#### 6.20 UI 组件化重构
- [ ] 重构 `app.py` 为页面路由
- [ ] 创建 Dashboard 页面组件
- [ ] 创建 Scanner 页面组件
- [ ] 创建 Analyzer 页面组件
- [ ] 创建 Backtest 页面组件
- [ ] 创建 Settings 页面组件
- [ ] 实现图表可复用组件
- [ ] 实现卡片可复用组件
- [ ] 实现过滤器可复用组件
- [ ] 添加主题管理
- [ ] 编写 UI 组件测试

---

### Phase 5: 集成与部署

#### 6.21 集成测试
- [ ] 编写端到端集成测试
- [ ] 编写 API 集成测试
- [ ] 编写 UI 集成测试
- [ ] 性能基准测试
- [ ] 负载测试
- [ ] 压力测试

#### 6.22 CI/CD 配置
- [ ] 配置 GitHub Actions CI
- [ ] 配置代码质量检查流水线
- [ ] 配置测试执行流水线
- [ ] 配置自动部署流水线
- [ ] 配置环境变量管理
- [ ] 配置监控告警

#### 6.23 迁移与上线
- [ ] 制定数据迁移方案
- [ ] 制定回滚计划
- [ ] 灰度发布策略
- [ ] 生产环境配置
- [ ] 监控与告警配置
- [ ] 文档归档

---

### 检查清单使用说明

1. **任务分配**: 将检查项分配给团队成员
2. **进度跟踪**: 完成后勾选 `[x]`，定期更新进度
3. **依赖管理**: 注意任务间的依赖关系
4. **质量把控**: 每项完成后需通过代码审查
5. **文档更新**: 完成后同步更新相关文档

### 进度统计

| Phase | 总任务数 | 已完成 | 完成率 |
|-------|---------|--------|--------|
| Phase 1: 基础重构 | 45 | 0 | 0% |
| Phase 2: 核心引擎升级 | 52 | 0 | 0% |
| Phase 3: 工程化建设 | 48 | 0 | 0% |
| Phase 4: 高级功能 | 38 | 0 | 0% |
| Phase 5: 集成与部署 | 18 | 0 | 0% |
| **总计** | **201** | **0** | **0%** |
