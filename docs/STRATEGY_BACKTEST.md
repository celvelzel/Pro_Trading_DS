# Strategy Backtest & Management System

## Overview

This document describes the new strategy backtest and management system added to Lobster Quant. The system enables:

1. **Flexible Backtesting** - Test strategies over any time period with single or multiple stocks
2. **Daily Simulation** - Run daily stock selection and trade simulation
3. **Strategy Management** - Create, compare, and switch between multiple strategies

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Strategy Mgmt │  │  Backtest    │  │  Daily Simulation│  │
│  │    Page       │  │  Results     │  │    Dashboard     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ /strategy/*  │  │ /backtest/*  │  │  /simulation/*   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Strategy Engine (New)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Strategy   │  │   Preset     │  │    Strategy      │  │
│  │   Manager    │  │  Strategies  │  │    Comparator    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backtest Engine (Extended)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Single     │  │   Portfolio  │  │     Metrics      │  │
│  │   Stock      │  │   Backtest   │  │    Calculator    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Storage Layer (New)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │    Trade     │  │   Snapshot   │  │     Strategy     │  │
│  │    Store     │  │    Store     │  │      Store       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Data Models

### Strategy

```python
class Strategy(BaseModel):
    id: str
    name: str
    description: str
    params: StrategyParams
    logic: Literal["default", "momentum", "mean_reversion"] = "default"
    isPreset: bool = False
    createdAt: datetime
    updatedAt: Optional[datetime] = None
```

### StrategyParams

```python
class StrategyParams(BaseModel):
    holdingDays: int = 20          # Days to hold each position
    minScore: int = 60             # Minimum score to enter trade
    slippagePct: float = 0.001     # Slippage percentage
    commissionPct: float = 0.001   # Commission percentage
    positionSizing: str = "fixed"  # "fixed" or "dynamic"
    positionSize: float = 0.1      # Position size (10%)
    initialCapital: float = 100000 # Starting capital
    maxPositions: int = 5          # Max concurrent positions
```

### BacktestMetrics

```python
class BacktestMetrics(BaseModel):
    totalReturn: float
    annualizedReturn: float
    volatility: float
    sharpeRatio: float
    maxDrawdown: float
    winRate: float
    profitLossRatio: float
    totalTrades: int
    winningTrades: int
    losingTrades: int
    avgHoldingDays: float
    avgWin: float
    avgLoss: float
```

## API Endpoints

### Strategy Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/strategy/strategies` | List all strategies |
| GET | `/api/strategy/strategies/{id}` | Get strategy by ID |
| POST | `/api/strategy/strategies` | Create new strategy |
| PUT | `/api/strategy/strategies/{id}` | Update strategy |
| DELETE | `/api/strategy/strategies/{id}` | Delete strategy |
| POST | `/api/strategy/strategies/compare` | Compare strategies |

### Backtest

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/backtest/run` | Run single stock backtest |
| POST | `/api/backtest/backtest/strategy` | Run strategy backtest |
| POST | `/api/backtest/backtest/portfolio` | Run portfolio backtest |
| GET | `/api/backtest/results` | List backtest results |

### Simulation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/simulation/simulation/run` | Run simulation for strategy |
| POST | `/api/simulation/simulation/run-all` | Run all strategies |
| GET | `/api/simulation/simulation/trades` | List trades |
| GET | `/api/simulation/simulation/snapshots` | List snapshots |
| GET | `/api/simulation/simulation/performance` | Get performance metrics |

## Preset Strategies

The system includes 3 preset strategies:

### Conservative
- **Holding Days**: 30
- **Min Score**: 75
- **Position Size**: 5%
- **Max Positions**: 3

### Balanced
- **Holding Days**: 20
- **Min Score**: 60
- **Position Size**: 10%
- **Max Positions**: 5

### Aggressive
- **Holding Days**: 10
- **Min Score**: 50
- **Position Size**: 15%
- **Max Positions**: 8

## Frontend Pages

### Strategy Management (`/strategy`)
- List all strategies (preset + custom)
- Create/edit/delete custom strategies
- Strategy comparison view

### Backtest (`/backtest`)
- Strategy selector
- Single/Multi-stock toggle
- Time range selector
- Results with metrics, trades, and equity curve

### Simulation Dashboard (`/simulation`)
- Daily simulation trigger
- Trade list (open/closed)
- Performance metrics
- Portfolio value tracking

## File Structure (Updated 2026-05-26)

```
lobster_quant/src/
├── analysis/
│   └── backtest/                # 回测模块 (统一)
│       ├── __init__.py         # 导出所有回测相关类和函数
│       ├── engine.py           # BacktestEngine (单股票回测)
│       ├── portfolio.py        # PortfolioBacktest (组合回测)
│       └── metrics.py          # 指标计算函数 (统一)
├── data/
│   └── models.py                    # Strategy, BacktestMetrics, etc.
├── core/
│   ├── strategy_manager.py          # Strategy CRUD
│   ├── trade_simulator.py           # Daily simulation
│   └── scheduler.py                 # Scheduling
├── storage/
│   ├── strategy_store.py            # Strategy persistence
│   ├── backtest_store.py            # Backtest results
│   └── simulation_store.py          # Trades/snapshots
└── config/
    └── presets/                      # Preset strategy JSONs

backend/api/
├── routes/
│   ├── strategy.py                  # Strategy endpoints
│   ├── backtest.py                  # Backtest endpoints
│   └── simulation.py                # Simulation endpoints
└── models/
    ├── strategy.py                  # Strategy request/response
    └── simulation.py                # Simulation request/response

lobster-quant-web/src/
├── stores/
│   └── strategyStore.ts             # Zustand store
├── components/
│   ├── strategy/                    # Strategy components
│   ├── backtest/                    # Backtest components
│   └── simulation/                  # Simulation components
└── app/
    ├── strategy/page.tsx            # Strategy management page
    ├── backtest/page.tsx            # Backtest page
    └── simulation/page.tsx          # Simulation dashboard
```

### Import Path Migration

**旧路径 (已废弃)**:
```python
from src.core.portfolio_backtest import PortfolioBacktest
from lobster_quant.src.core.portfolio_backtest import PortfolioBacktest
```

**新路径 (推荐)**:
```python
from src.analysis.backtest.portfolio import PortfolioBacktest
from src.analysis.backtest import PortfolioBacktest
from lobster_quant.src.analysis.backtest.portfolio import PortfolioBacktest
```imulation components
└── app/
    ├── strategy/page.tsx            # Strategy management
    ├── backtest/page.tsx            # Enhanced backtest
    └── simulation/page.tsx          # Simulation dashboard
```

## Usage Examples

### Create a Custom Strategy

```typescript
const strategy = await createStrategy(
  "My Strategy",
  "Custom strategy for tech stocks",
  {
    holdingDays: 15,
    minScore: 65,
    positionSizing: "dynamic",
    positionSize: 0.12,
    initialCapital: 50000,
    maxPositions: 4
  }
);
```

### Run Backtest

```typescript
const result = await runBacktest({
  mode: "single",
  strategyId: "balanced",
  symbol: "AAPL",
  startDate: "2024-01-01",
  endDate: "2024-12-31"
});
```

### Run Daily Simulation

```typescript
const result = await runSimulation({
  strategyId: "conservative",
  market: "US"
});
```

## Performance Metrics

The system calculates the following metrics:

- **Total Return**: Overall percentage gain/loss
- **Annualized Return**: Yearly return rate
- **Volatility**: Standard deviation of returns (annualized)
- **Sharpe Ratio**: Risk-adjusted return (higher is better)
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of winning trades
- **Profit/Loss Ratio**: Average win / Average loss
- **Total Trades**: Number of trades executed

## Data Storage

All data is stored in JSON files under the `data/` directory:

```
data/
├── strategies/
│   ├── presets/           # Preset strategy configs
│   └── custom/            # User-created strategies
├── backtest_results/      # Backtest result history
└── simulation/
    ├── trades/            # Trade records by strategy
    └── snapshots/         # Daily portfolio snapshots
```

## Rolling Window Analysis

The system supports rolling window performance analysis:

- 1 Week (5 trading days)
- 1 Month (22 trading days)
- 3 Months (66 trading days)
- 6 Months (132 trading days)
- 1 Year (252 trading days)
- Year-to-Date (YTD)
- Custom range
