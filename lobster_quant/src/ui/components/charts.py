"""
Lobster Quant - Chart Components
Reusable Plotly chart components for the Streamlit app.
"""

from typing import Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ..theme import theme_manager


def candlestick_chart(df: pd.DataFrame, symbol: str = "", title: str = "") -> go.Figure:
    """Create candlestick chart with MA overlays, volume, and RSI subplots.

    Args:
        df: DataFrame with OHLCV data and optional MA/RSI columns
        symbol: Stock symbol for title
        title: Chart title (overrides symbol if provided)

    Returns:
        Plotly figure with candlestick, MA20, MA200, volume, and RSI
    """
    colors = theme_manager.get_chart_colors()

    chart_title = title if title else f"{symbol} Price"

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(chart_title, "Volume", "RSI")
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='OHLC',
        increasing_line_color=colors['up'],
        decreasing_line_color=colors['down']
    ), row=1, col=1)

    # MA20 overlay
    if 'ma20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['ma20'],
            name='MA20',
            line=dict(color='orange', width=1),
            hovertemplate='MA20: %{y:.2f}<extra></extra>'
        ), row=1, col=1)

    # MA200 overlay
    if 'ma200' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['ma200'],
            name='MA200',
            line=dict(color='red', width=1),
            hovertemplate='MA200: %{y:.2f}<extra></extra>'
        ), row=1, col=1)

    # Volume subplot with green/red coloring
    volume_colors = [colors['up'] if df['close'].iloc[i] >= df['open'].iloc[i] else colors['down']
                    for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['volume'],
        name='Volume',
        marker_color=volume_colors,
        hovertemplate='Volume: %{y:,.0f}<extra></extra>'
    ), row=2, col=1)

    # RSI subplot
    if 'rsi' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['rsi'],
            name='RSI',
            line=dict(color='purple', width=1),
            hovertemplate='RSI: %{y:.2f}<extra></extra>'
        ), row=3, col=1)

        # RSI overbought/oversold lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1, annotation_text="70")
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1, annotation_text="30")

    fig.update_layout(
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )

    return fig


def volume_chart(df: pd.DataFrame, symbol: str = "") -> go.Figure:
    """Create standalone volume bar chart with green/red coloring.

    Args:
        df: DataFrame with 'open', 'close', and 'volume' columns
        symbol: Stock symbol for title

    Returns:
        Plotly figure with volume bars
    """
    colors = theme_manager.get_chart_colors()

    title = f"{symbol} Volume" if symbol else "Volume"

    # Green if close >= open, red otherwise
    volume_colors = [colors['up'] if df['close'].iloc[i] >= df['open'].iloc[i] else colors['down']
                    for i in range(len(df))]

    fig = go.Figure(data=go.Bar(
        x=df.index,
        y=df['volume'],
        marker_color=volume_colors,
        name='Volume',
        hovertemplate='Date: %{x}<br>Volume: %{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        yaxis_title="Volume",
        hovermode="x unified"
    )

    return fig


def indicator_chart(df: pd.DataFrame, indicators: Optional[list[str]] = None, symbol: str = "") -> go.Figure:
    """Create multi-subplot chart for selected technical indicators.

    Args:
        df: DataFrame with indicator columns
        indicators: List of indicators to display (RSI, MACD, ATR, Bollinger)
        symbol: Stock symbol for title

    Returns:
        Plotly figure with selected indicators in separate subplots
    """
    if indicators is None:
        indicators = ['RSI']

    colors = theme_manager.get_chart_colors()

    # Determine number of subplots based on indicators
    num_subplots = len(indicators)
    if num_subplots == 0:
        return go.Figure()

    # Calculate row heights (equal distribution)
    row_heights = [1.0 / num_subplots] * num_subplots

    subplot_titles = []
    for ind in indicators:
        if ind.upper() == 'RSI':
            subplot_titles.append('RSI')
        elif ind.upper() == 'MACD':
            subplot_titles.append('MACD')
        elif ind.upper() == 'ATR':
            subplot_titles.append('ATR')
        elif ind.upper() == 'BOLLINGER':
            subplot_titles.append('Bollinger Bands')
        else:
            subplot_titles.append(ind)

    fig = make_subplots(
        rows=num_subplots,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1 / num_subplots,
        row_heights=row_heights,
        subplot_titles=subplot_titles
    )

    for idx, ind in enumerate(indicators, start=1):
        ind_upper = ind.upper()

        if ind_upper == 'RSI' and 'rsi' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['rsi'],
                name='RSI',
                line=dict(color='purple', width=1),
                hovertemplate='RSI: %{y:.2f}<extra></extra>'
            ), row=idx, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=idx, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=idx, col=1)
            fig.update_yaxes(range=[0, 100], row=idx, col=1)

        elif ind_upper == 'MACD':
            if 'macd' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['macd'],
                    name='MACD',
                    line=dict(color='blue', width=1),
                    hovertemplate='MACD: %{y:.4f}<extra></extra>'
                ), row=idx, col=1)
            if 'macd_signal' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['macd_signal'],
                    name='Signal',
                    line=dict(color='orange', width=1),
                    hovertemplate='Signal: %{y:.4f}<extra></extra>'
                ), row=idx, col=1)
            if 'macd_hist' in df.columns:
                colors_hist = [colors['up'] if val >= 0 else colors['down'] for val in df['macd_hist']]
                fig.add_trace(go.Bar(
                    x=df.index,
                    y=df['macd_hist'],
                    name='Histogram',
                    marker_color=colors_hist,
                    hovertemplate='Hist: %{y:.4f}<extra></extra>'
                ), row=idx, col=1)

        elif ind_upper == 'ATR' and 'atr' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['atr'],
                name='ATR',
                line=dict(color='teal', width=1),
                hovertemplate='ATR: %{y:.4f}<extra></extra>'
            ), row=idx, col=1)

        elif ind_upper == 'BOLLINGER':
            if 'bb_upper' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['bb_upper'],
                    name='BB Upper',
                    line=dict(color='red', width=1),
                    hovertemplate='Upper: %{y:.2f}<extra></extra>'
                ), row=idx, col=1)
            if 'bb_middle' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['bb_middle'],
                    name='BB Middle',
                    line=dict(color='blue', width=1),
                    hovertemplate='Middle: %{y:.2f}<extra></extra>'
                ), row=idx, col=1)
            if 'bb_lower' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['bb_lower'],
                    name='BB Lower',
                    line=dict(color='green', width=1),
                    hovertemplate='Lower: %{y:.2f}<extra></extra>'
                ), row=idx, col=1)

    title = f"{symbol} Indicators" if symbol else "Technical Indicators"

    fig.update_layout(
        title=title,
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )

    return fig


def equity_curve_chart(equity_curve: list[float], title: str = "Equity Curve") -> go.Figure:
    """Create equity curve line chart with hover data.

    Args:
        equity_curve: List of equity values over time
        title: Chart title

    Returns:
        Plotly figure with equity curve
    """
    colors = theme_manager.get_chart_colors()

    x_values = list(range(len(equity_curve)))

    fig = go.Figure(data=go.Scatter(
        x=x_values,
        y=equity_curve,
        mode='lines',
        name='Equity',
        line=dict(color=colors['up'], width=2),
        fill='tozeroy',
        fillcolor=f"rgba({int(colors['up'][1:3], 16)}, {int(colors['up'][3:5], 16)}, {int(colors['up'][5:7], 16)}, 0.1)",
        hovertemplate='Period: %{x}<br>Equity: $%{y:,.2f}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        xaxis_title="Period",
        yaxis_title="Equity Value ($)",
        hovermode="x unified"
    )

    return fig