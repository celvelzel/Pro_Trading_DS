"""
Lobster Quant - Analyzer Page
Individual stock deep analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.core.data_engine import get_data_engine
from src.core.indicator_engine import get_indicator_engine
from src.core.risk_engine import RiskEngine
from src.analysis.signals import SignalGenerator
from src.analysis.backtest import BacktestEngine
from src.utils.logging import get_logger
from ..components.cards import signal_card, status_card

logger = get_logger()


def render_analyzer():
    """Render the stock analyzer page."""
    st.title("📈 Stock Analyzer")
    
    engine = get_data_engine()
    
    # Symbol input
    symbol = st.text_input("Enter Stock Symbol", value="AAPL").upper().strip()
    
    if not symbol:
        st.info("Enter a stock symbol to analyze")
        return
    
    if st.button("Analyze", type="primary"):
        with st.spinner(f"Analyzing {symbol}..."):
            analyze_stock(symbol, engine)


def analyze_stock(symbol: str, engine) -> None:
    """Analyze a single stock.
    
    Args:
        symbol: Stock symbol
        engine: DataEngine instance
    """
    try:
        # Fetch data
        stock_data = engine.fetch_stock(symbol)
        if stock_data is None:
            st.error(f"Failed to fetch data for {symbol}")
            return
        
        # Compute indicators
        indicator_engine = get_indicator_engine()
        df = indicator_engine.compute_all(stock_data.daily)
        
        # Generate signal
        signal_gen = SignalGenerator()
        signal = signal_gen.generate_signal(df)
        signal.symbol = symbol
        
        # Display signal
        st.subheader("Signal")
        signal_card(
            signal_type=signal.signal_type,
            score=signal.score,
            probability=signal.probability_up,
            reasons=signal.reasons
        )
        
        # Price chart
        st.subheader("Price Chart")
        fig = create_price_chart(df, symbol)
        st.plotly_chart(fig, use_container_width=True)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        latest = df.iloc[-1]
        
        with col1:
            st.metric("Price", f"${latest['close']:.2f}")
        with col2:
            rsi = latest.get('rsi')
            if rsi:
                st.metric("RSI", f"{rsi:.1f}")
        with col3:
            atr_pct = latest.get('atr_pct')
            if atr_pct:
                st.metric("ATR%", f"{atr_pct*100:.2f}%")
        with col4:
            vol_ratio = latest.get('volume_ratio')
            if vol_ratio:
                st.metric("Vol Ratio", f"{vol_ratio:.2f}x")
        
        # OFF Filter
        st.subheader("OFF Filter Status")
        risk_engine = RiskEngine()
        off_results = risk_engine.assess(df)
        latest_off = risk_engine.get_latest_status(df)
        
        status_card(
            title="Trading Status",
            status=latest_off.status_text,
            is_good=latest_off.is_on,
            details=f"Reasons: {', '.join(latest_off.reasons)}" if latest_off.reasons else None
        )
        
        # Backtest
        st.subheader("Backtest")
        backtest_engine = BacktestEngine()
        score_series = pd.Series(
            [signal_gen.calculate_score(df.iloc[:i+1]) for i in range(len(df))],
            index=df.index
        )
        
        result = backtest_engine.run(df, score_series, symbol=symbol)
        
        if result.total_trades > 0:
            summary = backtest_engine.get_trade_summary(result)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Trades", summary['total_trades'])
            with col2:
                st.metric("Win Rate", summary['win_rate'])
            with col3:
                st.metric("Avg Return", summary['avg_return'])
            
            # Equity curve
            if result.equity_curve:
                equity_df = pd.DataFrame({
                    'Trade': range(len(result.equity_curve)),
                    'Equity': result.equity_curve
                })
                st.line_chart(equity_df.set_index('Trade'))
        else:
            st.info("No trades generated with current parameters")
        
    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}")
        st.error(f"Error analyzing {symbol}: {e}")


def create_price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create interactive price chart.
    
    Args:
        df: DataFrame with OHLCV and indicators
        symbol: Stock symbol
    
    Returns:
        Plotly figure
    """
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f'{symbol} Price', 'Volume', 'RSI')
    )
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='OHLC'
    ), row=1, col=1)
    
    # MA lines
    if 'ma20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ma20'],
            name='MA20', line=dict(color='orange', width=1)
        ), row=1, col=1)
    
    if 'ma200' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ma200'],
            name='MA200', line=dict(color='red', width=1)
        ), row=1, col=1)
    
    # Volume
    colors = ['green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red' 
              for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['volume'],
        name='Volume',
        marker_color=colors
    ), row=2, col=1)
    
    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['rsi'],
            name='RSI', line=dict(color='purple', width=1)
        ), row=3, col=1)
        
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    fig.update_layout(
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False
    )
    
    return fig

