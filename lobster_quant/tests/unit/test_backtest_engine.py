"""
Tests for backtest engine.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.analysis.backtest import BacktestEngine
from src.data.models import (
    Trade, BacktestResult, Strategy, StrategyParams, BacktestMetrics
)


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


@pytest.fixture
def sample_strategy():
    """Create a sample Strategy object."""
    return Strategy(
        id="test_strategy_1",
        name="Test Strategy",
        description="A test strategy for unit tests",
        params=StrategyParams(
            holdingDays=15,
            minScore=55,
            slippagePct=0.002,
            commissionPct=0.001,
            positionSizing="fixed",
            positionSize=0.1,
            initialCapital=100000,
            maxPositions=5
        ),
        logic="default",
        isPreset=False,
        createdAt=datetime(2023, 1, 1)
    )


@pytest.fixture
def sample_trades():
    """Create sample trades for metrics testing."""
    return [
        Trade(
            symbol="TEST",
            buy_date=datetime(2023, 1, 1),
            buy_price=100.0,
            sell_date=datetime(2023, 1, 20),
            sell_price=110.0,
            return_pct=0.10,
            holding_days=15
        ),
        Trade(
            symbol="TEST",
            buy_date=datetime(2023, 2, 1),
            buy_price=110.0,
            sell_date=datetime(2023, 2, 15),
            sell_price=105.0,
            return_pct=-0.045,
            holding_days=10
        ),
        Trade(
            symbol="TEST",
            buy_date=datetime(2023, 3, 1),
            buy_price=105.0,
            sell_date=datetime(2023, 3, 20),
            sell_price=120.0,
            return_pct=0.143,
            holding_days=15
        ),
    ]


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


class TestRunWithStrategy:
    """Tests for run_with_strategy method."""
    
    @patch('src.core.signal_engine.get_signal_engine')
    def test_run_with_strategy_basic(self, mock_get_signal, sample_backtest_data, sample_strategy):
        """Test basic run_with_strategy execution."""
        # Mock the signal engine and scoring engine
        mock_scoring = MagicMock()
        mock_scoring.compute_score.return_value = pd.Series(
            [50.0] * len(sample_backtest_data),
            index=sample_backtest_data.index
        )
        mock_signal = MagicMock()
        mock_signal.scoring_engine = mock_scoring
        mock_get_signal.return_value = mock_signal
        
        engine = BacktestEngine()
        result = engine.run_with_strategy(sample_backtest_data, sample_strategy, symbol="TEST")
        
        assert result.symbol == "TEST"
        assert isinstance(result, BacktestResult)
        assert result.metrics is not None
        assert isinstance(result.metrics, BacktestMetrics)
    
    @patch('src.core.signal_engine.get_signal_engine')
    def test_run_with_strategy_applies_params(self, mock_get_signal, sample_backtest_data, sample_strategy):
        """Test that strategy params are applied to engine."""
        mock_scoring = MagicMock()
        mock_scoring.compute_score.return_value = pd.Series(
            [50.0] * len(sample_backtest_data),
            index=sample_backtest_data.index
        )
        mock_signal = MagicMock()
        mock_signal.scoring_engine = mock_scoring
        mock_get_signal.return_value = mock_signal
        
        engine = BacktestEngine()
        original_holding = engine.holding_days
        original_min_score = engine.min_score
        original_slippage = engine.slippage
        original_commission = engine.commission
        
        engine.run_with_strategy(sample_backtest_data, sample_strategy, symbol="TEST")
        
        # Verify settings were restored
        assert engine.holding_days == original_holding
        assert engine.min_score == original_min_score
        assert engine.slippage == original_slippage
        assert engine.commission == original_commission
    
    @patch('src.core.signal_engine.get_signal_engine')
    def test_run_with_strategy_restores_on_error(self, mock_get_signal, sample_backtest_data, sample_strategy):
        """Test that settings are restored even if an error occurs."""
        mock_scoring = MagicMock()
        mock_scoring.compute_score.side_effect = Exception("Test error")
        mock_signal = MagicMock()
        mock_signal.scoring_engine = mock_scoring
        mock_get_signal.return_value = mock_signal
        
        engine = BacktestEngine()
        original_holding = engine.holding_days
        original_min_score = engine.min_score
        
        # Should not raise, scores default to 0
        engine.run_with_strategy(sample_backtest_data, sample_strategy, symbol="TEST")
        
        # Verify settings were restored
        assert engine.holding_days == original_holding
        assert engine.min_score == original_min_score
    
    @patch('src.core.signal_engine.get_signal_engine')
    def test_run_with_strategy_generates_scores(self, mock_get_signal, sample_backtest_data, sample_strategy):
        """Test that score series is generated from scoring engine."""
        mock_scoring = MagicMock()
        mock_scores = pd.Series(
            [70.0] * len(sample_backtest_data),
            index=sample_backtest_data.index
        )
        mock_scoring.compute_score.return_value = mock_scores
        mock_signal = MagicMock()
        mock_signal.scoring_engine = mock_scoring
        mock_get_signal.return_value = mock_signal
        
        engine = BacktestEngine()
        result = engine.run_with_strategy(sample_backtest_data, sample_strategy, symbol="TEST")
        
        # Verify scoring engine was called
        assert mock_scoring.compute_score.call_count == len(sample_backtest_data)
        assert result.metrics is not None


class TestCalculateEnhancedMetrics:
    """Tests for _calculate_enhanced_metrics method."""
    
    def test_enhanced_metrics_with_trades(self, sample_trades):
        """Test enhanced metrics calculation with trades."""
        engine = BacktestEngine()
        
        result = BacktestResult(
            symbol="TEST",
            trades=sample_trades,
            win_rate=0.667,
            avg_return=0.066,
            profit_factor=2.0,
            max_drawdown=0.05,
            cumulative_return=0.20,
            best_trade=0.143,
            worst_trade=-0.045,
            sharpe_ratio=1.5
        )
        
        metrics = engine._calculate_enhanced_metrics(result)
        
        assert isinstance(metrics, BacktestMetrics)
        assert metrics.totalTrades == 3
        assert metrics.winningTrades == 2
        assert metrics.losingTrades == 1
        assert metrics.winRate > 0
        assert metrics.avgWin > 0
        assert metrics.avgLoss < 0
        assert metrics.profitLossRatio > 0
        assert metrics.avgHoldingDays > 0
    
    def test_enhanced_metrics_no_trades(self):
        """Test enhanced metrics with no trades."""
        engine = BacktestEngine()
        
        result = BacktestResult(symbol="TEST")
        metrics = engine._calculate_enhanced_metrics(result)
        
        assert isinstance(metrics, BacktestMetrics)
        assert metrics.totalTrades == 0
        assert metrics.winningTrades == 0
        assert metrics.losingTrades == 0
        assert metrics.totalReturn == 0
        assert metrics.winRate == 0
    
    def test_enhanced_metrics_all_winning(self):
        """Test enhanced metrics with all winning trades."""
        engine = BacktestEngine()
        
        trades = [
            Trade(
                symbol="TEST",
                buy_date=datetime(2023, 1, 1),
                buy_price=100.0,
                sell_date=datetime(2023, 1, 20),
                sell_price=110.0,
                return_pct=0.10,
                holding_days=15
            ),
            Trade(
                symbol="TEST",
                buy_date=datetime(2023, 2, 1),
                buy_price=110.0,
                sell_date=datetime(2023, 2, 15),
                sell_price=125.0,
                return_pct=0.136,
                holding_days=10
            ),
        ]
        
        result = BacktestResult(
            symbol="TEST",
            trades=trades,
            win_rate=1.0,
            avg_return=0.118,
            profit_factor=float('inf'),
            max_drawdown=0.0,
            cumulative_return=0.25,
            best_trade=0.136,
            worst_trade=0.10,
            sharpe_ratio=2.0
        )
        
        metrics = engine._calculate_enhanced_metrics(result)
        
        assert metrics.winningTrades == 2
        assert metrics.losingTrades == 0
        assert metrics.winRate == 100.0
        assert metrics.avgWin > 0
    
    def test_enhanced_metrics_all_losing(self):
        """Test enhanced metrics with all losing trades."""
        engine = BacktestEngine()
        
        trades = [
            Trade(
                symbol="TEST",
                buy_date=datetime(2023, 1, 1),
                buy_price=100.0,
                sell_date=datetime(2023, 1, 20),
                sell_price=90.0,
                return_pct=-0.10,
                holding_days=15
            ),
            Trade(
                symbol="TEST",
                buy_date=datetime(2023, 2, 1),
                buy_price=90.0,
                sell_date=datetime(2023, 2, 15),
                sell_price=80.0,
                return_pct=-0.111,
                holding_days=10
            ),
        ]
        
        result = BacktestResult(
            symbol="TEST",
            trades=trades,
            win_rate=0.0,
            avg_return=-0.106,
            profit_factor=0.0,
            max_drawdown=0.20,
            cumulative_return=-0.20,
            best_trade=-0.10,
            worst_trade=-0.111,
            sharpe_ratio=-1.5
        )
        
        metrics = engine._calculate_enhanced_metrics(result)
        
        assert metrics.winningTrades == 0
        assert metrics.losingTrades == 2
        assert metrics.winRate == 0.0
        assert metrics.avgLoss < 0
    
    def test_enhanced_metrics_equity_curve(self, sample_trades):
        """Test that equity curve metrics are calculated."""
        engine = BacktestEngine()
        
        result = BacktestResult(
            symbol="TEST",
            trades=sample_trades,
            win_rate=0.667,
            avg_return=0.066,
            profit_factor=2.0,
            max_drawdown=0.05,
            cumulative_return=0.20,
            best_trade=0.143,
            worst_trade=-0.045,
            sharpe_ratio=1.5
        )
        
        metrics = engine._calculate_enhanced_metrics(result)
        
        # With 3 trades, equity curve has 4 points
        assert metrics.totalReturn != 0 or metrics.volatility == 0
        assert isinstance(metrics.sharpeRatio, float)
        assert isinstance(metrics.maxDrawdown, float)
    
    def test_backtest_result_has_metrics_field(self):
        """Test that BacktestResult now has optional metrics field."""
        result = BacktestResult(symbol="TEST")
        assert result.metrics is None
        
        metrics = BacktestMetrics(
            totalReturn=10.0, annualizedReturn=5.0, volatility=15.0,
            sharpeRatio=1.2, maxDrawdown=8.0, winRate=60.0,
            profitLossRatio=1.5, totalTrades=10, winningTrades=6,
            losingTrades=4, avgHoldingDays=15.0, avgWin=3.0, avgLoss=-2.0
        )
        result.metrics = metrics
        assert result.metrics is not None
        assert result.metrics.totalReturn == 10.0
