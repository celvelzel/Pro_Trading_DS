"""
Lobster Quant - Help Content Module
Centralized help text for all pages (Chinese).
Each page has: intro (detailed usage guide) + param descriptions (widget tooltips).
"""

# ============================================================
# Dashboard
# ============================================================
DASHBOARD_INTRO = """
## 📊 Dashboard 概览

Dashboard 是 Lobster Quant 的主控面板，提供市场整体状态的快速概览。

### 功能说明

- **Market Condition (市场状态)**: 显示 OFF Filter 的实时评估结果。ON 表示市场条件适合交易，OFF 表示存在风险因素建议观望。
- **Benchmark Price (基准价格)**: 显示当前设定的基准指数（默认 SPY）的最新价格。
- **ON/OFF Ratio (ON/OFF 比例)**: 历史数据中市场处于 ON 和 OFF 状态的时间占比。
- **Historical OFF Status (历史 OFF 状态)**: 以折线图展示 OFF Filter 的历史变化趋势。
- **Current Risk Factors (当前风险因素)**: 列出触发 OFF 状态的具体原因。

### OFF Filter 评估逻辑

OFF Filter 基于以下维度综合评估市场风险：
1. **ATR%**: 平均真实波幅百分比，衡量市场波动性
2. **MA200 恢复**: 价格是否低于 200 日均线且均线向下
3. **Gap 分析**: 开盘跳空幅度是否异常（超过 2 倍标准差）
4. **大盘风险**: 基准指数的 MA20 趋势
5. **流动性**: 成交量比率是否过低

### 使用建议

- 每日开盘前查看 Dashboard，了解市场整体环境
- OFF 状态时建议降低仓位或暂停新开仓
- 关注 Risk Factors 中的具体原因，判断风险是否可控
"""

# ============================================================
# Scanner
# ============================================================
SCANNER_INTRO = """
## 🔍 Stock Scanner 使用说明

Stock Scanner 是多市场股票扫描工具，基于综合评分系统快速筛选符合条件的股票。

### 功能说明

1. **选择市场**: 支持 US Stocks（美股）、HK Stocks（港股）、A-Shares（A股）三个市场
2. **设置最低分数**: 调整筛选门槛，只显示评分高于此值的股票
3. **点击 Scan**: 批量获取数据、计算指标、生成信号并排序展示

### 评分系统（0-100 分）

评分由四个维度加权计算：
- **趋势 (40%)**: 日/周/月均线斜率强度，反映价格运动方向
- **动量 (20%)**: RSI 指标 + 20 日收益率百分位，衡量价格动能
- **成交量 (15%)**: 成交量比率确认，判断趋势是否有量能支撑
- **技术形态 (25%)**: MACD 金叉、均线多头排列、布林带位置

### 信号类型

| 信号 | 条件 | 含义 |
|------|------|------|
| 强烈推荐 | 得分≥70 且上涨概率≥60% | 多项指标共振，强烈看多 |
| 推荐 | 得分≥50 且上涨概率≥50% | 多数指标偏多，建议关注 |
| 持有 | 得分≥30 | 中性信号，维持现有仓位 |
| 观望 | 得分<30 | 指标偏弱，建议观望 |

### 使用建议

- 先用较低的 Min Score（如 20）进行宽范围扫描
- 关注 Top Picks 中评分最高的股票
- 结合 Analyzer 页面对感兴趣的股票进行深入分析
"""

SCANNER_PARAMS = {
    "market": "选择要扫描的股票市场。美股包含科技巨头和 ETF，港股包含蓝筹股，A股包含沪深主板龙头。需在 Settings 中启用对应市场。",
    "min_score": "最低评分阈值（0-100）。只显示综合评分高于此值的股票。建议先设较低值（如 20）宽范围扫描，再逐步提高筛选门槛。",
}

# ============================================================
# Analyzer
# ============================================================
ANALYZER_INTRO = """
## 📈 Stock Analyzer 使用说明

Stock Analyzer 是个股深度分析工具，对单只股票进行全面的技术面评估。

### 功能说明

1. **输入股票代码**: 支持美股（如 AAPL）、港股（如 0700.HK）、A股（如 600519）
2. **点击 Analyze**: 获取数据并生成完整分析报告

### 分析内容

- **Signal (交易信号)**: 基于综合评分的交易建议，包含评分、上涨概率和推荐理由
- **Price Chart (价格图表)**: K 线图展示价格走势和技术指标
- **Key Metrics (关键指标)**:
  - Price: 最新收盘价
  - RSI: 相对强弱指数（14日），>70 超买，<30 超卖
  - ATR%: 平均真实波幅百分比，衡量波动性
  - Vol Ratio: 成交量比率，>1.5 表示放量
- **OFF Filter Status**: 该股票的交易条件评估
- **Backtest**: 基于历史数据的策略回测结果

### 使用建议

- 输入代码后点击 Analyze 即可获取完整分析
- RSI 在 30-70 之间为正常区间，极端值需关注反转风险
- ATR% 越高表示波动越大，需要更宽的止损
- 结合 OFF Filter Status 判断是否适合开仓
"""

ANALYZER_PARAMS = {
    "symbol": "股票代码。美股直接输入代码（如 AAPL、TSLA），港股需加 .HK 后缀（如 0700.HK），A 股输入 6 位数字代码（如 600519）。不区分大小写。",
}

# ============================================================
# Backtest
# ============================================================
BACKTEST_INTRO = """
## 🧪 Strategy Backtest 使用说明

Strategy Backtest 是策略回测工具，基于历史数据验证交易策略的表现。

### 功能说明

1. **输入股票代码**: 要回测的标的
2. **设置参数**: 持股天数和最低入场评分
3. **点击 Run Backtest**: 运行回测并查看结果

### 回测逻辑

- 基于综合评分系统生成每日评分
- 当评分高于入场阈值时买入
- 持有指定天数后卖出
- 计算每笔交易的收益率

### 结果指标

| 指标 | 说明 |
|------|------|
| Total Trades | 总交易次数 |
| Win Rate | 胜率（盈利交易占比） |
| Avg Return | 平均每笔交易收益率 |
| Profit Factor | 盈亏比（总盈利/总亏损） |
| Max Drawdown | 最大回撤幅度 |
| Cumulative Return | 累计收益率 |
| Sharpe Ratio | 夏普比率（风险调整后收益） |

### 使用建议

- 先用默认参数运行，了解基准表现
- 调整 Holding Days 观察不同持股周期的效果
- 提高 Min Score 可以筛选更高确信度的入场点
- 关注 Max Drawdown，评估策略的下行风险
- Sharpe Ratio > 1 表示风险调整后收益较好
"""

BACKTEST_PARAMS = {
    "symbol": "要回测的股票代码。支持美股、港股、A股代码。建议选择流动性好、历史数据充足的标的。",
    "holding_days": "持股天数（5-60天）。买入后持有多少个交易日卖出。较短周期（5-10天）适合短线，较长周期（20-60天）适合中线。",
    "min_score": "最低入场评分（0-100）。只有当综合评分高于此值时才会触发买入。分值越高，入场条件越严格，交易次数越少但确信度越高。",
}

# ============================================================
# Quant Tool
# ============================================================
QUANT_TOOL_INTRO = """
## 🔧 Quant Tool 使用说明

Quant Tool 是期权分析工具，提供 OFF 评估、Max Pain、支撑/阻力位等期权市场关键指标。

### 功能说明

1. **输入股票代码**: 支持有期权的美股标的（如 AAPL、MSFT、TSLA）
2. **点击 获取数据**: 加载股票数据和期权链数据

### 分析模块

#### 🎯 OFF 评估
- 显示 ON/OFF 概率
- 列出风险因素：ATR%、MA200 距离、大盘环境
- ON 表示市场条件适合交易，OFF 表示建议观望

#### 📊 期权分析
- **Max Pain (最大痛点)**: 期权到期时造成最大损失的行权价，是期权卖方的"磁吸"目标
- **Support (支撑位)**: Put 未平仓量最大的行权价，下行支撑
- **Resistance (阻力位)**: Call 未平仓量最大的行权价，上行阻力
- **Put/Call Ratio**: 看跌/看涨比率，>1 表示看跌情绪偏重

#### 📈 期权链图表
- **Volume by Strike**: 各行权价的 Call/Put 成交量对比
- **Open Interest by Strike**: 各行权价的 Call/Put 未平仓量对比

### 使用建议

- 重点关注 Max Pain 与当前价格的距离
- 支撑位和阻力位可作为期权策略的行权价选择参考
- Put/Call Ratio 突然变化可能预示市场情绪转向
- 图表显示 ±30% 范围内的行权价，聚焦关键区域
"""

QUANT_TOOL_PARAMS = {
    "symbol": "股票代码。仅支持美股中有期权的标的。输入代码后点击「获取数据」加载分析。常用标的：AAPL、MSFT、TSLA、NVDA、SPY、QQQ。",
}

# ============================================================
# Settings
# ============================================================
SETTINGS_INTRO = """
## ⚙️ Settings 使用说明

Settings 页面管理 Lobster Quant 的全局配置参数。修改后需点击「Save Settings」保存。

### 配置分类

- **Market Configuration**: 启用/禁用不同市场的股票扫描
- **Data Configuration**: 历史数据范围和缓存设置
- **Scoring Weights**: 评分系统各维度的权重（必须总和为 1.0）
- **Backtest Configuration**: 回测策略参数
- **OFF Filter Parameters**: OFF Filter 的风险阈值

### 注意事项

- 部分设置修改后需要重启应用才能生效
- 评分权重之和必须接近 1.0，否则会显示警告
- OFF Filter 阈值影响交易信号的灵敏度，建议小幅调整后观察效果
"""

SETTINGS_PARAMS = {
    "enable_us_stock": "启用美股市场。启用后 Scanner 可以扫描美股标的，数据源为 yfinance。",
    "enable_hk_stock": "启用港股市场。启用后 Scanner 可以扫描港股标的，数据源为 yfinance。",
    "enable_a_stock": "启用 A 股市场。启用后 Scanner 可以扫描 A 股标的，数据源为 akshare。",
    "data_years": "历史数据年数（1-10年）。拉取多少年的历史数据用于分析和回测。数据越多，长期趋势分析越准确，但加载速度会变慢。建议 3-5 年。",
    "cache_ttl": "缓存过期时间（300-7200秒）。数据在本地缓存的有效期。较短的 TTL 保证数据新鲜度但增加 API 调用。较长的 TTL 减少请求但数据可能滞后。",
    "trend_weight": "趋势维度权重（0.0-1.0）。基于日/周/月均线斜率的趋势强度。默认 0.40（40%）。趋势是评分系统中权重最高的维度。",
    "momentum_weight": "动量维度权重（0.0-1.0）。基于 RSI 和 20 日收益率的动量信号。默认 0.20（20%）。",
    "volume_weight": "成交量维度权重（0.0-1.0）。基于成交量比率的量能确认。默认 0.15（15%）。",
    "pattern_weight": "技术形态维度权重（0.0-1.0）。基于 MACD 金叉、均线排列、布林带位置的形态分析。默认 0.25（25%）。",
    "holding_days": "回测默认持股天数（5-60天）。买入后持有多少个交易日自动卖出。",
    "min_score": "回测默认最低入场评分（0-100）。评分高于此值才会触发买入信号。",
    "atr_threshold": "OFF Filter 的 ATR% 阈值（0.01-0.20）。当平均真实波幅百分比超过此值时触发 OFF。默认 0.05（5%）。提高此值会减少 OFF 触发频率。",
    "gap_threshold": "OFF Filter 的跳空阈值（0.01-0.30）。当开盘跳空幅度超过此值时触发 OFF。默认 0.08（8%）。提高此值对大跳空更宽容。",
}

# ============================================================
# Aggregated help dict for easy lookup
# ============================================================
PAGE_INTROS = {
    "dashboard": DASHBOARD_INTRO,
    "scanner": SCANNER_INTRO,
    "analyzer": ANALYZER_INTRO,
    "backtest": BACKTEST_INTRO,
    "quant_tool": QUANT_TOOL_INTRO,
    "settings": SETTINGS_INTRO,
}

PAGE_PARAMS = {
    "scanner": SCANNER_PARAMS,
    "analyzer": ANALYZER_PARAMS,
    "backtest": BACKTEST_PARAMS,
    "quant_tool": QUANT_TOOL_PARAMS,
    "settings": SETTINGS_PARAMS,
}
