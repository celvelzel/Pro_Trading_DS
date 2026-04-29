以下是交给 AI Agent 完成该系统搭建与运行时所需的全部补充信息，包括技术环境、数据对接、配置调整、运行流程及常见问题预案。Agent 可依据此文档完成一站式部署。

---

## 一、项目概况与目标
复刻一个基于 Python 的量化研究辅助工具“龙虾辅助决策”，核心功能：
1. 多维度技术评分（趋势、动量、量能、形态）
2. OFF 过滤器（ATR、Gap、MA200、大盘风险）统计
3. 股票筛选器与个股深度分析
4. 固定持仓 20 日的历史回测
5. 通过 Streamlit 提供浏览器交互界面

要求：**不含期权模块**，支持美股和 A 股混排，可直接本地运行并通过浏览器访问。

---

## 二、技术栈与环境要求

| 组件 | 版本/说明 |
|------|-----------|
| Python | 3.9 ~ 3.11（推荐 3.10） |
| 包管理 | pip + `requirements.txt` |
| 前端 | Streamlit (>=1.25) |
| 数据获取 | yfinance（美股）、akshare（A股） |
| 指标计算 | pandas, numpy, pandas-ta（可选，目前用自实现） |
| 可视化 | plotly |
| 系统 | Windows / macOS / Linux 均可 |

**由于该工具仅本地使用，无需 API Key，但需网络连接以下载数据。**

---

## 三、文件结构与功能清单（Agent 必须创建的文件）

```
lobster_quant/
├── app.py                # Streamlit 主界面（三个标签页）
├── config.py             # 所有可调参数及股票池
├── data_fetcher.py       # 数据获取接口（美股/A股）
├── indicators.py         # 技术指标计算引擎
├── scoring.py            # 评分模型
├── backtest.py           # 回测引擎
├── off_filter.py         # OFF 过滤器
└── requirements.txt      # 项目依赖
```

每个文件的完整代码已在上一轮提供，Agent 可直接复制创建。

---

## 四、数据源对接细节

### 1. 美股数据（yfinance）
- 无需 API Key，直接使用 `yfinance.Ticker("MU").history(period="3y")`。
- 返回包含 OHLCV 的 DataFrame，时区已处理为 naive datetime。
- **注意**：yfinance 偶尔会因网络问题失败，可在 `_fetch_us_stock` 中增加重试（如 `try/except` 并 sleep 后重试）。

### 2. A股数据（akshare）
- 使用 `stock_zh_a_hist` 接口，传入 6 位代码（如 `"300308"`），`adjust="qfq"` 前复权。
- **关键点**：akshare 需要请求网络，`start_date` 设为 `"20190101"`，`end_date` 设为 `"20500101"` 以获取全部历史，但实际返回的截止日期为最新交易日。
- 若某只 A 股代码无效或网络错误，函数会返回 `None`，Agent 应在主流程中丢弃该股票并给出提示。
- **注意**：akshare 版本更新可能改变接口名称，若报错可尝试安装 `akshare>=1.13`。

### 3. 基准数据（用于 OFF 过滤器中的大盘风险）
- 固定使用 `"SPY"`（美股基准），在 `config.py` 中 `BENCHMARK = "SPY"`。
- 即使关注全部为 A 股，也建议保留此逻辑（可用沪深 300 替换，Agent 可根据需求修改，但默认代码使用 SPY）。

---

## 五、核心配置说明（`config.py`）

用户自定义区：
- **STOCK_LIST**：添加/删除股票代码，支持美股代码（字母）和 A 股代码（6 位数字字符串，如 `"600519"`）。
- **SCORE_WEIGHTS**：四个维度的权重，可调整。
- **技术指标周期**：如 MA20、RSI14、ATR14、布林带等，一般不需要改动。
- **OFF 过滤器阈值**：
  - `ATR_PCT_THRESHOLD = 0.05`（ATR 超过收盘价 5% 视为过高）
  - `GAP_STD_THRESHOLD = 2.0`（跳空幅度超过 2 倍标准差）
  - `MA200_RECOVERY_DAYS`（代码中实际未深度使用该数值，而是用“价格在 MA200 下且 MA200 下降”来判定）
- **回测参数**：
  - `HOLDING_DAYS = 20`
  - `MIN_SCORE_FOR_ENTRY = 50`

Agent 可根据用户需求在部署前调整这些参数。

---

## 六、运行流程与操作步骤

### 1. 环境初始化
```bash
cd lobster_quant
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 首次运行（数据下载）
```bash
streamlit run app.py
```
首次运行时，进度条会显示“下载数据中…”，系统将依次拉取股票池中所有标的的 3 年日线数据并计算指标。此过程需几分钟，务必等待完成后再使用界面。

### 3. 日常使用
- 数据缓存 1 小时，关闭浏览器后重开 Streamlit 页面仍会保留缓存，无需重复下载。
- 若想强制更新数据，可清空 Streamlit 缓存（点击界面右上角菜单 → Clear cache）。

### 4. 访问方式
- 本地启动后，浏览器打开 `http://localhost:8501`。
- 如需局域网内其他设备访问，启动时添加 `--server.address 0.0.0.0`。

---

## 七、系统使用指南（供 Agent 转达给用户）
- **仪表盘（Tab1）**：查看整体 ON/OFF 比例和 OFF 原因分布，辅助判断当前市场环境是否适合参与。
- **筛选器（Tab2）**：通过评分、MA 多头、 MACD 金叉、放量等条件筛选股票，点击下拉框选择后自动跳转深度分析。
- **个股分析（Tab3）**：可手动输入或从筛选器带过来的股票，展示 K 线+技术指标、回测统计、OFF 状态。

---

## 八、常见问题与 Agent 处理预案

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 启动后无数据，股票列表空白 | 数据下载失败 | 检查网络，在 `config.py` 中减少股票数量或仅用美股测试，查看终端报错信息。 |
| 某只 A 股代码导致崩溃 | akshare 对该代码返回异常 | 在 `_fetch_a_stock` 中已捕获异常并返回 None，主程序会跳过该股。Agent 可记录日志，后续排查代码是否正确。 |
| 回测无交易记录 | 评分阈值过高或数据不足 | 降低 `MIN_SCORE_FOR_ENTRY` 至 30，或确认有至少 500 个交易日的历史数据。 |
| OFF 过滤器占比过高 | 阈值过于严格 | 调高 `ATR_PCT_THRESHOLD` 至 0.08，或增大 `GAP_STD_THRESHOLD`。 |
| 界面卡在“下载数据中” | 某只股票拉取超时 | Agent 可在 `fetch_stock_data` 中加入 timeout 机制（如使用 `signal` 或 `concurrent.futures` 限制时间），但当前代码未包含，初次运行等待即可。 |
| plotly 图表不显示 | 浏览器问题或 Streamlit 版本 | 确保 `plotly>=5.15`，并尝试重启 Streamlit。 |

---

## 九、扩展与优化方向（Agent 可根据用户需求迭代）
- 增加实时数据推送与预警（需结合消息接口）。
- 增加动态止损、仓位管理模块。
- 回测对比基准指数收益曲线（目前仅有累计净值）。
- 多线程数据下载，加快启动速度。
- 将 A 股基准从 SPY 改为 CSI 300，可在 `off_filter.py` 中增加判断。

---

## 十、给 Agent 的执行指令建议
1. 创建上述 8 个文件并填入代码。
2. 确保 `requirements.txt` 中的包版本兼容。
3. 使用虚拟环境安装依赖。
4. 询问用户专注的股票池并填入 `config.py`，或先保留默认池验证。
5. 执行 `streamlit run app.py`，打开浏览器确认界面加载正常。
6. 向用户报告系统就绪，并解释三个标签页功能。

---

以上信息足以让一个 Agent 独立完成从环境搭建到系统跑通的全流程。若有不明之处可随时询问。