# 模块整合迁移指南

## 概述

本文档描述了 Lobster Quant 项目模块整合的变更，帮助开发者从旧的导入路径迁移到新的路径。

## 变更摘要

### 1. 回测模块统一

**变更**: 将 `PortfolioBacktest` 从 `src/core/` 移动到 `src/analysis/backtest/`

**原因**:
- 统一所有回测相关功能到一个模块
- 提高代码可维护性
- 减少模块间的耦合

### 2. 指标计算统一

**变更**: 所有指标计算函数统一到 `src/analysis/backtest/metrics.py`

**原因**:
- 消除重复的指标计算代码
- 提供统一的指标计算接口
- 便于测试和维护

---

## 迁移步骤

### Step 1: 更新导入路径

#### PortfolioBacktest

**旧路径**:
```python
from src.core.portfolio_backtest import PortfolioBacktest, EquityPoint
from lobster_quant.src.core.portfolio_backtest import PortfolioBacktest
```

**新路径**:
```python
from src.analysis.backtest.portfolio import PortfolioBacktest, EquityPoint
from src.analysis.backtest import PortfolioBacktest
from lobster_quant.src.analysis.backtest.portfolio import PortfolioBacktest
```

#### BacktestEngine

**旧路径**:
```python
from src.analysis.backtest import BacktestEngine
from src.analysis.backtest.engine import BacktestEngine
```

**新路径** (无变化):
```python
from src.analysis.backtest import BacktestEngine
from src.analysis.backtest.engine import BacktestEngine
```

#### 指标计算函数

**旧路径**:
```python
from src.analysis.backtest.metrics import calculate_sharpe_ratio
```

**新路径** (无变化):
```python
from src.analysis.backtest.metrics import calculate_sharpe_ratio
from src.analysis.backtest import calculate_sharpe_ratio
```

---

### Step 2: 更新测试文件中的 Mock 路径

如果您在测试中使用了 `@patch` 装饰器，需要更新 mock 路径：

**旧路径**:
```python
@patch("src.core.portfolio_backtest.get_data_engine")
@patch("src.core.portfolio_backtest.get_indicator_engine")
@patch("src.core.portfolio_backtest.BacktestEngine")
```

**新路径**:
```python
@patch("src.analysis.backtest.portfolio.get_data_engine")
@patch("src.analysis.backtest.portfolio.get_indicator_engine")
@patch("src.analysis.backtest.portfolio.BacktestEngine")
```

---

### Step 3: 更新后端 API 导入

**旧路径**:
```python
from lobster_quant.src.core.portfolio_backtest import PortfolioBacktest
```

**新路径**:
```python
from lobster_quant.src.analysis.backtest.portfolio import PortfolioBacktest
```

---

## 验证迁移

### 1. 运行单元测试

```bash
cd lobster_quant
python -m pytest tests/ -v
```

### 2. 运行后端测试

```bash
cd backend
python -m pytest tests/ -v
```

### 3. 验证导入

```python
# 测试导入是否正常
from src.analysis.backtest import BacktestEngine, PortfolioBacktest
from src.analysis.backtest.portfolio import PortfolioBacktest, EquityPoint
from src.analysis.backtest.metrics import calculate_sharpe_ratio
```

---

## 常见问题

### Q1: 为什么移动 PortfolioBacktest？

**A**: 为了统一所有回测相关功能到一个模块，提高代码组织性和可维护性。

### Q2: 旧路径还能用吗？

**A**: 旧路径已经删除，不再可用。请更新到新路径。

### Q3: 需要更新所有文件吗？

**A**: 是的，所有引用旧路径的文件都需要更新。

### Q4: 测试会受到影响吗？

**A**: 测试需要更新 mock 路径，但测试逻辑本身不需要改变。

---

## 回滚计划

如果需要回滚到旧版本：

1. 恢复 `src/core/portfolio_backtest.py` 文件
2. 恢复 `src/core/__init__.py` 中的导入
3. 恢复所有测试文件中的导入路径
4. 恢复后端 API 中的导入路径

---

## 联系方式

如有问题，请联系项目维护者或查看项目文档。
