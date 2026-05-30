"""
Lobster Quant - Backtest Page
Strategy backtesting interface.
"""

import streamlit as st
import pandas as pd

from src.core.data_engine import get_data_engine
from src.core.indicator_engine import get_indicator_engine
from src.core.scoring_engine import get_scoring_engine
from src.analysis.backtest import BacktestEngine
from src.config.settings import get_settings
from src.utils.i18n import t
from src.utils.logging import get_logger

logger = get_logger()


def render_backtest():
    """Render the backtest page."""
    st.title(t("backtest.title"))
    
    settings = get_settings()
    engine = get_data_engine()
    
    # Parameters
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol = st.text_input(t("backtest.symbol"), value="SPY").upper().strip()
    with col2:
        holding_days = st.slider(t("backtest.holding_days"), 5, 60, settings.backtest_holding_days)
    with col3:
        min_score = st.slider(t("backtest.min_score"), 0, 100, settings.backtest_min_score)
    
    if st.button(t("backtest.run"), type="primary"):
        with st.spinner(t("backtest.running", symbol=symbol)):
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
            st.error(t("error.fetch_failed", symbol=symbol))
            return
        
        # Compute indicators
        indicator_engine = get_indicator_engine()
        df = indicator_engine.compute_all(stock_data.daily)
        
        # Generate score series (O(n) vectorized)
        scoring_engine = get_scoring_engine()
        score_series = scoring_engine.compute_score(df)
        
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
        st.error(t("backtest.error", error=e))


def display_backtest_results(result, engine) -> None:
    """Display backtest results.
    
    Args:
        result: BacktestResult
        engine: BacktestEngine
    """
    if result.total_trades == 0:
        st.warning(t("backtest.no_trades"))
        return
    
    summary = engine.get_trade_summary(result)
    
    # Key metrics
    st.subheader(t("backtest.performance"))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t("backtest.total_trades"), summary['total_trades'])
    with col2:
        st.metric(t("backtest.win_rate"), summary['win_rate'])
    with col3:
        st.metric(t("backtest.avg_return"), summary['avg_return'])
    with col4:
        st.metric(t("backtest.profit_factor"), summary['profit_factor'])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("backtest.max_drawdown"), summary['max_drawdown'])
    with col2:
        st.metric(t("backtest.cumulative_return"), summary['cumulative_return'])
    with col3:
        st.metric(t("backtest.sharpe_ratio"), summary['sharpe_ratio'])
    
    # Equity curve
    st.subheader(t("backtest.equity_curve"))
    if result.equity_curve:
        equity_df = pd.DataFrame({
            'Trade': range(len(result.equity_curve)),
            'Equity': result.equity_curve
        })
        st.line_chart(equity_df.set_index('Trade'))
    
    # Trade list
    st.subheader(t("backtest.trade_history"))
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
            for t in result.trades
        ])
        st.dataframe(trades_df, use_container_width=True)

