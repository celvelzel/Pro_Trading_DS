"""
Lobster Quant - Backtest Page
Strategy backtesting interface.
"""

import streamlit as st
import pandas as pd

from ...core.data_engine import get_data_engine
from ...core.indicator_engine import get_indicator_engine
from ...analysis.signals import SignalGenerator
from ...analysis.backtest import BacktestEngine
from ...config.settings import get_settings
from ...utils.logging import get_logger

logger = get_logger()


def render_backtest():
    """Render the backtest page."""
    st.title("🧪 Strategy Backtest")
    
    settings = get_settings()
    engine = get_data_engine()
    
    # Parameters
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol = st.text_input("Symbol", value="SPY").upper().strip()
    with col2:
        holding_days = st.slider("Holding Days", 5, 60, settings.backtest_holding_days)
    with col3:
        min_score = st.slider("Min Score", 0, 100, settings.backtest_min_score)
    
    if st.button("Run Backtest", type="primary"):
        with st.spinner(f"Backtesting {symbol}..."):
            run_backtest(symbol, engine, holding_days, min_score)


def run_backtest(symbol: str, engine, holding_days: int, min_score: int) -> None:
    """Run backtest and display results.
    
    Args:
        symbol: Stock symbol
        engine: DataEngine instance
        holding_days: Holding period in days
        min_score: Minimum entry score
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
        
        # Generate score series
        signal_gen = SignalGenerator()
        score_series = pd.Series(
            [signal_gen.calculate_score(df.iloc[:i+1]) for i in range(len(df))],
            index=df.index
        )
        
        # Run backtest
        backtest_engine = BacktestEngine()
        
        # Temporarily override settings
        original_holding = backtest_engine.holding_days
        original_min = backtest_engine.min_score
        backtest_engine.holding_days = holding_days
        backtest_engine.min_score = min_score
        
        result = backtest_engine.run(df, score_series, symbol=symbol)
        
        # Restore settings
        backtest_engine.holding_days = original_holding
        backtest_engine.min_score = original_min
        
        # Display results
        display_backtest_results(result, backtest_engine)
        
    except Exception as e:
        logger.error(f"Backtest error for {symbol}: {e}")
        st.error(f"Error running backtest: {e}")


def display_backtest_results(result, engine) -> None:
    """Display backtest results.
    
    Args:
        result: BacktestResult
        engine: BacktestEngine
    """
    if result.total_trades == 0:
        st.warning("No trades generated. Try lowering the minimum score.")
        return
    
    summary = engine.get_trade_summary(result)
    
    # Key metrics
    st.subheader("Performance Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", summary['total_trades'])
    with col2:
        st.metric("Win Rate", summary['win_rate'])
    with col3:
        st.metric("Avg Return", summary['avg_return'])
    with col4:
        st.metric("Profit Factor", summary['profit_factor'])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Drawdown", summary['max_drawdown'])
    with col2:
        st.metric("Cumulative Return", summary['cumulative_return'])
    with col3:
        st.metric("Sharpe Ratio", summary['sharpe_ratio'])
    
    # Equity curve
    st.subheader("Equity Curve")
    if result.equity_curve:
        equity_df = pd.DataFrame({
            'Trade': range(len(result.equity_curve)),
            'Equity': result.equity_curve
        })
        st.line_chart(equity_df.set_index('Trade'))
    
    # Trade list
    st.subheader("Trade History")
    if result.trades:
        trades_df = pd.DataFrame([
            {
                'Buy Date': t.buy_date.strftime('%Y-%m-%d'),
                'Buy Price': f"${t.buy_price:.2f}",
                'Sell Date': t.sell_date.strftime('%Y-%m-%d') if t.sell_date else 'Open',
                'Sell Price': f"${t.sell_price:.2f}" if t.sell_price else 'Open',
                'Return': f"{t.return_pct*100:.2f}%" if t.return_pct else 'N/A',
                'Days': t.holding_days
            }
