"""
Quant Tool 页面模块
整合自 quant_tool/app.py，作为 lobster_quant 的独立页面
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from legacy.quant_tool_data import fetch_daily_data, fetch_option_chain
from legacy.quant_tool_indicators import (
    calc_atr_percent,
    calc_ma200_dist,
    calc_gap_percent,
    calc_max_pain,
    find_support_resistance,
    calc_put_call_ratio,
)
from legacy.theme_manager import get_quant_tool_css, get_chart_colors


def render_quant_tool_page():
    """渲染量化工具页面"""
    try:
        # Custom CSS styling
        st.markdown(get_quant_tool_css(), unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Top search bar / symbol input
        col1, col2 = st.columns([3, 1])
        
        with col1:
            symbol = st.text_input(
                "输入股票代码",
                placeholder="例如：AAPL, MSFT, TSLA",
                key="quant_tool_symbol"
            )
        
        with col2:
            fetch_button = st.button("获取数据", type="primary", key="quant_tool_fetch")
        
        # Main content area
        if symbol and fetch_button:
            symbol = symbol.strip().upper()
            
            with st.spinner(f"正在获取 {symbol} 数据..."):
                daily_data = fetch_daily_data(symbol)
            
            if "error" in daily_data:
                st.error(daily_data["error"])
                return
            
            df = pd.DataFrame({
                "Date": pd.to_datetime(daily_data["date"]),
                "Open": daily_data["open"],
                "High": daily_data["high"],
                "Low": daily_data["low"],
                "Close": daily_data["close"],
                "Volume": daily_data["volume"],
            })
            df.set_index("Date", inplace=True)
            
            current_price = df["Close"].iloc[-1]
            
            atr_pct_series = calc_atr_percent(df.rename(columns={
                "Open": "open", "High": "high", "Low": "low", "Close": "close"
            }))
            ma200_dist_series = calc_ma200_dist(df.rename(columns={"Close": "close"}))
            gap_pct_series = calc_gap_percent(df.rename(columns={"Open": "open", "Close": "close"}))
            
            atr_percent = atr_pct_series.iloc[-1] if not atr_pct_series.empty else None
            ma200_dist = ma200_dist_series.iloc[-1] if not ma200_dist_series.empty else None
            gap_percent = gap_pct_series.iloc[-1] if not gap_pct_series.empty else None
            
            market_status = "Bull" if df["Close"].iloc[-1] >= df["Open"].iloc[-1] else "Bear"
            
            # ============================================================
            # OFF Filter 分析 Card
            # ============================================================
            with st.spinner("计算 OFF 评估..."):
                st.markdown("### 🎯 OFF 评估")
                
                off_probability = 0.10
                
                if atr_percent is not None and atr_percent > 3:
                    off_probability += 0.20
                
                if ma200_dist is not None and ma200_dist < 0:
                    off_probability += 0.30
                
                if gap_percent is not None and gap_percent > 1:
                    off_probability += 0.10
                
                off_probability = min(off_probability, 0.95)
                on_probability = 1 - off_probability
                
                col_on, col_off = st.columns(2)
                
                with col_on:
                    st.markdown("**ON Probability**")
                    st.progress(on_probability)
                    st.markdown(f'<p class="green-text">{on_probability:.0%}</p>', 
                               unsafe_allow_html=True)
                
                with col_off:
                    st.markdown("**OFF Probability**")
                    st.progress(off_probability)
                    st.markdown(f'<p class="orange-text">{off_probability:.0%}</p>', 
                               unsafe_allow_html=True)
                
                st.markdown("---")
                
                st.markdown("#### 📋 原因分析")
                
                reason_col1, reason_col2, reason_col3 = st.columns(3)
                
                with reason_col1:
                    st.metric(
                        "ATR%",
                        f"{atr_percent:.2f}%" if atr_percent is not None else "N/A",
                        delta="Above threshold" if atr_percent and atr_percent > 3 else "Normal",
                        delta_color="inverse" if atr_percent and atr_percent > 3 else "normal"
                    )
                
                with reason_col2:
                    st.metric(
                        "MA200 Distance",
                        f"{ma200_dist:.2f}%" if ma200_dist is not None else "N/A",
                        delta="Below MA200" if ma200_dist and ma200_dist < 0 else "Above MA200",
                        delta_color="inverse" if ma200_dist and ma200_dist < 0 else "normal"
                    )
                
                with reason_col3:
                    st.metric(
                        "SPY Environment",
                        market_status,
                        delta="Bullish" if market_status == "Bull" else "Bearish",
                        delta_color="normal" if market_status == "Bull" else "inverse"
                    )
            
            # ============================================================
            # Fetch options data
            # ============================================================
            with st.spinner("加载期权数据..."):
                try:
                    options_data = fetch_option_chain(symbol)
                except Exception as e:
                    st.error(f"期权数据获取失败: {e}")
                    options_data = {"error": str(e)}
            
            if options_data is None:
                st.warning("该标的无可用期权数据")
                st.info("该股票没有可用的期权数据，跳过期权分析 dashboard")
            elif "error" in options_data:
                st.warning(f"期权数据获取失败: {options_data['error']}")
                st.info("无法加载期权数据，跳过期权分析 dashboard")
            else:
                st.markdown("### 📊 期权分析")
                
                calls = options_data.get("calls", [])
                puts = options_data.get("puts", [])
                expiration = options_data.get("expiration", "Unknown")
                
                if not calls or not puts:
                    st.warning("该标的无可用期权数据")
                else:
                    max_pain = calc_max_pain(calls, puts, current_price)
                    sr_levels = find_support_resistance(calls, puts)
                    put_call_ratio = calc_put_call_ratio(calls, puts)
                    
                    support = sr_levels[0] if sr_levels else None
                    resistance = sr_levels[1] if sr_levels else None
                    
                    metric_col1, metric_col2, metric_col3 = st.columns(3)
                    
                    with metric_col1:
                        st.metric(
                            label="Max Pain",
                            value=f"${max_pain:.2f}" if max_pain else "N/A",
                            delta="Pain concentration point",
                            delta_color="off"
                        )
                    
                    with metric_col2:
                        st.metric(
                            label="Support",
                            value=f"${support:.2f}" if support else "N/A",
                            delta="Put support level",
                            delta_color="normal"
                        )
                    
                    with metric_col3:
                        st.metric(
                            label="Resistance",
                            value=f"${resistance:.2f}" if resistance else "N/A",
                            delta="Call resistance level",
                            delta_color="inverse"
                        )
                    
                    if put_call_ratio is not None:
                        st.markdown(f"**Put/Call Ratio:** {put_call_ratio:.2f}")
                    
                    st.markdown("---")
                    
                    # Option Chain Volume/OI Bar Chart
                    with st.spinner("生成期权链图表..."):
                        st.markdown("#### 📈 期权链图表")
                        
                        call_strikes = [c.get("strike") for c in calls if "strike" in c]
                        put_strikes = [p.get("strike") for p in puts if "strike" in p]
                        
                        all_strikes = sorted(set(call_strikes) & set(put_strikes))
                        
                        call_vol_by_strike = {c.get("strike"): c.get("volume", 0) for c in calls}
                        put_vol_by_strike = {p.get("strike"): p.get("volume", 0) for p in puts}
                        call_oi_by_strike = {c.get("strike"): c.get("openInterest", 0) for c in calls}
                        put_oi_by_strike = {p.get("strike"): p.get("openInterest", 0) for p in puts}
                        
                        strikes_filtered = [s for s in all_strikes if s is not None]
                        if strikes_filtered:
                            if current_price:
                                strikes_filtered = [s for s in strikes_filtered 
                                             if current_price * 0.7 <= s <= current_price * 1.3]
                            
                            if len(strikes_filtered) > 15:
                                strikes_filtered = strikes_filtered[:15]
                            
                            call_vol_filtered = [call_vol_by_strike.get(s, 0) for s in strikes_filtered]
                            put_vol_filtered = [put_vol_by_strike.get(s, 0) for s in strikes_filtered]
                            call_oi_filtered = [call_oi_by_strike.get(s, 0) for s in strikes_filtered]
                            put_oi_filtered = [put_oi_by_strike.get(s, 0) for s in strikes_filtered]
                            
                            theme = st.session_state.get('theme', 'light')
                            plotly_template = "plotly_dark" if theme == 'dark' else "plotly_white"
                            font_color = '#ffffff' if theme == 'dark' else '#31333f'
                            chart_colors = get_chart_colors()
                            
                            # Volume Chart
                            fig_volume = go.Figure()
                            
                            fig_volume.add_trace(go.Bar(
                                x=strikes_filtered,
                                y=call_vol_filtered,
                                name='Call Volume',
                                marker_color=chart_colors['call_vol'],
                                offsetgroup=0
                            ))
                            
                            fig_volume.add_trace(go.Bar(
                                x=strikes_filtered,
                                y=put_vol_filtered,
                                name='Put Volume',
                                marker_color=chart_colors['put_vol'],
                                offsetgroup=1
                            ))
                            
                            fig_volume.update_layout(
                                title="Option Chain Volume by Strike",
                                xaxis_title="Strike Price",
                                yaxis_title="Volume",
                                barmode='group',
                                template=plotly_template,
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color=font_color),
                                height=400,
                                xaxis=dict(
                                    tickmode='linear',
                                    tick0=strikes_filtered[0] if strikes_filtered else 0,
                                    dtick=5
                                )
                            )
                            
                            st.plotly_chart(fig_volume, use_container_width=True)
                            
                            # Open Interest Chart
                            fig_oi = go.Figure()
                            
                            fig_oi.add_trace(go.Bar(
                                x=strikes_filtered,
                                y=call_oi_filtered,
                                name='Call OI',
                                marker_color=chart_colors['call_oi'],
                                offsetgroup=0
                            ))
                            
                            fig_oi.add_trace(go.Bar(
                                x=strikes_filtered,
                                y=put_oi_filtered,
                                name='Put OI',
                                marker_color=chart_colors['put_oi'],
                                offsetgroup=1
                            ))
                            
                            fig_oi.update_layout(
                                title="Open Interest by Strike",
                                xaxis_title="Strike Price",
                                yaxis_title="Open Interest",
                                barmode='group',
                                template=plotly_template,
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color=font_color),
                                height=400,
                                xaxis=dict(
                                    tickmode='linear',
                                    tick0=strikes_filtered[0] if strikes_filtered else 0,
                                    dtick=5
                                )
                            )
                            
                            st.plotly_chart(fig_oi, use_container_width=True)
        else:
            st.markdown("""
            ### 👋 输入股票代码开始分析
            
            上方输入股票代码并点击"获取数据"以查看：
            - 🎯 **OFF 评估** - 概率驱动的交易条件分析
            - 📊 **期权分析** - Max Pain、支撑位/阻力位
            - 📈 **期权链图表** - 成交量与未平仓量分析
            
            支持代码：AAPL, MSFT, TSLA, NVDA, MU
            """)
        
        st.markdown("---")
        st.caption("Powered by yfinance | Data refreshes every hour")
    
    except Exception as e:
        st.error(f"页面渲染失败: {e}")
        st.info("请刷新页面后重试")
