"""
Lobster Quant - Scanner Page
Multi-market stock scanner with scoring.
"""

import streamlit as st
import pandas as pd
import asyncio

from ...core.data_engine import get_data_engine
from ...core.indicator_engine import get_indicator_engine
from ...analysis.signals import SignalGenerator
from ...config.settings import get_settings
from ...utils.logging import get_logger
from ..components.cards import signal_card

logger = get_logger()

# Stock lists (migrated from config)
US_STOCK_LIST = [
    'AIPO', 'AMZN', 'COHR', 'GLW', 'GOOG', 'ICLN', 'LITE', 'MU',
    'QQQ', 'SPY', 'TSLA', 'URA', 'VTI', 'XLE', 'XLU'
]

HK_STOCK_LIST = [
    '0005.HK', '0700.HK', '1299.HK', '2318.HK', '3690.HK',
    '9988.HK', '1810.HK', '2269.HK', '2020.HK', '9618.HK'
]

A_STOCK_LIST = [
    '600519', '000001', '300308', '002594', '600036',
    '000333', '300750', '601318', '600276', '002415'
]


def render_scanner():
    """Render the stock scanner page."""
    st.title("🔍 Stock Scanner")
    
    settings = get_settings()
    engine = get_data_engine()
    
    # Market selection
    col1, col2 = st.columns([3, 1])
    with col1:
        available_markets = []
        if settings.enable_us_stock:
            available_markets.append("US Stocks")
        if settings.enable_hk_stock:
            available_markets.append("HK Stocks")
        if settings.enable_a_stock:
            available_markets.append("A-Shares")
        
        selected_market = st.selectbox(
            "Select Market",
            options=available_markets,
            index=0
        )
    
    with col2:
        min_score = st.slider("Min Score", 0, 100, settings.backtest_min_score)
    
    # Get stock list
    if selected_market == "US Stocks":
        stock_list = US_STOCK_LIST
    elif selected_market == "HK Stocks":
        stock_list = HK_STOCK_LIST
    else:
        stock_list = A_STOCK_LIST
    
    # Scan button
    if st.button("🚀 Scan", type="primary"):
        with st.spinner(f"Scanning {len(stock_list)} stocks..."):
            results = scan_stocks(stock_list, engine, min_score)
        
        if results:
            display_results(results)
        else:
            st.info("No stocks meet the criteria")


def scan_stocks(symbols: list, engine, min_score: int) -> list:
    """Scan stocks and return results.
    
    Args:
        symbols: List of stock symbols
        engine: DataEngine instance
        min_score: Minimum score threshold
    
    Returns:
        List of result dictionaries
    """
    results = []
    indicator_engine = get_indicator_engine()
    signal_gen = SignalGenerator()
    
    # Fetch all stocks
    stock_data_dict = asyncio.run(engine.fetch_batch(symbols))
    
    for symbol, stock_data in stock_data_dict.items():
        if stock_data is None:
            continue
        
        try:
            # Compute indicators
            df = indicator_engine.compute_all(stock_data.daily)
            
            # Generate signal
            signal = signal_gen.generate_signal(df)
            signal.symbol = symbol
            
            if signal.score >= min_score:
                latest = df.iloc[-1]
                results.append({
                    'symbol': symbol,
                    'score': signal.score,
                    'signal': signal.signal_type,
                    'probability': signal.probability_up,
                    'price': stock_data.get_latest_price(),
                    'rsi': latest.get('rsi'),
                    'slope_daily': latest.get('slope_daily'),
                    'volume_ratio': latest.get('volume_ratio'),
                    'reasons': signal.reasons
                })
        
        except Exception as e:
            logger.warning(f"Error scanning {symbol}: {e}")
            continue
    
    # Sort by score descending
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def display_results(results: list) -> None:
    """Display scan results.
    
    Args:
        results: List of result dictionaries
    """
    st.success(f"Found {len(results)} stocks")
    
    # Create summary table
    df_display = pd.DataFrame([
        {
            'Symbol': r['symbol'],
            'Score': f"{r['score']:.0f}",
            'Signal': r['signal'],
            'Prob ↑': f"{r['probability']:.0f}%",
            'Price': f"${r['price']:.2f}" if r['price'] else 'N/A',
            'RSI': f"{r['rsi']:.1f}" if r['rsi'] else 'N/A'
        }
        for r in results
    ])
    
    st.dataframe(df_display, use_container_width=True)
    
    # Detailed cards for top 5
    st.subheader("Top Picks")
    for result in results[:5]:
        signal_card(
            signal_type=result['signal'],
            score=result['score'],
            probability=result['probability'],
            reasons=result['reasons']
        )
