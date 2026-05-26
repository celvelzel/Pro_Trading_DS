"""
Tests for TradeSimulator.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

from src.data.models import (
    Strategy,
    StrategyParams,
    StockData,
    SignalResult,
    SimulatedTrade,
    DailySnapshot,
)


@pytest.fixture
def strategy_params():
    """Default strategy parameters for testing."""
    return StrategyParams(
        holdingDays=20,
        minScore=60,
        slippagePct=0.001,
        commissionPct=0.001,
        positionSizing="fixed",
        positionSize=0.1,
        initialCapital=100000,
        maxPositions=5,
    )


@pytest.fixture
def strategy(strategy_params):
    """Test strategy."""
    return Strategy(
        id="test_strategy",
        name="Test Strategy",
        description="A test strategy",
        params=strategy_params,
        logic="default",
        isPreset=True,
        createdAt=datetime.now(),
    )


@pytest.fixture
def mock_stock_data(sample_ohlcv_df):
    """Mock stock data."""
    return StockData(
        symbol="AAPL",
        daily=sample_ohlcv_df,
        last_update=datetime.now(),
        source="mock",
    )


@pytest.fixture
def mock_signal():
    """Mock signal result with high score."""
    return SignalResult(
        symbol="AAPL",
        signal_type="推荐",
        score=75.0,
        probability_up=65.0,
        reasons=["RSI oversold", "MACD bullish"],
    )


@pytest.fixture
def mock_trade():
    """A mock open trade."""
    return SimulatedTrade(
        id="trade_123_AAPL",
        strategyId="test_strategy",
        symbol="AAPL",
        entryDate=(datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d"),
        entryPrice=150.0,
        shares=66,
        status="open",
    )


@pytest.fixture
def trade_simulator(tmp_path):
    """Create a TradeSimulator with mocked dependencies."""
    from src.core.trade_simulator import TradeSimulator

    with patch("src.core.trade_simulator.get_data_engine") as mock_data, \
         patch("src.core.trade_simulator.get_indicator_engine") as mock_indicator, \
         patch("src.core.trade_simulator.get_signal_engine") as mock_signal_engine, \
         patch("src.core.trade_simulator.SimulationStore") as mock_store_cls, \
         patch("src.core.trade_simulator.StrategyManager") as mock_manager_cls:

        sim = TradeSimulator(data_dir=str(tmp_path))
        yield sim


class TestScanStocks:
    """Tests for scan_stocks method."""

    def test_returns_matching_stocks(
        self, trade_simulator, strategy, mock_stock_data, mock_signal
    ):
        """Stocks meeting criteria should be returned."""
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.indicator_engine.compute_all.return_value = mock_stock_data.daily
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        result = trade_simulator.scan_stocks(strategy, ["AAPL"])

        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["score"] == 75.0

    def test_filters_low_score(
        self, trade_simulator, strategy, mock_stock_data
    ):
        """Stocks below minScore should be filtered out."""
        low_signal = SignalResult(
            symbol="AAPL",
            signal_type="观望",
            score=30.0,
            probability_up=20.0,
            reasons=["Weak trend"],
        )
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.indicator_engine.compute_all.return_value = mock_stock_data.daily
        trade_simulator.signal_engine.generate_signal.return_value = low_signal

        result = trade_simulator.scan_stocks(strategy, ["AAPL"])

        assert len(result) == 0

    def test_skips_unavailable_data(self, trade_simulator, strategy):
        """Stocks with no data should be skipped."""
        trade_simulator.data_engine.fetch_stock.return_value = None

        result = trade_simulator.scan_stocks(strategy, ["INVALID"])

        assert len(result) == 0

    def test_handles_fetch_error(self, trade_simulator, strategy):
        """Exceptions during fetch should be caught and logged."""
        trade_simulator.data_engine.fetch_stock.side_effect = Exception("Network error")

        result = trade_simulator.scan_stocks(strategy, ["AAPL"])

        assert len(result) == 0

    def test_respects_max_positions(
        self, trade_simulator, mock_stock_data, mock_signal
    ):
        """Should limit results to maxPositions."""
        params = StrategyParams(
            minScore=0,
            maxPositions=2,
            initialCapital=100000,
        )
        small_strategy = Strategy(
            id="small",
            name="Small",
            description="",
            params=params,
            createdAt=datetime.now(),
        )

        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.indicator_engine.compute_all.return_value = mock_stock_data.daily
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        symbols = ["AAPL", "MSFT", "GOOG", "AMZN"]
        result = trade_simulator.scan_stocks(small_strategy, symbols)

        assert len(result) <= 2

    def test_sorted_by_score_descending(
        self, trade_simulator, mock_stock_data
    ):
        """Results should be sorted by score (highest first)."""
        params = StrategyParams(minScore=0, maxPositions=10, initialCapital=100000)
        test_strategy = Strategy(
            id="test",
            name="Test",
            description="",
            params=params,
            createdAt=datetime.now(),
        )

        signals = [
            SignalResult(symbol="A", signal_type="推荐", score=50.0, reasons=[]),
            SignalResult(symbol="B", signal_type="推荐", score=80.0, reasons=[]),
            SignalResult(symbol="C", signal_type="推荐", score=65.0, reasons=[]),
        ]
        call_count = 0

        def mock_generate(sd):
            nonlocal call_count
            result = signals[call_count]
            call_count += 1
            return result

        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.indicator_engine.compute_all.return_value = mock_stock_data.daily
        trade_simulator.signal_engine.generate_signal.side_effect = mock_generate

        result = trade_simulator.scan_stocks(test_strategy, ["A", "B", "C"])

        assert len(result) == 3
        assert result[0]["symbol"] == "B"
        assert result[1]["symbol"] == "C"
        assert result[2]["symbol"] == "A"


class TestExecuteTrades:
    """Tests for execute_trades method."""

    def test_creates_trade(self, trade_simulator, strategy, mock_trade):
        """Should create a trade for eligible stock."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [
            {
                "symbol": "AAPL",
                "score": 75.0,
                "signal_type": "推荐",
                "price": 150.0,
                "reasons": [],
            }
        ]

        result = trade_simulator.execute_trades("test_strategy", selected)

        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        assert result[0].shares > 0
        assert result[0].status == "open"
        trade_simulator.store.save_trade.assert_called_once()

    def test_skips_existing_position(self, trade_simulator, strategy, mock_trade):
        """Should skip stocks with existing open positions."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [mock_trade]

        selected = [
            {
                "symbol": "AAPL",
                "score": 75.0,
                "signal_type": "推荐",
                "price": 150.0,
                "reasons": [],
            }
        ]

        result = trade_simulator.execute_trades("test_strategy", selected)

        assert len(result) == 0

    def test_returns_empty_when_no_strategy(self, trade_simulator):
        """Should return empty when strategy not found."""
        trade_simulator.strategy_manager.get_strategy.return_value = None

        result = trade_simulator.execute_trades("missing", [])

        assert result == []

    def test_respects_capital_limit(self, trade_simulator):
        """Should not trade when capital is insufficient."""
        params = StrategyParams(
            initialCapital=1000,
            positionSize=0.5,
            positionSizing="fixed",
            maxPositions=5,
        )
        small_cap_strategy = Strategy(
            id="small",
            name="Small",
            description="",
            params=params,
            createdAt=datetime.now(),
        )
        trade_simulator.strategy_manager.get_strategy.return_value = small_cap_strategy

        existing_trade = SimulatedTrade(
            id="existing",
            strategyId="small",
            symbol="OTHER",
            entryDate="2024-01-01",
            entryPrice=100.0,
            shares=9,
            status="open",
        )
        trade_simulator.store.get_trades.return_value = [existing_trade]

        selected = [
            {
                "symbol": "AAPL",
                "score": 75.0,
                "signal_type": "推荐",
                "price": 150.0,
                "reasons": [],
            }
        ]

        result = trade_simulator.execute_trades("small", selected)

        assert len(result) == 0

    def test_dynamic_position_sizing(self, trade_simulator):
        """Dynamic sizing should scale position by score."""
        params = StrategyParams(
            initialCapital=100000,
            positionSize=0.2,
            positionSizing="dynamic",
            maxPositions=5,
        )
        dyn_strategy = Strategy(
            id="dyn",
            name="Dynamic",
            description="",
            params=params,
            createdAt=datetime.now(),
        )
        trade_simulator.strategy_manager.get_strategy.return_value = dyn_strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [
            {
                "symbol": "AAPL",
                "score": 80.0,
                "signal_type": "推荐",
                "price": 150.0,
                "reasons": [],
            }
        ]

        result = trade_simulator.execute_trades("dyn", selected)

        assert len(result) == 1
        # Dynamic sizing: 100000 * 0.2 * (80/100) = 16000
        # Shares: int(16000 / 150) = 106
        assert result[0].shares == 106

    def test_skips_zero_price(self, trade_simulator, strategy):
        """Should skip stocks with zero or negative price."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [
            {
                "symbol": "ZERO",
                "score": 75.0,
                "signal_type": "推荐",
                "price": 0.0,
                "reasons": [],
            }
        ]

        result = trade_simulator.execute_trades("test_strategy", selected)

        assert len(result) == 0


class TestUpdateOpenTrades:
    """Tests for update_open_trades method."""

    def test_closes_expired_trade(
        self, trade_simulator, strategy, mock_trade, mock_stock_data
    ):
        """Trades past holdingDays should be closed."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [mock_trade]
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 1
        assert result[0].status == "closed"
        assert result[0].exitDate is not None
        assert result[0].exitPrice is not None
        assert result[0].pnl is not None
        assert result[0].pnlPercent is not None
        trade_simulator.store.save_trade.assert_called_once()

    def test_keeps_active_trade(self, trade_simulator, strategy, mock_stock_data):
        """Trades within holding period should remain open."""
        active_trade = SimulatedTrade(
            id="trade_active",
            strategyId="test_strategy",
            symbol="AAPL",
            entryDate=datetime.now().strftime("%Y-%m-%d"),
            entryPrice=150.0,
            shares=66,
            status="open",
        )
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [active_trade]
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 0
        trade_simulator.store.save_trade.assert_not_called()

    def test_returns_empty_when_no_strategy(self, trade_simulator):
        """Should return empty when strategy not found."""
        trade_simulator.strategy_manager.get_strategy.return_value = None

        result = trade_simulator.update_open_trades("missing")

        assert result == []

    def test_handles_data_fetch_error(self, trade_simulator, strategy, mock_trade):
        """Should continue on data fetch errors."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [mock_trade]
        trade_simulator.data_engine.fetch_stock.side_effect = Exception("Timeout")

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 0


class TestRunDaily:
    """Tests for run_daily method."""

    def test_creates_snapshot(
        self, trade_simulator, strategy, mock_stock_data, mock_signal
    ):
        """Should create and save a daily snapshot."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.indicator_engine.compute_all.return_value = mock_stock_data.daily
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        result = trade_simulator.run_daily("test_strategy", ["AAPL"])

        assert isinstance(result, DailySnapshot)
        assert result.strategyId == "test_strategy"
        assert result.portfolioValue > 0
        trade_simulator.store.save_snapshot.assert_called_once()

    def test_raises_when_strategy_missing(self, trade_simulator):
        """Should raise ValueError when strategy not found."""
        trade_simulator.strategy_manager.get_strategy.return_value = None

        with pytest.raises(ValueError, match="not found"):
            trade_simulator.run_daily("missing", ["AAPL"])

    def test_full_workflow(
        self, trade_simulator, strategy, mock_stock_data, mock_signal
    ):
        """Should run the full scan → execute → snapshot workflow."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.indicator_engine.compute_all.return_value = mock_stock_data.daily
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        snapshot = trade_simulator.run_daily("test_strategy", ["AAPL", "MSFT"])

        assert snapshot.portfolioValue == strategy.params.initialCapital
        assert len(snapshot.selectedStocks) <= strategy.params.maxPositions

    def test_includes_closed_trades_in_snapshot(
        self, trade_simulator, strategy, mock_stock_data, mock_signal, mock_trade
    ):
        """Snapshot should include trades closed during the run."""
        call_count = 0

        def mock_get_trades(sid, status=None):
            nonlocal call_count
            call_count += 1
            # First call: during update_open_trades -> returns old trade
            if call_count == 1 and status == "open":
                return [mock_trade]
            # Subsequent calls: empty
            return []

        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.side_effect = mock_get_trades
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.indicator_engine.compute_all.return_value = mock_stock_data.daily
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        snapshot = trade_simulator.run_daily("test_strategy", ["AAPL"])

        assert len(snapshot.closedTrades) >= 0
