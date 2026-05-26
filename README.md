# Lobster Quant - 专业量化交易平台

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)
![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)

**一个全功能的量化交易分析平台，支持多市场股票分析、技术指标计算、信号生成和策略回测。**

[功能特性](#功能特性) • [快速开始](#快速开始) • [项目架构](#项目架构) • [API文档](#api文档) • [配置说明](#配置说明) • [开发指南](#开发指南)

</div>

---

## 📋 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目架构](#项目架构)
- [核心模块](#核心模块)
- [API文档](#api文档)
- [前端界面](#前端界面)
- [配置说明](#配置说明)
- [开发指南](#开发指南)
- [测试](#测试)
- [部署](#部署)
- [更新日志](#更新日志)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 🚀 功能特性

### 多市场支持
- **美股**: 通过 yfinance 获取实时和历史数据
- **港股**: 支持港股主板股票
- **A股**: 通过 akshare 获取A股数据

### 技术分析引擎
- **移动平均线**: MA5/10/20/60/120/200
- **动量指标**: RSI、ROC、Stochastic
- **趋势指标**: MACD、ADX、线性回归斜率
- **波动率指标**: ATR、Bollinger Bands
- **成交量指标**: OBV、成交量比率

### 智能信号系统
- **多因子评分**: 基于趋势(40%)、动量(20%)、成交量(15%)、形态(25%)的综合评分
- **信号分类**: 强烈推荐、推荐、持有、观望、卖出
- **风险过滤**: OFF过滤器用于识别异常市场状态

### 策略回测
- **历史回测**: 支持自定义回测周期
- **滑点模拟**: 真实的交易成本模拟
- **绩效指标**: Sharpe比率、Sortino比率、最大回撤、胜率、盈亏比
- **权益曲线**: 可视化回测结果

### 股票扫描器
- **批量扫描**: 支持同时扫描多只股票
- **评分筛选**: 按最低评分过滤
- **市场分类**: 美股、港股、A股独立扫描

### 现代化前端
- **响应式设计**: 支持桌面和移动端
- **暗色模式**: 完整的明暗主题切换
- **专业图表**: TradingView Lightweight Charts
- **实时更新**: TanStack Query 数据同步

---

## 🛠️ 技术栈

### 后端 (Python)

| 组件 | 技术 | 用途 |
|------|------|------|
| Web框架 | FastAPI | REST API服务 |
| 数据验证 | Pydantic v2 | 请求/响应模型 |
| 数据处理 | pandas, numpy | 金融数据计算 |
| 美股数据 | yfinance | 美股/港股数据源 |
| A股数据 | akshare | A股数据源 |
| 可视化 | Plotly | 图表生成 |
| 配置管理 | pydantic-settings | 环境变量和配置 |

### 前端 (TypeScript)

| 组件 | 技术 | 用途 |
|------|------|------|
| 框架 | Next.js 16 (App Router) | React全栈框架 |
| UI组件 | shadcn/ui + Radix UI | 组件库 |
| 样式 | Tailwind CSS v4 | 原子化CSS |
| 状态管理 | Zustand | 客户端状态 |
| 数据获取 | TanStack Query | 服务端状态 |
| 图表 | TradingView Lightweight Charts | K线图表 |
| 主题 | next-themes | 主题切换 |

---

## 🏁 快速开始

### 前置要求

- **Python 3.10+**
- **Node.js 18+**
- **npm 9+** 或 **pnpm** 或 **yarn**

### 一键启动 (推荐)

```powershell
# Windows PowerShell
.\start-dev.ps1
```

此脚本会自动:
1. 检查依赖环境
2. 安装缺失的依赖
3. 启动后端 (http://localhost:8000)
4. 启动前端 (http://localhost:3000)

### 手动启动

#### 1. 克隆项目

```bash
git clone https://github.com/lobster-quant/lobster-quant.git
cd lobster-quant
```

#### 2. 启动后端

```bash
cd backend

# 创建虚拟环境 (推荐)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

后端将在 http://localhost:8000 启动

#### 3. 启动前端

```bash
cd lobster-quant-web

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:3000 启动

### 访问应用

- **前端界面**: http://localhost:3000
- **API文档**: http://localhost:8000/docs (Swagger UI)
- **API健康检查**: http://localhost:8000/health

---

## 🏗️ 项目架构

```
Pro_Trading_DS/
├── backend/                    # FastAPI 后端服务
│   ├── api/
│   │   ├── models/            # Pydantic 数据模型
│   │   │   ├── backtest.py   # 回测请求/响应模型
│   │   │   ├── scanner.py    # 扫描器模型
│   │   │   ├── settings.py   # 设置模型
│   │   │   ├── stocks.py     # 股票数据模型
│   │   │   └── common.py     # 通用模型
│   │   └── routes/            # API路由
│   │       ├── backtest.py   # 回测端点
│   │       ├── scanner.py    # 扫描器端点
│   │       ├── settings.py   # 设置端点
│   │       └── stocks.py     # 股票数据端点
│   ├── main.py                # FastAPI 应用入口
│   └── requirements.txt       # Python依赖
│
├── lobster_quant/             # 核心量化分析库
│   ├── src/
│   │   ├── analysis/          # 分析模块
│   │   │   ├── backtest/     # 回测引擎
│   │   │   │   ├── engine.py # 回测执行器
│   │   │   │   └── metrics.py# 绩效指标计算
│   │   │   ├── indicators/   # 技术指标
│   │   │   │   ├── base.py   # 基础指标函数
│   │   │   │   ├── momentum.py# 动量指标
│   │   │   │   ├── trend.py  # 趋势指标
│   │   │   │   ├── volatility.py# 波动率指标
│   │   │   │   └── volume.py # 成交量指标
│   │   │   └── signals/      # 信号生成
│   │   │       └── lobster_signal.py# 多因子信号
│   │   ├── config/            # 配置管理
│   │   │   ├── defaults.yaml # 默认配置
│   │   │   ├── settings.py   # Pydantic设置
│   │   │   └── presets/      # 预设配置
│   │   ├── core/              # 核心引擎
│   │   │   ├── data_engine.py# 数据引擎
│   │   │   ├── indicator_engine.py# 指标引擎
│   │   │   ├── signal_engine.py# 信号引擎
│   │   │   ├── risk_engine.py# 风险引擎
│   │   │   └── strategy_manager.py# 策略管理
│   │   ├── data/              # 数据层
│   │   │   ├── cache.py      # 数据缓存
│   │   │   ├── models.py     # 数据模型
│   │   │   └── providers/    # 数据源提供者
│   │   ├── storage/           # 持久化存储
│   │   │   ├── backtest_store.py
│   │   │   ├── simulation_store.py
│   │   │   └── strategy_store.py
│   │   └── utils/             # 工具函数
│   │       ├── exceptions.py # 自定义异常
│   │       └── logging.py    # 日志配置
│   ├── tests/                 # 单元测试
│   └── pyproject.toml        # Python项目配置
│
├── lobster-quant-web/         # Next.js 前端
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   │   ├── dashboard/    # 仪表盘页面
│   │   │   ├── analysis/     # 股票分析页面
│   │   │   ├── scanner/      # 股票扫描页面
│   │   │   ├── backtest/     # 回测页面
│   │   │   └── settings/     # 设置页面
│   │   ├── components/        # React组件
│   │   │   ├── charts/       # 图表组件
│   │   │   ├── cards/        # 卡片组件
│   │   │   ├── layout/       # 布局组件
│   │   │   └── ui/           # UI基础组件
│   │   ├── hooks/             # React Hooks
│   │   ├── lib/               # 工具函数和常量
│   │   ├── providers/         # Context Providers
│   │   └── stores/            # Zustand状态
│   ├── public/                # 静态资源
│   ├── package.json           # Node.js依赖
│   └── tsconfig.json          # TypeScript配置
│
├── data/                      # 数据目录
│   └── cache/                # 数据缓存
│
├── docs/                      # 项目文档
│   ├── updates/              # 更新日志
│   └── superpowers/          # 开发计划
│
├── logs/                      # 日志文件
├── start-dev.ps1             # 开发启动脚本
├── .gitignore                # Git忽略配置
└── README.md                 # 项目说明
```

---

## 📦 核心模块

### 1. 数据引擎 (DataEngine)

统一的数据访问层，支持多数据源和缓存。

```python
from lobster_quant.src.core.data_engine import get_data_engine

engine = get_data_engine()
stock_data = engine.fetch_stock("AAPL")
```

**特性**:
- 多数据源抽象 (yfinance, akshare, mock)
- 持久化磁盘缓存
- 异步批量获取
- 健康监控

### 2. 指标引擎 (IndicatorEngine)

计算所有技术指标。

```python
from lobster_quant.src.core.indicator_engine import get_indicator_engine

engine = get_indicator_engine()
df_with_indicators = engine.compute_all(stock_data.daily)
```

**支持的指标**:
- MA (5, 10, 20, 60, 120, 200)
- RSI (14)
- MACD (12, 26, 9)
- ATR (14)
- Bollinger Bands (20, 2)
- OBV
- Stochastic
- ADX

### 3. 信号生成器 (SignalGenerator)

基于多因子模型生成交易信号。

```python
from lobster_quant.src.analysis.signals import SignalGenerator

generator = SignalGenerator()
score = generator.calculate_score(df_with_indicators)
```

**评分体系**:
- 趋势得分 (40%): MA斜率、均线排列
- 动量得分 (20%): RSI、ROC
- 成交量得分 (15%): OBV趋势、量比
- 形态得分 (25%): MACD、均线金叉/死叉

**信号分类**:
| 评分范围 | 信号类型 | 建议 |
|----------|----------|------|
| 80-100 | 强烈推荐 | 强势买入 |
| 60-79 | 推荐 | 适量买入 |
| 40-59 | 持有 | 持有观望 |
| 20-39 | 观望 | 谨慎观望 |
| 0-19 | 卖出 | 考虑卖出 |

### 4. 回测引擎 (BacktestEngine)

策略回测和绩效分析。

```python
from lobster_quant.src.analysis.backtest import BacktestEngine

engine = BacktestEngine()
results = engine.run(data, score_series, symbol="AAPL")
```

**特性**:
- 固定持仓周期
- 滑点模拟 (默认0.1%)
- 手续费计算 (默认0.1%)
- 风险管理 (止损)
- 全面的绩效指标

**绩效指标**:
- 总收益率
- 年化收益率
- Sharpe比率
- Sortino比率
- 最大回撤
- 胜率
- 盈亏比

---

## 📡 API文档

### 基础端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | API根路径 |
| GET | `/health` | 健康检查 |

### 股票数据 `/api/stocks`

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/{symbol}` | 获取股票OHLCV数据 |
| GET | `/{symbol}/indicators` | 获取技术指标 |
| GET | `/{symbol}/signal` | 获取交易信号 |
| GET | `/{symbol}/risk` | 获取风险评估 |

**参数**:
- `symbol`: 股票代码 (如 AAPL, 0700.HK, 600519)
- `period`: 时间周期 (1d, 1w, 1m, 3m, 6m, 1y, 5y)

### 股票扫描 `/api/scanner`

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/scan` | 扫描股票 |

**请求体**:
```json
{
  "market": "US",  // US, HK, A
  "minScore": 60   // 最低评分 (0-100)
}
```

### 策略回测 `/api/backtest`

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/run` | 运行回测 |

**请求体**:
```json
{
  "symbol": "AAPL",
  "period": "1y",
  "holdingDays": 20,
  "minScore": 20,
  "slippagePct": 0.001,
  "commissionPct": 0.001
}
```

### 设置管理 `/api/settings`

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 获取当前设置 |
| PUT | `/` | 更新设置 |

### 交互式文档

启动后端后访问:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🖥️ 前端界面

### 仪表盘 (Dashboard)
- 市场状态概览
- SPY基准指数实时数据
- 自选股列表
- 快速分析入口

### 股票分析 (Analysis)
- 专业K线图表 (TradingView Lightweight Charts)
- 技术指标叠加显示
- 信号卡片展示
- 风险评估面板

### 股票扫描 (Scanner)
- 市场选择 (美股/港股/A股)
- 评分阈值筛选
- 批量扫描结果
- 虚拟滚动优化 (大量结果)

### 策略回测 (Backtest)
- 回测参数配置
- 权益曲线图表
- 交易记录表格
- 绩效指标展示

### 设置 (Settings)
- 数据源配置
- 指标参数调整
- 评分权重设置
- 回测参数设置

---

## ⚙️ 配置说明

### 环境变量

在项目根目录创建 `.env` 文件:

```env
# 应用配置
APP_NAME=Lobster Quant
DEBUG=false
LOG_LEVEL=INFO

# 市场配置
ENABLE_US_STOCK=true
ENABLE_HK_STOCK=true
ENABLE_A_STOCK=false

# 数据配置
DATA_YEARS=3
DATA_CACHE_DIR=./data/cache
DATA_CACHE_TTL=3600
DATA_TIMEOUT=10

# 数据源
US_DATA_PROVIDER=yfinance
HK_DATA_PROVIDER=yfinance
A_DATA_PROVIDER=akshare

# 指标参数
MA_SHORT_PERIOD=20
MA_LONG_PERIOD=200
RSI_PERIOD=14
ATR_PERIOD=14
MACD_FAST=12
MACD_SLOW=26
MACD_SIGNAL=9
BB_PERIOD=20
BB_STD=2.0

# 评分权重 (总和为1.0)
SCORE_WEIGHT_TREND=0.40
SCORE_WEIGHT_MOMENTUM=0.20
SCORE_WEIGHT_VOLUME=0.15
SCORE_WEIGHT_PATTERN=0.25

# 回测参数
BACKTEST_HOLDING_DAYS=20
BACKTEST_MIN_SCORE=20
BACKTEST_LOOKBACK_DAYS=500
BACKTEST_SLIPPAGE_PCT=0.001
BACKTEST_COMMISSION_PCT=0.001

# 基准
BENCHMARK_SYMBOL=SPY
```

### 预设配置

项目提供三种预设配置:

#### 保守型 (Conservative)
```json
{
  "scoring_weights": {
    "trend": 0.50,
    "momentum": 0.15,
    "volume": 0.10,
    "pattern": 0.25
  },
  "backtest": {
    "holding_days": 10,
    "min_score": 40
  }
}
```

#### 平衡型 (Balanced)
```json
{
  "scoring_weights": {
    "trend": 0.40,
    "momentum": 0.20,
    "volume": 0.15,
    "pattern": 0.25
  },
  "backtest": {
    "holding_days": 20,
    "min_score": 20
  }
}
```

#### 激进型 (Aggressive)
```json
{
  "scoring_weights": {
    "trend": 0.30,
    "momentum": 0.30,
    "volume": 0.20,
    "pattern": 0.20
  },
  "backtest": {
    "holding_days": 30,
    "min_score": 10
  }
}
```

---

## 💻 开发指南

### 后端开发

#### 添加新的技术指标

1. 在 `lobster_quant/src/analysis/indicators/` 创建新文件
2. 实现指标计算函数
3. 在 `indicator_engine.py` 中注册

```python
# lobster_quant/src/analysis/indicators/custom.py
import pandas as pd

def calculate_custom_indicator(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算自定义指标."""
    # 实现计算逻辑
    return result_series
```

#### 添加新的API端点

1. 在 `backend/api/models/` 定义请求/响应模型
2. 在 `backend/api/routes/` 创建路由
3. 在 `backend/main.py` 注册路由

```python
# backend/api/routes/custom.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/custom-endpoint")
async def custom_endpoint():
    return {"message": "Custom endpoint"}
```

### 前端开发

#### 添加新页面

1. 在 `lobster-quant-web/src/app/` 创建页面目录
2. 创建 `page.tsx` 文件
3. 在侧边栏导航中添加链接

```typescript
// lobster-quant-web/src/app/custom/page.tsx
export default function CustomPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold">Custom Page</h1>
    </div>
  )
}
```

#### 添加新组件

1. 在 `lobster-quant-web/src/components/` 创建组件
2. 使用 shadcn/ui 组件库
3. 遵循现有组件模式

```typescript
// lobster-quant-web/src/components/cards/CustomCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface CustomCardProps {
  title: string
  children: React.ReactNode
}

export function CustomCard({ title, children }: CustomCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}
```

### 代码规范

#### Python (后端)

- 使用 Black 格式化代码
- 使用 Ruff 进行代码检查
- 使用 mypy 进行类型检查
- 遵循 PEP 8 规范

```bash
# 格式化
black .

# 检查
ruff check .

# 类型检查
mypy .
```

#### TypeScript (前端)

- 使用 ESLint 进行代码检查
- 遵循 Next.js 最佳实践
- 使用 TypeScript 严格模式

```bash
# 检查
npm run lint

# 构建验证
npm run build
```

---

## 🧪 测试

### 后端测试

```bash
cd lobster_quant

# 运行所有测试
pytest

# 运行带覆盖率的测试
pytest --cov=src --cov-report=html

# 运行特定测试
pytest tests/unit/test_metrics.py
```

### 前端测试

```bash
cd lobster-quant-web

# 运行E2E测试
npm run test:e2e

# 运行带UI的E2E测试
npm run test:e2e:ui
```

---

## 🚀 部署

### 生产构建

#### 前端

```bash
cd lobster-quant-web
npm run build
npm run start
```

#### 后端

```bash
cd backend
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker部署 (计划中)

```bash
docker-compose up -d
```

---

## 📝 更新日志

### Phase 1 (2026-05-09)

#### 核心架构升级
- **前端重构**: 迁移至 Next.js 16 (App Router)
- **后端分离**: 引入 FastAPI 中间件
- **状态管理**: 集成 TanStack Query

#### UI/UX 重定义
- **Google Finance 设计语言**: 专业金融设计风格
- **主题支持**: 完整的明暗模式切换
- **响应式布局**: 优化多端体验

#### 核心功能整合
- **统一分析工作台**: 合并 Analyzer 和 Quant Tool
- **专业图表**: 接入 TradingView Lightweight Charts

#### 稳定性修复
- 解决端口占用和进程冲突
- 修复类型错误和接口问题
- 通过生产构建验证

---

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 提交规范

使用语义化提交信息:

```
feat: 添加新功能
fix: 修复bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建/工具变更
```

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 🙏 致谢

- [TradingView Lightweight Charts](https://github.com/nicholasgasior/lightweight-charts) - 专业金融图表库
- [shadcn/ui](https://ui.shadcn.com/) - 现代化UI组件库
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Python Web框架
- [Next.js](https://nextjs.org/) - React全栈框架
- [yfinance](https://github.com/ranaroussi/yfinance) - 美股数据源
- [akshare](https://github.com/akfamily/akshare) - A股数据源

---

<div align="center">

**[⬆ 回到顶部](#lobster-quant---专业量化交易平台)**

Made with ❤️ by Lobster Quant Team

</div>
