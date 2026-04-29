"""
Tests for backtest engine.
"""

import pytest
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from analysis.backtest import BacktestEngine


@pytest.fixture
def sample_backtest_data():
    """Generate sample data for backtesting."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range('2023-01-01', periods=n)
    
    # Generate trending price
    trend = np.linspace(100, 150, n)
    noise = np.random.normal(0, 2, n)
    close = trend + noise
    
    df = pd.DataFrame({
        'open': close - np.abs(np.random.randn(n)),
        'high': close + np.abs(np.random.randn(n) * 2),
        'low': close - np.abs(np.random.randn(n) * 2),
        'close': close,
        'volume': np.random.randint(1000000, 10000000, n)
    }, index=dates)
    
    return df


@pytest.fixture
def sample_score_series(sample_backtest_data):
    """Generate sample score series."""
    # Generate scores that correlate with price
    scores = []
    for i in range(len(sample_backtest_data)):
        if i < 50:
            scores.append(30)  # Low scores initially
        elif i < 100:
            scores.append(60)  # Medium scores
        else:
            scores.append(80)  # High scores
    
    return pd.Series(scores, index=sample_backtest_data.index)


class TestBacktestEngine:
    def test_initialization(self):
        engine = BacktestEngine()
        assert engine is not None
        assert engine.holding_days > 0
        assert engine.min_score >= 0
    
    def test_run_backtest(self, sample_backtest_data, sample_score_series):
        engine = BacktestEngine()
        result = engine.run(sample_backtest_data, sample_score_series, symbol="TEST")
        
        assert result.symbol == "TEST"
        assert result.total_trades >= 0
        assert 0 <= result.win_rate <= 1
        assert isinstance(result.trades, list)
    
    def test_insufficient_data(self):
        engine = BacktestEngine()
        df = pd.DataFrame({
            'close': [100, 101, 102],
            'volume': [1000, 1000, 1000]
        })
        scores = pd.Series([50, 50, 50], index=df.index)
        
        result = engine.run(df, scores, symbol="TEST")
        assert result.total_trades == 0
    
    def test_trade_generation(self, sample_backtest_data, sample_score_series):
        engine = BacktestEngine()
        result = engine.run(sample_backtest_data, sample_score_series, symbol="TEST")
        
        if result.total_trades > 0:
            trade = result.trades[0]
            assert trade.symbol == "TEST"
            assert trade.buy_price > 0
            assert trade.is_closed
            assert trade.return_pct is not None
    
    def test_metrics_calculation(self, sample_backtest_data, sample_score_series):
        engine = BacktestEngine()
        result = engine.run(sample_backtest_data, sample_score_series, symbol="TEST")
        
        if result.total_trades > 0:
            assert result.profit_factor >= 0
            assert result.max_drawdown >= 0
            assert result.max_drawdown <= 1
            
            summary = engine.get_trade_summary(result)
            assert "total_trades" in summary
            assert "win_rate" in summary
            assert "avg_return" in summary
    
    def test_equity_curve(self, sample_backtest_data, sample_score_series):
        engine = BacktestEngine()
        result = engine.run(sample_backtest_data, sample_score_series, symbol="TEST")
        
        curve = result.equity_curve
        assert len(curve) == result.total_trades + 1
        assert curve[0] == 1.0
        assert all(c > 0 for c in curve)
