"""
Lobster Quant - Quant Tool Page
Options analysis: OFF assessment, Max Pain, support/resistance, option chain charts.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from .quant_tool_indicators import (
    calc_atr_percent,
    calc_ma200_dist,
    calc_gap_percent,
    calc_max_pain,
    find_support_resistance,
    calc_put_call_ratio,
)
from ..theme import theme_manager
from src.utils.logging import get_logger
from src.utils.i18n import t

logger = get_logger()


# ── Private data helpers (ported from quant_tool_data.py) ──────

def _fetch_daily_data(symbol: str, period: str = "1y") -> dict:
    """Fetch daily OHLCV data.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL").
        period: Time period to fetch.

    Returns:
        Dict with date/open/high/low/close/volume keys,
        or {"error": message} on failure.
    """
    import warnings
    import yfinance as yf

    if not symbol or not symbol.strip():
        return {"error": "Symbol cannot be empty"}

    symbol = symbol.strip().upper()

    try:
        ticker = yf.Ticker(symbol)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            hist = ticker.history(period=period, timeout=10)

        if hist.empty:
            return {"error": f"No data available for symbol {symbol}"}

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in required_cols:
            if col not in hist.columns:
                return {"error": f"Missing column {col} in data for {symbol}"}

        if bool(hist["Close"].isna().all()):
            return {"error": f"No valid price data for symbol {symbol}"}

        return {
            "date": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in hist.index],
            "open": hist["Open"].tolist(),
            "high": hist["High"].tolist(),
            "low": hist["Low"].tolist(),
            "close": hist["Close"].tolist(),
            "volume": hist["Volume"].astype(int).tolist(),
        }

    except Exception as e:
        return {"error": f"Failed to fetch data for {symbol}: {e}"}


def _fetch_option_chain(symbol: str) -> dict | None:
    """Fetch options chain for the nearest expiration date.

    Returns:
        Dict with expiration/calls/puts, None if no options,
        or {"error": message} on failure.
    """
    import warnings
    import yfinance as yf

    if not symbol or not symbol.strip():
        return {"error": "Symbol cannot be empty"}

    symbol = symbol.strip().upper()

    try:
        ticker = yf.Ticker(symbol)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            options_dates = ticker.options

        if not options_dates:
            return None

        nearest = options_dates[0]
        chain = ticker.option_chain(nearest)

        calls_list = _clean_records(chain.calls.to_dict("records"))
        puts_list = _clean_records(chain.puts.to_dict("records"))

        return {
            "expiration": nearest,
            "calls": calls_list,
            "puts": puts_list,
        }

    except Exception as e:
        return {"error": f"Failed to fetch options for {symbol}: {e}"}


def _clean_records(records: list[dict]) -> list[dict]:
    """Clean records for JSON-safe serialization."""
    import numpy as np
    result = []
    for r in records:
        cleaned = {}
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            elif not isinstance(v, (int, float, str, bool)) and v is not None:
                try:
                    if np.isnan(v):
                        v = None
                except TypeError:
                    pass
            cleaned[k] = v
        result.append(cleaned)
    return result


# ── Page renderer ──────────────────────────────────────────────

def render_quant_tool() -> None:
    """Render the quant tool page with OFF assessment and options analysis."""
    try:
        # Custom CSS styling
        st.markdown(theme_manager.get_css(), unsafe_allow_html=True)

        st.markdown("---")

        # Top search bar / symbol input
        col1, col2 = st.columns([3, 1])

        with col1:
            symbol = st.text_input(
                t("analyzer.enter_symbol"),
                placeholder=t("quant.input_placeholder"),
                key="quant_tool_symbol",
            )

        with col2:
            fetch_button = st.button(
                t("quant.fetch_data"), type="primary", key="quant_tool_fetch"
            )

        # Main content area
        if symbol and fetch_button:
            symbol = symbol.strip().upper()

            with st.spinner(t("quant.fetching", symbol=symbol)):
                daily_data = _fetch_daily_data(symbol)

            if isinstance(daily_data, dict) and "error" in daily_data:
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
                "Open": "open", "High": "high", "Low": "low", "Close": "close",
            }))
            ma200_dist_series = calc_ma200_dist(df.rename(columns={"Close": "close"}))
            gap_pct_series = calc_gap_percent(df.rename(columns={
                "Open": "open", "Close": "close",
            }))

            atr_percent = (
                atr_pct_series.iloc[-1] if not atr_pct_series.empty else None
            )
            ma200_dist = (
                ma200_dist_series.iloc[-1] if not ma200_dist_series.empty else None
            )
            gap_percent = (
                gap_pct_series.iloc[-1] if not gap_pct_series.empty else None
            )

            market_status = (
                "Bull" if df["Close"].iloc[-1] >= df["Open"].iloc[-1] else "Bear"
            )

            # == OFF Filter Analysis Card ==============================
            with st.spinner(t("quant.calculating_off")):
                st.markdown(f"### {t('quant.off_assessment')}")

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
                    st.markdown(f"**{t('quant.on_probability')}**")
                    st.progress(on_probability)
                    st.markdown(
                        f'<p class="green-text">{on_probability:.0%}</p>',
                        unsafe_allow_html=True,
                    )

                with col_off:
                    st.markdown(f"**{t('quant.off_probability')}**")
                    st.progress(off_probability)
                    st.markdown(
                        f'<p class="orange-text">{off_probability:.0%}</p>',
                        unsafe_allow_html=True,
                    )

                st.markdown("---")

                st.markdown(f"#### {t('quant.reason_analysis')}")

                reason_col1, reason_col2, reason_col3 = st.columns(3)

                with reason_col1:
                    st.metric(
                        t("quant.atr_pct"),
                        f"{atr_percent:.2f}%" if atr_percent is not None else "N/A",
                        delta=(
                            t("quant.above_threshold")
                            if atr_percent and atr_percent > 3
                            else t("quant.normal")
                        ),
                        delta_color=(
                            "inverse" if atr_percent and atr_percent > 3 else "normal"
                        ),
                    )

                with reason_col2:
                    st.metric(
                        t("quant.ma200_dist"),
                        f"{ma200_dist:.2f}%" if ma200_dist is not None else "N/A",
                        delta=(
                            t("quant.below_ma200")
                            if ma200_dist and ma200_dist < 0
                            else t("quant.above_ma200")
                        ),
                        delta_color=(
                            "inverse" if ma200_dist and ma200_dist < 0 else "normal"
                        ),
                    )

                with reason_col3:
                    st.metric(
                        t("quant.spy_env"),
                        market_status,
                        delta=t("quant.bullish") if market_status == "Bull" else t("quant.bearish"),
                        delta_color="normal" if market_status == "Bull" else "inverse",
                    )

            # == Options Analysis =====================================
            with st.spinner(t("quant.loading_options")):
                options_data = _fetch_option_chain(symbol)

            if options_data is None:
                st.warning(t("quant.no_options"))
                st.info(t("quant.no_options_info"))
            elif isinstance(options_data, dict) and "error" in options_data:
                st.warning(t("quant.options_fetch_error", error=options_data['error']))
                st.info(t("quant.options_load_failed"))
            else:
                st.markdown(f"### {t('quant.options_analysis')}")

                calls = options_data.get("calls", [])
                puts = options_data.get("puts", [])

                if not calls or not puts:
                    st.warning(t("quant.no_options"))
                else:
                    max_pain = calc_max_pain(calls, puts, current_price)
                    sr_levels = find_support_resistance(calls, puts)
                    pcr = calc_put_call_ratio(calls, puts)

                    support = sr_levels[0] if sr_levels else None
                    resistance = sr_levels[1] if sr_levels else None

                    metric_col1, metric_col2, metric_col3 = st.columns(3)

                    with metric_col1:
                        st.metric(
                            label=t("quant.max_pain"),
                            value=f"${max_pain:.2f}" if max_pain else "N/A",
                            delta=t("quant.pain_concentration"),
                            delta_color="off",
                        )

                    with metric_col2:
                        st.metric(
                            label=t("quant.support"),
                            value=f"${support:.2f}" if support else "N/A",
                            delta=t("quant.put_support"),
                            delta_color="normal",
                        )

                    with metric_col3:
                        st.metric(
                            label=t("quant.resistance"),
                            value=(
                                f"${resistance:.2f}" if resistance else "N/A"
                            ),
                            delta=t("quant.call_resistance"),
                            delta_color="inverse",
                        )

                    if pcr is not None:
                        st.markdown(f"**{t('quant.put_call_ratio')}:** {pcr:.2f}")

                    st.markdown("---")

                    # Option Chain Volume/OI Bar Chart
                    with st.spinner(t("quant.generating_charts")):
                        st.markdown(f"#### {t('quant.option_chain_charts')}")

                        call_strikes = [
                            c.get("strike") for c in calls if "strike" in c
                        ]
                        put_strikes = [
                            p.get("strike") for p in puts if "strike" in p
                        ]

                        all_strikes = sorted(set(call_strikes) & set(put_strikes))

                        call_vol = {
                            c.get("strike"): c.get("volume", 0) for c in calls
                        }
                        put_vol = {
                            p.get("strike"): p.get("volume", 0) for p in puts
                        }
                        call_oi = {
                            c.get("strike"): c.get("openInterest", 0) for c in calls
                        }
                        put_oi = {
                            p.get("strike"): p.get("openInterest", 0) for p in puts
                        }

                        strikes_filtered = [s for s in all_strikes if s is not None]
                        if strikes_filtered:
                            if current_price:
                                strikes_filtered = [
                                    s
                                    for s in strikes_filtered
                                    if current_price * 0.7 <= s <= current_price * 1.3
                                ]

                            if len(strikes_filtered) > 15:
                                strikes_filtered = strikes_filtered[:15]

                            call_vol_f = [
                                call_vol.get(s, 0) for s in strikes_filtered
                            ]
                            put_vol_f = [
                                put_vol.get(s, 0) for s in strikes_filtered
                            ]
                            call_oi_f = [
                                call_oi.get(s, 0) for s in strikes_filtered
                            ]
                            put_oi_f = [
                                put_oi.get(s, 0) for s in strikes_filtered
                            ]

                            theme = st.session_state.get("theme", "light")
                            plotly_template = (
                                "plotly_dark" if theme == "dark" else "plotly_white"
                            )
                            font_color = (
                                "#ffffff" if theme == "dark" else "#31333f"
                            )
                            chart_colors = theme_manager.get_chart_colors()

                            # Volume Chart
                            fig_volume = go.Figure()

                            fig_volume.add_trace(go.Bar(
                                x=strikes_filtered,
                                y=call_vol_f,
                                name=t("quant.call_volume"),
                                marker_color=chart_colors["call_vol"],
                                offsetgroup=0,
                            ))

                            fig_volume.add_trace(go.Bar(
                                x=strikes_filtered,
                                y=put_vol_f,
                                name=t("quant.put_volume"),
                                marker_color=chart_colors["put_vol"],
                                offsetgroup=1,
                            ))

                            fig_volume.update_layout(
                                title=t("quant.volume_by_strike"),
                                xaxis_title=t("quant.strike_price"),
                                yaxis_title=t("quant.volume"),
                                barmode="group",
                                template=plotly_template,
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(color=font_color),
                                height=400,
                                xaxis=dict(
                                    tickmode="linear",
                                    tick0=(
                                        strikes_filtered[0]
                                        if strikes_filtered
                                        else 0
                                    ),
                                    dtick=5,
                                ),
                            )

                            st.plotly_chart(fig_volume, use_container_width=True)

                            # Open Interest Chart
                            fig_oi = go.Figure()

                            fig_oi.add_trace(go.Bar(
                                x=strikes_filtered,
                                y=call_oi_f,
                                name=t("quant.call_oi"),
                                marker_color=chart_colors["call_oi"],
                                offsetgroup=0,
                            ))

                            fig_oi.add_trace(go.Bar(
                                x=strikes_filtered,
                                y=put_oi_f,
                                name=t("quant.put_oi"),
                                marker_color=chart_colors["put_oi"],
                                offsetgroup=1,
                            ))

                            fig_oi.update_layout(
                                title=t("quant.oi_by_strike"),
                                xaxis_title=t("quant.strike_price"),
                                yaxis_title=t("quant.open_interest"),
                                barmode="group",
                                template=plotly_template,
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(color=font_color),
                                height=400,
                                xaxis=dict(
                                    tickmode="linear",
                                    tick0=(
                                        strikes_filtered[0]
                                        if strikes_filtered
                                        else 0
                                    ),
                                    dtick=5,
                                ),
                            )

                            st.plotly_chart(fig_oi, use_container_width=True)
        else:
            st.markdown(f"""
            ### {t('quant.welcome_title')}

            {t('quant.welcome_description')}
            - {t('quant.welcome_off')}
            - {t('quant.welcome_options')}
            - {t('quant.welcome_charts')}

            {t('quant.supported_symbols')}
            """)

        st.markdown("---")
        st.caption(t("quant.powered_by"))

    except Exception as e:
        st.error(t("quant.render_error", error=e))
        st.info(t("quant.refresh_hint"))