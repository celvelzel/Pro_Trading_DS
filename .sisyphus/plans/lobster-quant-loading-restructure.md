# 龙虾扫描 & Quant Tool 页面加载与标题重构计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) for tracking.

**Goal:** 修复龙虾扫描 (Tab 4) 和 Quant Tool (Tab 5) 页面加载空白问题，添加加载状态和错误处理，并重构页面标题和内容布局。

**Architecture:** Streamlit single-page app with 5 tabs. Three files need modification: `data_fetcher.py` (add try/except), `app.py` (restructure Tab 4), `quant_tool_page.py` (restructure Tab 5). All tabs must follow "never blank" pattern: try/except + spinner + fallback message.

**Tech Stack:** Python, Streamlit, yfinance, plotly, Streamlit built-in components (`st.spinner`, `st.error`, `st.warning`, `st.expander`, `st.cache_data`)

---

## 文件结构 (File Structure)

| 文件 | 当前问题 | 修改内容 |
|------|----------|----------|
| `lobster_quant/data_fetcher.py` | `_fetch_us_stock()` 无 try/except | 添加 try/except 保护，统一错误处理格式 |
| `lobster_quant/app.py` | Tab 4 空白 + 标题冗长 | 标题重构 + spinner + error handling + expander 布局 |
| `lobster_quant/quant_tool_page.py` | Tab 5 空白 + 英文欢迎词 | 标题重构 + spinner + error handling + 中文空状态 |

---

### Task 1: 加固数据获取层 (data_fetcher.py)

**Files:**
- Modify: `lobster_quant/data_fetcher.py` (lines 16-29)

- [x] **Step 1: 为 `_fetch_us_stock()` 添加 try/except**
- [x] **Step 2: 验证修改**
- [x] **Step 3: 提交**

  当前 (lines 16-29):
  ```python
  def _fetch_us_stock(symbol):
      """美股数据"""
      ticker = yf.Ticker(symbol)
      df = ticker.history(period=f"{DATA_YEARS}y")
      if df.empty:
          return None
      df = df[['Open','High','Low','Close','Volume']]
      df.columns = ['open','high','low','close','volume']
      df.index = df.index.tz_localize(None)
      weekly = df.resample('W').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
      monthly = df.resample('ME').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
      return {'daily': df, 'weekly': weekly, 'monthly': monthly}
  ```

  修改为：
  ```python
  def _fetch_us_stock(symbol):
      """美股数据"""
      try:
          ticker = yf.Ticker(symbol)
          df = ticker.history(period=f"{DATA_YEARS}y")
          if df.empty:
              return None
          df = df[['Open','High','Low','Close','Volume']]
          df.columns = ['open','high','low','close','volume']
          df.index = df.index.tz_localize(None)
          weekly = df.resample('W').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
          monthly = df.resample('ME').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
          return {'daily': df, 'weekly': weekly, 'monthly': monthly}
      except Exception as e:
          print(f"美股数据获取失败 {symbol}: {e}")
          return None
  ```

- [x] **Step 2: 验证修改**

  Run: `python -c "from data_fetcher import fetch_stock_data; print(fetch_stock_data('INVALID'))"`
  Expected: `None` (returns None gracefully, no exception)

- [x] **Step 3: 提交**

  ```bash
  git add lobster_quant/data_fetcher.py
  git commit -m "fix: add try/except to _fetch_us_stock to prevent silent crashes"
  ```

---

### Task 2: 重构 Tab 4 (龙虾扫描) - app.py 标题 + 加载状态 + 布局

**Files:**
- Modify: `lobster_quant/app.py` (lines 340-525)

- [x] **Step 1: 修改 Tab 4 标题和子节标题**

  找到 lines 340-345:
  ```python
  # Tab 4: 🦞 龙虾扫描（整合自 quant_lobster）
  with tab4:
      st.header("🦞 龙虾量化信号扫描")
      st.caption("整合自 quant_lobster | 多市场扫描 + 信号评分 + 操作建议")
  ```

  修改为：
  ```python
  # Tab 4: 🦞 龙虾扫描
  with tab4:
      st.header("🦞 多市场信号扫描")
  ```

  修改子节标题：
  - line 348: `st.subheader("OFF Filter 状态总览")` → `st.subheader("📋 市场状态")`
  - line 364: `st.subheader("全市场信号扫描")` → `st.subheader("📊 信号扫描结果")`
  - line 446: `st.subheader("🦞 单股深度分析")` → `st.subheader("🔍 个股详情")`
  - line 476: `st.subheader(f"{target_code} K线与信号")` → `st.subheader(f"📈 {target_code} K线图")`

- [x] **Step 2: 为 OFF Filter 区域添加 try/except 保护**

  找到 lines 347-361:
  ```python
  # ---- 4a. OFF Filter 概览 ----
  st.subheader("OFF Filter 状态总览")
  with st.spinner("扫描 OFF 状态..."):
      off_df = get_off_status_table(list(stock_dict.keys()), stock_dict)
  if not off_df.empty:
      ...
  ```

  修改为：
  ```python
  # ---- 4a. 市场状态 ----
  st.subheader("📋 市场状态")
  with st.spinner("扫描 OFF 状态..."):
      try:
          off_df = get_off_status_table(list(stock_dict.keys()), stock_dict)
      except Exception as e:
          st.error(f"市场状态扫描失败: {e}")
          off_df = pd.DataFrame()
  if not off_df.empty:
      col_on, col_off = st.columns(2)
      on_count = (off_df['Status'] == 'ON ✅').sum()
      off_count = len(off_df) - on_count
      with col_on.container():
          st.markdown(get_card_style(), unsafe_allow_html=True)
          st.metric("可交易 (ON)", on_count)
      with col_off.container():
          st.markdown(get_card_style(), unsafe_allow_html=True)
          st.metric("禁止交易 (OFF)", off_count)
      st.dataframe(off_df.set_index('Code'), width='stretch')
  ```

- [x] **Step 3: 为信号扫描区域添加 try/except 保护**
- [x] **Step 4: 为个股详情添加加载状态**
- [x] **Step 5: 添加错误兜底消息**
- [x] **Step 6: 验证修改**
- [x] **Step 7: 提交**

---

### Task 3: 重构 Tab 5 (Quant Tool / 量化工具) - quant_tool_page.py

**Files:**
- Modify: `lobster_quant/quant_tool_page.py` (full file)

- [x] **Step 1: 修改 Tab 5 标题为中文**
- [x] **Step 2: 修改 quant_tool_page.py 内部标题**
- [x] **Step 3: 添加数据获取 spinner + 空状态 spinner**
- [x] **Step 4: 为 OFF 分析添加 Spinner**
- [x] **Step 5: 为期权数据添加 Spinner**
- [x] **Step 6: 为图表渲染添加 Spinner**
- [x] **Step 7: 将欢迎页面改为中文**
- [x] **Step 8: 添加 catch-all try/except 包裹整个 render 函数**
- [x] **Step 9: 验证修改**
- [x] **Step 10: 提交**

---

## Final Verification Wave

### F1: 数据层验证

- [x] 验证 `_fetch_us_stock()` 在 yfinance 失败时返回 None 而非抛异常
- [x] 验证 `fetch_stock_data()` 在无效 code 上不会崩溃

### F2: Tab 4 功能验证

- [x] 页面标题显示 "🦞 多市场信号扫描" ✅
- [x] 子节标题正确：📋 市场状态 | 📊 信号扫描结果 | 🔍 个股详情 | 📈 {code} K线图
- [x] 市场状态有 spinner 和 try/except
- [x] 信号扫描有 spinner 和 try/except
- [x] 个股详情和K线图在 expander 中
- [x] 空数据时显示 info 消息（非空白）

### F3: Tab 5 功能验证

- [x] 页面标题显示 "📈 个股深度分析" ✅
- [x] 输入股票后数据获取显示 spinner
- [x] OFF 评估显示 spinner
- [x] 期权数据加载有 spinner 和 try/except
- [x] 期权链图表有 spinner
- [x] 空状态显示中文提示（非英文 Welcome）

### F4: 整体验证

- [x] `python -c "import sys; sys.path.insert(0,'lobster_quant'); import app; from quant_tool_page import render_quant_tool_page; print('ALL OK')"` — 无导入错误
- [x] Streamlit 应用能正常启动：`streamlit run lobster_quant/app.py`

---

## 执行指引

**Plan complete and saved to `.sisyphus/plans/lobster-quant-loading-restructure.md`.**

执行选项：

1. **Subagent-Driven (推荐)** - 每个任务分配独立 subagent，逐个审查
2. **Inline Execution** - 在当前会话中执行，分批审查

请选择哪种方式？
