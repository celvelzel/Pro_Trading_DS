import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import time

from config import (STOCK_LIST, BENCHMARK, is_a_stock, is_hk_stock,
                    ENABLE_MARKETS, DEFAULT_UNIVERSE, SCORING_WEIGHTS)
from data_fetcher import fetch_stock_data, fetch_benchmark
from indicators import compute_indicators, compute_weekly_monthly_slopes
from scoring import compute_score
from backtest import run_backtest, backtest_summary
from off_filter import compute_off_filter, get_on_off_stats
from lobster_signal import SignalGenerator, volume_ratio
from lobster_off_filter import should_trade, get_off_status_table
from quant_tool_page import render_quant_tool_page
from theme_manager import init_theme, apply_theme, get_card_style

st.set_page_config(layout="wide", page_title="Pro_Trading_DS")

init_theme()

with st.sidebar:
    theme_toggle = st.toggle("Dark Mode", value=(st.session_state.theme == 'dark'))
    if theme_toggle:
        if st.session_state.theme != 'dark':
            st.session_state.theme = 'dark'
            apply_theme('dark')
            st.rerun()
    else:
        if st.session_state.theme != 'light':
            st.session_state.theme = 'light'
            apply_theme('light')
            st.rerun()

st.title("Pro_Trading_DS")
st.caption("Quantitative Trading Research Tool")

# ============================================================
# Data Loading with Caching
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data():
    """Load all stock data - cached for 1 hour"""
    progress_bar = st.progress(0, text="Initializing...")

    bench = fetch_benchmark()
    stock_data = {}
    total = len(STOCK_LIST)
    for i, code in enumerate(STOCK_LIST):
        progress_bar.progress((i + 1) / total, text=f"Loading {code}...")
        data = fetch_stock_data(code)
        if data is not None and not data.get('daily', pd.DataFrame()).empty:
            daily = compute_indicators(data['daily'])
            slopes = compute_weekly_monthly_slopes(data)
            score = compute_score(daily, slopes)
            stock_data[code] = {
                'daily': daily,
                'weekly': data['weekly'],
                'monthly': data['monthly'],
                'score': score,
                'slopes': slopes
            }
        time.sleep(0.05)

    progress_bar.empty()
    return bench, stock_data, datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ============================================================
# Session State
# ============================================================
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

with st.spinner('Loading market data...'):
    bench, stock_dict, update_time = load_all_data()

st.session_state.last_update = update_time

if not stock_dict:
    st.warning("No stock data loaded. Please refresh later.")
    st.stop()

# Sidebar status
st.sidebar.markdown("---")
st.sidebar.markdown("### Data Status")
st.sidebar.write(f"**Last Update:** {update_time}")

try:
    last_dt = datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S')
    age_minutes = (datetime.now() - last_dt).total_seconds() / 60
    if age_minutes > 60:
        st.sidebar.warning(f"Data is {int(age_minutes)} min old - may be outdated!")
    else:
        st.sidebar.success(f"Data is {int(age_minutes)} min old")
except Exception:
    pass

st.write(f":green[Loaded {len(stock_dict)} stocks] | Updated: {update_time}")

# ============================================================
# Tabs: OFF Filter | Stock Selector | Stock Analysis | 龙虾扫描 | Quant Tool
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "OFF Filter",
    "Stock Selector",
    "Stock Analysis",
    "🦞 龙虾扫描",
    "📈 Quant Tool"
])

# ============================================================
# Tab 1: OFF Filter
# ============================================================
with tab1:
    st.header("OFF Filter Status")
    st.markdown("OFF (not trading) is a strategy to avoid poor market conditions.")

    total_on_days = 0
    total_days = 0
    all_reasons = {}
    for code, d in stock_dict.items():
        off_res, reasons_dict = compute_off_filter(d['daily'], bench)
        stats = get_on_off_stats(d['daily'], off_res)
        total_on_days += stats['total_days'] - stats['off_days']
        total_days += stats['total_days']
        for r, count in stats['reasons'].items():
            all_reasons[r] = all_reasons.get(r, 0) + count

    on_pct = total_on_days / total_days * 100 if total_days else 0
    off_pct = 100 - on_pct

    col1, col2 = st.columns(2)
    with col1.container():
        st.markdown(get_card_style(), unsafe_allow_html=True)
        st.metric("ON (Allowed)", f"{on_pct:.1f}%")
    with col2.container():
        st.markdown(get_card_style(), unsafe_allow_html=True)
        st.metric("OFF (Avoid)", f"{off_pct:.1f}%")

    if all_reasons:
        st.subheader("OFF Reasons")
        reason_df = pd.DataFrame({
            'Reason': list(all_reasons.keys()),
            'Count': list(all_reasons.values())
        }).sort_values('Count', ascending=False)
        st.bar_chart(reason_df.set_index('Reason'))

# ============================================================
# Tab 2: Stock Selector
# ============================================================
with tab2:
    st.header("Stock Selector")

    snapshot = []
    for code, d in stock_dict.items():
        daily = d['daily'].dropna(subset=['close', 'ma20'])
        if daily.empty:
            continue
        latest = daily.iloc[-1]
        score_series = d['score'].reindex(daily.index).dropna()
        if score_series.empty:
            continue
        score_val = score_series.iloc[-1]
        rsi_val = latest.get('rsi', np.nan)
        slope_d = latest.get('slope_daily', np.nan)
        slope_w = d['slopes']['slope_weekly'].iloc[-1] if len(d['slopes']) > 0 else np.nan
        slope_m = d['slopes']['slope_monthly'].iloc[-1] if len(d['slopes']) > 0 else np.nan
        tags = []
        if latest.get('ma_bullish', False):
            tags.append('MA Bullish')
        if latest.get('macd_golden', False):
            tags.append('MACD Gold')
        if latest.get('volume_ratio', 0) > 1.5:
            tags.append('High Vol')
        if slope_d > 0 and slope_w > 0 and slope_m > 0:
            tags.append('Uptrend')

        snapshot.append({
            'Code': code,
            'Price': round(latest['close'], 2),
            'Score': round(score_val, 1) if not pd.isna(score_val) else 0,
            'SlopeD': f"{slope_d:.2f}" if not pd.isna(slope_d) else "N/A",
            'SlopeW': f"{slope_w:.2f}" if not pd.isna(slope_w) else "N/A",
            'SlopeM': f"{slope_m:.2f}" if not pd.isna(slope_m) else "N/A",
            'RSI': round(rsi_val, 1) if not pd.isna(rsi_val) else "N/A",
            'Tags': ', '.join(tags)
        })

    df_snapshot = pd.DataFrame(snapshot)

    st.sidebar.header("Filters")
    min_score = st.sidebar.slider("Min Score", 0, 100, 15)
    min_rsi = st.sidebar.slider("RSI Min", 0, 100, 0)
    max_rsi = st.sidebar.slider("RSI Max", 0, 100, 100)
    show_ma = st.sidebar.checkbox("MA Bullish")
    show_golden = st.sidebar.checkbox("MACD Gold")
    show_vol = st.sidebar.checkbox("High Vol")

    filtered = df_snapshot[df_snapshot['Score'] >= min_score]
    if show_ma:
        filtered = filtered[filtered['Tags'].str.contains('MA Bullish', na=False)]  # type: ignore
    if show_golden:
        filtered = filtered[filtered['Tags'].str.contains('MACD Gold', na=False)]  # type: ignore
    if show_vol:
        filtered = filtered[filtered['Tags'].str.contains('High Vol', na=False)]  # type: ignore

    rsi_col = filtered['RSI'].replace('N/A', np.nan)  # type: ignore
    rsi_vals = pd.to_numeric(rsi_col, errors='coerce')
    rsi_mask = pd.Series(True, index=filtered.index)  # type: ignore
    if min_rsi > 0:
        rsi_mask &= rsi_vals >= min_rsi  # type: ignore
    if max_rsi < 100:
        rsi_mask &= rsi_vals <= max_rsi  # type: ignore
    filtered = filtered[rsi_mask]

    if len(df_snapshot) == 0:
        st.warning("No stock data. Please refresh later.")
    elif len(filtered) == 0:
        st.warning("No stocks match criteria. Adjust filters.")
    else:
        st.write(f"Showing {len(filtered)} / {len(df_snapshot)} stocks")
        st.dataframe(filtered.set_index('Code'), width='stretch')  # type: ignore

        selected = st.selectbox("Select stock", filtered['Code'].tolist())
        if selected:
            st.session_state['selected_stock'] = selected
            st.rerun()

# ============================================================
# Tab 3: Stock Analysis
# ============================================================
with tab3:
    if 'selected_stock' not in st.session_state:
        st.session_state['selected_stock'] = STOCK_LIST[0]
    code = st.selectbox("Stock Code", STOCK_LIST, key='stock_sel')
    if code != st.session_state['selected_stock']:
        st.session_state['selected_stock'] = code

    if code not in stock_dict:
        st.error(f"Stock {code} data not available")
    else:
        stock = stock_dict[code]
        daily = stock['daily']
        score = stock['score']

        st.header(f"{code} - Analysis")
        last = daily.iloc[-1]
        score_val = score.iloc[-1] if len(score) > 0 and not pd.isna(score.iloc[-1]) else 0
        col1, col2, col3 = st.columns(3)
        with col1.container():
            st.markdown(get_card_style(), unsafe_allow_html=True)
            st.metric("Score", f"{score_val:.1f}")
        with col2.container():
            st.markdown(get_card_style(), unsafe_allow_html=True)
            st.metric("RSI", f"{last.get('rsi', 0):.1f}")
        with col3.container():
            st.markdown(get_card_style(), unsafe_allow_html=True)
            st.metric("Vol Ratio", f"{last.get('volume_ratio', 0):.2f}")

        # K-line chart
        st.subheader("K-Line & Tech Indicators")
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            vertical_spacing=0.02,
                            row_heights=[0.6, 0.2, 0.2])
        fig.add_trace(go.Candlestick(x=daily.index, open=daily['open'],
                                     high=daily['high'], low=daily['low'],
                                     close=daily['close'], name='K'), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily.index, y=daily['ma20'],
                                 line=dict(color='orange', width=1), name='MA20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily.index, y=daily['ma200'],
                                 line=dict(color='blue', width=1), name='MA200'), row=1, col=1)

        if 'bb_upper' in daily.columns:
            fig.add_trace(go.Scatter(x=daily.index, y=daily['bb_upper'],
                                     line=dict(color='gray', dash='dot'), name='BB Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=daily.index, y=daily['bb_lower'],
                                     line=dict(color='gray', dash='dot'), name='BB Lower'), row=1, col=1)

        colors = ['green' if daily['close'].iloc[i] >= daily['open'].iloc[i] else 'red'
                  for i in range(len(daily))]
        fig.add_trace(go.Bar(x=daily.index, y=daily['volume'],
                             marker_color=colors, name='Volume'), row=2, col=1)

        if 'macd' in daily.columns:
            fig.add_trace(go.Scatter(x=daily.index, y=daily['macd'],
                                     line=dict(color='blue', width=1), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=daily.index, y=daily['macd_signal'],
                                     line=dict(color='red', width=1), name='Signal'), row=3, col=1)
            colors_macd = ['green' if v > 0 else 'red' for v in daily['macd_hist']]
            fig.add_trace(go.Bar(x=daily.index, y=daily['macd_hist'],
                                 marker_color=colors_macd, name='MACD Hist'), row=3, col=1)

        fig.update_layout(height=800, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, width='stretch')

        # Backtest
        st.subheader("Backtest (Fixed 20-day)")
        trades = run_backtest(daily, score)
        summary = backtest_summary(trades)
        if summary['trades'] > 0:
            c1, c2, c3, c4 = st.columns(4)
            with c1.container():
                st.markdown(get_card_style(), unsafe_allow_html=True)
                st.metric("Trades", summary['trades'])
            with c2.container():
                st.markdown(get_card_style(), unsafe_allow_html=True)
                st.metric("Win Rate", f"{summary['win_rate']*100:.1f}%")
            with c3.container():
                st.markdown(get_card_style(), unsafe_allow_html=True)
                st.metric("Avg Return", f"{summary['avg_return']*100:.2f}%")
            with c4.container():
                st.markdown(get_card_style(), unsafe_allow_html=True)
                st.metric("Profit Factor", f"{summary['profit_factor']:.2f}")
            if trades:
                cum_returns = [1]
                for t in trades:
                    cum_returns.append(cum_returns[-1] * (1 + t['return']))
                cum_df = pd.DataFrame({'Trade': range(len(cum_returns)), 'Cumulative': cum_returns})
                st.line_chart(cum_df.set_index('Trade'))
        else:
            st.warning("No trades under current score threshold.")

        # OFF filter
        st.subheader("OFF Filter Status (Last 60 days)")
        off_res, reasons = compute_off_filter(daily, bench)
        recent_off = off_res.iloc[-60:]
        off_count = recent_off['is_off'].sum()
        st.write(f"OVER LAST 60 DAYS: {off_count} / 60 ({off_count/60*100:.1f}%)")
        if off_count > 0:
            st.write("OFF Reasons (recent):")
            reason_counts = {r: reasons[r][-60:].sum() for r in reasons if reasons[r][-60:].sum() > 0}
            st.bar_chart(pd.DataFrame({
                'Reason': list(reason_counts.keys()),
                'Count': list(reason_counts.values())
            }).set_index('Reason'))

# ============================================================
# Tab 4: 🦞 龙虾扫描（整合自 quant_lobster）
# ============================================================
with tab4:
    st.header("🦞 龙虾量化信号扫描")
    st.caption("整合自 quant_lobster | 多市场扫描 + 信号评分 + 操作建议")

    # ---- 4a. OFF Filter 概览 ----
    st.subheader("OFF Filter 状态总览")
    with st.spinner("扫描 OFF 状态..."):
        off_df = get_off_status_table(list(stock_dict.keys()), stock_dict)
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

    # ---- 4b. 全市场扫描 ----
    st.subheader("全市场信号扫描")
    with st.spinner("计算信号评分..."):
        scan_results = []
        for code, d in stock_dict.items():
            daily = d['daily']
            if daily is None or len(daily) < 50:
                continue

            # OFF 检查
            trade_ok, off_reasons = should_trade(code, daily)
            if not trade_ok:
                continue  # OFF 状态下跳过

            # 计算龙虾信号
            vr = volume_ratio(daily)
            prob_up = SignalGenerator.calculate_probability_up(daily)
            score = SignalGenerator.calculate_score(daily, vr, SCORING_WEIGHTS)
            signal, desc = SignalGenerator.get_signal(daily, score, prob_up)

            # 基础信息
            latest_price = daily['close'].iloc[-1]

            # 支撑/阻力
            recent_high = daily['high'].rolling(20).max().iloc[-1]
            recent_low = daily['low'].rolling(20).min().iloc[-1]

            # 目标价 & 止损
            vol_20 = daily['close'].pct_change().rolling(20).std().iloc[-1]
            target_up = latest_price * (1 + vol_20 * 2)
            stop_loss = latest_price * (1 - vol_20 * 1.5)

            # 三线斜率
            daily_slope = daily['close'].iloc[-20:].values
            x = np.arange(20)
            slope_val = np.polyfit(x, daily_slope, 1)[0] / daily_slope[-1]

            # 市场类型
            market = "美股"
            if is_hk_stock(code):
                market = "港股"
            elif is_a_stock(code):
                market = "A股"

            scan_results.append({
                'Code': code,
                'Market': market,
                'Score': round(score, 0),
                'Signal': signal,
                'Price': round(latest_price, 2),
                'Slope%': round(slope_val * 100, 2),
                'ProbUp%': round(prob_up, 0),
                'Target': round(target_up, 2),
                'Target%': round((target_up / latest_price - 1) * 100, 1),
                'Stop': round(stop_loss, 2),
                'Stop%': round((1 - stop_loss / latest_price) * 100, 1),
                'Support': round(recent_low, 2),
                'Resist': round(recent_high, 2),
                'Reason': desc,
            })

    if scan_results:
        df_scan = pd.DataFrame(scan_results)
        df_scan = df_scan.sort_values('Score', ascending=False)
        st.write(f"共扫描 {len(df_scan)} 只可交易股票（OFF状态已过滤）")

        # 过滤控件
        col_sig1, col_sig2 = st.columns(2)
        signal_filter = col_sig1.multiselect(
            "信号类型",
            options=["强烈推荐", "推荐", "持有", "观望"],
            default=["强烈推荐", "推荐", "持有"]
        )
        min_scan_score = col_sig2.slider("最低评分", 0, 100, 0)

        filtered_scan = df_scan[
            (df_scan['Score'] >= min_scan_score) &
            (df_scan['Signal'].isin(signal_filter))
        ]
        st.write(f"符合条件: {len(filtered_scan)} / {len(df_scan)}")
        st.dataframe(filtered_scan.set_index('Code'), width='stretch')

        # ---- 4c. 单股深度分析 ----
        st.subheader("🦞 单股深度分析")
        target_code = st.selectbox("选择股票", df_scan['Code'].tolist(), key='lobster_code')
        row = df_scan[df_scan['Code'] == target_code].iloc[0]

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1.container():
            st.markdown(get_card_style(), unsafe_allow_html=True)
            st.metric("评分", f"{row['Score']:.0f}")
        with col_p2.container():
            st.markdown(get_card_style(), unsafe_allow_html=True)
            st.metric("信号", row['Signal'])
        with col_p3.container():
            st.markdown(get_card_style(), unsafe_allow_html=True)
            st.metric("上涨概率", f"{row['ProbUp%']:.0f}%")
        with col_p4.container():
            st.markdown(get_card_style(), unsafe_allow_html=True)
            st.metric("价格", f"${row['Price']:.2f}")

        st.markdown("**操作建议**")
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"- **入场价**: ${row['Price']:.2f}")
        c2.markdown(f"- **目标价**: ${row['Target']:.2f} ({row['Target%']:+.1f}%)")
        c3.markdown(f"- **止损价**: ${row['Stop']:.2f} (-{row['Stop%']:.1f}%)")

        c4, c5, c6 = st.columns(3)
        c4.markdown(f"- **支撑位**: ${row['Support']:.2f}")
        c5.markdown(f"- **阻力位**: ${row['Resist']:.2f}")
        c6.markdown(f"- **信号依据**: {row['Reason']}")

        # ---- 4d. K线 + 信号标注 ----
        st.subheader(f"{target_code} K线与信号")
        if target_code in stock_dict:
            d = stock_dict[target_code]
            daily = d['daily']

            # 标注信号点
            daily = daily.copy()
            daily['signal'] = ''
            daily['signal_color'] = 'gray'

            # 简单标注最近20日的数据
            score_list = []
            for i in range(len(daily)):
                if i < 20:
                    score_list.append(np.nan)
                else:
                    window_df = daily.iloc[i-20:i+1]
                    vr = volume_ratio(window_df)
                    s = SignalGenerator.calculate_score(window_df, vr, SCORING_WEIGHTS)
                    score_list.append(s)
            daily['lobster_score'] = score_list

            fig2 = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.7, 0.3]
            )
            fig2.add_trace(go.Candlestick(
                x=daily.index, open=daily['open'],
                high=daily['high'], low=daily['low'],
                close=daily['close'], name='K'
            ), row=1, col=1)
            fig2.add_trace(go.Scatter(
                x=daily.index, y=daily['ma20'],
                line=dict(color='orange', width=1), name='MA20'
            ), row=1, col=1)

            # 评分着色
            colors_score = ['green' if s >= 60 else 'orange' if s >= 40 else 'red'
                             for s in daily['lobster_score']]
            fig2.add_trace(go.Bar(
                x=daily.index, y=daily['lobster_score'],
                marker_color=colors_score, name='Score',
                yaxis='y2'
            ), row=2, col=1)

            fig2.update_layout(height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig2, width='stretch')
    else:
        st.warning("没有找到符合条件的股票（可能全部处于OFF状态）")

# ============================================================
# Tab 5: 📈 Quant Tool（整合自 quant_tool）
# ============================================================
with tab5:
    st.header("📈 Quant Tool - 单股深度分析")
    st.caption("整合自 quant_tool | 期权分析 + OFF Filter + 日内建议")
    render_quant_tool_page()
