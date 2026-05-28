"""
Comprehensive tests for TradeSimulator.

Covers ALL business logic paths:
- scan_stocks: filtering, sorting, limiting, error handling, None data
- execute_trades: trade creation, position sizing (fixed/dynamic), capital limits,
  duplicate positions, zero/negative price, zero shares
- update_open_trades: expiry-based closure, active trade retention, error handling
- run_daily: full workflow, snapshot creation, strategy missing
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.data.models import (
    DailySnapshot,
    SignalResult,
    SimulatedTrade,
    StockData,
    Strategy,
    StrategyParams,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    """A mock open trade that is PAST holding period (25 days old > 20 holdingDays)."""
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
def active_trade():
    """A mock open trade that is WITHIN holding period (5 days old < 20 holdingDays)."""
    return SimulatedTrade(
        id="trade_active_AAPL",
        strategyId="test_strategy",
        symbol="AAPL",
        entryDate=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        entryPrice=150.0,
        shares=66,
        status="open",
    )


@pytest.fixture
def trade_simulator(tmp_path):
    """Create a TradeSimulator with mocked dependencies."""
    from src.core.trade_simulator import TradeSimulator

    with (
        patch("src.core.trade_simulator.get_data_engine") as _mock_data,
        patch("src.core.trade_simulator.get_indicator_engine") as _mock_indicator,
        patch("src.core.trade_simulator.get_signal_engine") as _mock_signal_engine,
        patch("src.core.trade_simulator.SimulationStore") as _mock_store_cls,
        patch("src.core.trade_simulator.StrategyManager") as _mock_manager_cls,
    ):
        sim = TradeSimulator(data_dir=str(tmp_path))
        yield sim


def _make_stock_dict(symbol="AAPL", score=75.0, signal_type="推荐", price=150.0):
    """Helper to create a stock info dict as returned by scan_stocks."""
    return {
        "symbol": symbol,
        "score": score,
        "signal_type": signal_type,
        "price": price,
        "reasons": ["test reason"],
    }


# ===========================================================================
# TestScanStocks
# ===========================================================================


class TestScanStocks:
    """Tests for scan_stocks method."""

    def test_returns_matching_stocks(self, trade_simulator, strategy, mock_stock_data, mock_signal):
        """Stocks meeting criteria should be returned with correct fields."""
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        result = trade_simulator.scan_stocks(strategy, ["AAPL"])

        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["score"] == 75.0
        assert result[0]["signal_type"] == "推荐"
        assert result[0]["price"] == mock_stock_data.get_latest_price()
        assert result[0]["reasons"] == ["RSI oversold", "MACD bullish"]

    def test_filters_low_score(self, trade_simulator, strategy, mock_stock_data):
        """Stocks below minScore should be filtered out."""
        low_signal = SignalResult(
            symbol="AAPL",
            signal_type="观望",
            score=30.0,
            probability_up=20.0,
            reasons=["Weak trend"],
        )
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = low_signal

        result = trade_simulator.scan_stocks(strategy, ["AAPL"])

        assert len(result) == 0

    def test_includes_stocks_at_exact_min_score(self, trade_simulator, strategy, mock_stock_data):
        """Stocks exactly at minScore boundary should be included."""
        exact_signal = SignalResult(
            symbol="AAPL",
            signal_type="推荐",
            score=60.0,  # exactly minScore
            probability_up=50.0,
            reasons=["Borderline"],
        )
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = exact_signal

        result = trade_simulator.scan_stocks(strategy, ["AAPL"])

        assert len(result) == 1
        assert result[0]["score"] == 60.0

    def test_skips_none_stock_data(self, trade_simulator, strategy):
        """Stocks where fetch_stock returns None should be skipped."""
        trade_simulator.data_engine.fetch_stock.return_value = None

        result = trade_simulator.scan_stocks(strategy, ["INVALID"])

        assert len(result) == 0
        trade_simulator.signal_engine.generate_signal.assert_not_called()

    def test_handles_fetch_exception(self, trade_simulator, strategy):
        """Exceptions during fetch should be caught, logged, and the stock skipped."""
        trade_simulator.data_engine.fetch_stock.side_effect = Exception("Network error")

        result = trade_simulator.scan_stocks(strategy, ["AAPL"])

        assert len(result) == 0

    def test_handles_signal_generation_exception(self, trade_simulator, strategy, mock_stock_data):
        """Exceptions during signal generation should be caught and the stock skipped."""
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.side_effect = ValueError("Scoring failed")

        result = trade_simulator.scan_stocks(strategy, ["AAPL"])

        assert len(result) == 0

    def test_returns_empty_when_no_stocks_meet_criteria(self, trade_simulator, strategy):
        """Empty stock_list should return empty list."""
        result = trade_simulator.scan_stocks(strategy, [])

        assert result == []

    def test_returns_empty_when_all_below_min_score(self, trade_simulator, strategy, mock_stock_data):
        """All stocks below minScore → empty result."""
        low_signal = SignalResult(
            symbol="X", signal_type="观望", score=10.0, probability_up=10.0, reasons=[]
        )
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = low_signal

        result = trade_simulator.scan_stocks(strategy, ["A", "B", "C"])

        assert result == []

    def test_respects_max_positions(self, trade_simulator, mock_stock_data, mock_signal):
        """Should limit results to maxPositions."""
        params = StrategyParams(minScore=0, maxPositions=2, initialCapital=100000)
        small_strategy = Strategy(
            id="small", name="Small", description="", params=params, createdAt=datetime.now()
        )

        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        symbols = ["AAPL", "MSFT", "GOOG", "AMZN"]
        result = trade_simulator.scan_stocks(small_strategy, symbols)

        assert len(result) <= 2

    def test_sorted_by_score_descending(self, trade_simulator, mock_stock_data):
        """Results should be sorted by score (highest first)."""
        params = StrategyParams(minScore=0, maxPositions=10, initialCapital=100000)
        test_strategy = Strategy(
            id="test", name="Test", description="", params=params, createdAt=datetime.now()
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
        trade_simulator.signal_engine.generate_signal.side_effect = mock_generate

        result = trade_simulator.scan_stocks(test_strategy, ["A", "B", "C"])

        assert len(result) == 3
        assert result[0]["symbol"] == "B"
        assert result[0]["score"] == 80.0
        assert result[1]["symbol"] == "C"
        assert result[1]["score"] == 65.0
        assert result[2]["symbol"] == "A"
        assert result[2]["score"] == 50.0

    def test_max_positions_applied_after_sorting(self, trade_simulator, mock_stock_data):
        """maxPositions should keep the top-scoring stocks after sort."""
        params = StrategyParams(minScore=0, maxPositions=2, initialCapital=100000)
        test_strategy = Strategy(
            id="test", name="Test", description="", params=params, createdAt=datetime.now()
        )

        signals = [
            SignalResult(symbol="A", signal_type="推荐", score=50.0, reasons=[]),
            SignalResult(symbol="B", signal_type="推荐", score=90.0, reasons=[]),
            SignalResult(symbol="C", signal_type="推荐", score=70.0, reasons=[]),
        ]
        call_count = 0

        def mock_generate(sd):
            nonlocal call_count
            result = signals[call_count]
            call_count += 1
            return result

        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.side_effect = mock_generate

        result = trade_simulator.scan_stocks(test_strategy, ["A", "B", "C"])

        assert len(result) == 2
        # B (90) and C (70) should be kept; A (50) dropped
        assert result[0]["symbol"] == "B"
        assert result[1]["symbol"] == "C"

    def test_mixed_success_and_failure(self, trade_simulator, strategy, mock_stock_data, mock_signal):
        """Should handle mix of successful fetches, None returns, and exceptions."""
        call_count = 0

        def mock_fetch(symbol):
            nonlocal call_count
            call_count += 1
            if symbol == "GOOD":
                return mock_stock_data
            elif symbol == "NONE":
                return None
            else:  # "ERROR"
                raise Exception("Fetch failed")

        trade_simulator.data_engine.fetch_stock.side_effect = mock_fetch
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        result = trade_simulator.scan_stocks(strategy, ["GOOD", "NONE", "ERROR"])

        assert len(result) == 1
        assert result[0]["symbol"] == "GOOD"


# ===========================================================================
# TestExecuteTrades
# ===========================================================================


class TestExecuteTrades:
    """Tests for execute_trades method."""

    def test_creates_trade(self, trade_simulator, strategy, mock_trade):
        """Should create a trade for eligible stock."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [_make_stock_dict()]

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

        selected = [_make_stock_dict(symbol="AAPL")]

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
            id="small", name="Small", description="", params=params, createdAt=datetime.now()
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

        # position_size = 1000 * 0.5 = 500
        # available = 1000 - (100 * 9) = 100
        # 500 > 100 → skip
        selected = [_make_stock_dict(price=150.0)]

        result = trade_simulator.execute_trades("small", selected)

        assert len(result) == 0

    def test_fixed_position_sizing(self, trade_simulator):
        """Fixed sizing: position_value = initialCapital * positionSize."""
        params = StrategyParams(
            initialCapital=100000,
            positionSize=0.1,
            positionSizing="fixed",
            maxPositions=5,
        )
        fixed_strategy = Strategy(
            id="fixed", name="Fixed", description="", params=params, createdAt=datetime.now()
        )
        trade_simulator.strategy_manager.get_strategy.return_value = fixed_strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [_make_stock_dict(price=150.0)]

        result = trade_simulator.execute_trades("fixed", selected)

        assert len(result) == 1
        # position_value = 100000 * 0.1 = 10000
        # shares = int(10000 / 150) = 66
        assert result[0].shares == 66

    def test_dynamic_position_sizing(self, trade_simulator):
        """Dynamic sizing: position_value = initialCapital * positionSize * (score/100)."""
        params = StrategyParams(
            initialCapital=100000,
            positionSize=0.2,
            positionSizing="dynamic",
            maxPositions=5,
        )
        dyn_strategy = Strategy(
            id="dyn", name="Dynamic", description="", params=params, createdAt=datetime.now()
        )
        trade_simulator.strategy_manager.get_strategy.return_value = dyn_strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [_make_stock_dict(score=80.0, price=150.0)]

        result = trade_simulator.execute_trades("dyn", selected)

        assert len(result) == 1
        # position_value = 100000 * 0.2 * (80/100) = 16000
        # shares = int(16000 / 150) = 106
        assert result[0].shares == 106

    def test_dynamic_sizing_low_score(self, trade_simulator):
        """Dynamic sizing with low score produces smaller position."""
        params = StrategyParams(
            initialCapital=100000,
            positionSize=0.2,
            positionSizing="dynamic",
            maxPositions=5,
        )
        dyn_strategy = Strategy(
            id="dyn", name="Dynamic", description="", params=params, createdAt=datetime.now()
        )
        trade_simulator.strategy_manager.get_strategy.return_value = dyn_strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [_make_stock_dict(score=30.0, price=150.0)]

        result = trade_simulator.execute_trades("dyn", selected)

        assert len(result) == 1
        # position_value = 100000 * 0.2 * (30/100) = 6000
        # shares = int(6000 / 150) = 40
        assert result[0].shares == 40

    def test_skips_zero_price(self, trade_simulator, strategy):
        """Should skip stocks with zero price."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [_make_stock_dict(price=0.0)]

        result = trade_simulator.execute_trades("test_strategy", selected)

        assert len(result) == 0

    def test_skips_negative_price(self, trade_simulator, strategy):
        """Should skip stocks with negative price."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [_make_stock_dict(price=-5.0)]

        result = trade_simulator.execute_trades("test_strategy", selected)

        assert len(result) == 0

    def test_skips_zero_shares(self, trade_simulator):
        """Should skip when calculated shares <= 0 (price too high for position)."""
        params = StrategyParams(
            initialCapital=1000,
            positionSize=0.01,
            positionSizing="fixed",
            maxPositions=5,
        )
        tiny_strategy = Strategy(
            id="tiny", name="Tiny", description="", params=params, createdAt=datetime.now()
        )
        trade_simulator.strategy_manager.get_strategy.return_value = tiny_strategy
        trade_simulator.store.get_trades.return_value = []

        # position_value = 1000 * 0.01 = 10; price = 1000; shares = int(10/1000) = 0
        selected = [_make_stock_dict(price=1000.0)]

        result = trade_simulator.execute_trades("tiny", selected)

        assert len(result) == 0

    def test_creates_multiple_trades(self, trade_simulator, strategy):
        """Should create trades for multiple eligible stocks."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [
            _make_stock_dict(symbol="AAPL", price=150.0),
            _make_stock_dict(symbol="MSFT", price=300.0),
            _make_stock_dict(symbol="GOOG", price=140.0),
        ]

        result = trade_simulator.execute_trades("test_strategy", selected)

        assert len(result) == 3
        symbols = {t.symbol for t in result}
        assert symbols == {"AAPL", "MSFT", "GOOG"}

    def test_trade_has_correct_fields(self, trade_simulator, strategy):
        """Created trade should have all required fields populated."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        selected = [_make_stock_dict(price=200.0)]

        result = trade_simulator.execute_trades("test_strategy", selected)

        trade = result[0]
        assert trade.id is not None and len(trade.id) > 0
        assert trade.strategyId == "test_strategy"
        assert trade.symbol == "AAPL"
        assert trade.entryDate == datetime.now().strftime("%Y-%m-%d")
        assert trade.entryPrice == 200.0
        assert trade.shares > 0
        assert trade.status == "open"
        assert trade.exitDate is None
        assert trade.exitPrice is None
        assert trade.pnl is None
        assert trade.pnlPercent is None

    def test_capital_decreases_after_trade(self, trade_simulator):
        """Available capital should decrease after each trade, preventing over-allocation."""
        params = StrategyParams(
            initialCapital=10000,
            positionSize=0.5,
            positionSizing="fixed",
            maxPositions=5,
        )
        cap_strategy = Strategy(
            id="cap", name="Cap", description="", params=params, createdAt=datetime.now()
        )
        trade_simulator.strategy_manager.get_strategy.return_value = cap_strategy
        trade_simulator.store.get_trades.return_value = []

        # Each trade: position_value = 10000 * 0.5 = 5000
        # AAPL: shares = int(5000/150) = 33, cost = 150*33 = 4950, available = 10000-4950 = 5050
        # MSFT: shares = int(5000/300) = 16, cost = 300*16 = 4800, available = 5050-4800 = 250
        # GOOG: shares = int(5000/140) = 35, cost = 140*35 = 4900, 4900 > 250 → skip
        selected = [
            _make_stock_dict(symbol="AAPL", price=150.0),
            _make_stock_dict(symbol="MSFT", price=300.0),
            _make_stock_dict(symbol="GOOG", price=140.0),
        ]

        result = trade_simulator.execute_trades("cap", selected)

        assert len(result) == 2
        symbols = [t.symbol for t in result]
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "GOOG" not in symbols

    def test_empty_selected_stocks(self, trade_simulator, strategy):
        """Empty selected_stocks should return empty list."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        result = trade_simulator.execute_trades("test_strategy", [])

        assert result == []
        trade_simulator.store.save_trade.assert_not_called()

    def test_strategy_manager_get_strategy_called(self, trade_simulator):
        """Should call strategy_manager.get_strategy with correct ID."""
        trade_simulator.strategy_manager.get_strategy.return_value = None

        trade_simulator.execute_trades("my_strategy", [])

        trade_simulator.strategy_manager.get_strategy.assert_called_once_with("my_strategy")


# ===========================================================================
# TestUpdateOpenTrades
# ===========================================================================


class TestUpdateOpenTrades:
    """Tests for update_open_trades method."""

    def test_closes_expired_trade(self, trade_simulator, strategy, mock_trade, mock_stock_data):
        """Trades past holdingDays should be closed with correct fields."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [mock_trade]
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 1
        closed = result[0]
        assert closed.status == "closed"
        assert closed.exitDate == datetime.now().strftime("%Y-%m-%d")
        assert closed.exitPrice == mock_stock_data.get_latest_price()
        assert closed.pnl is not None
        assert closed.pnlPercent is not None
        trade_simulator.store.save_trade.assert_called_once()

    def test_pnl_calculation_correct(self, trade_simulator, strategy, mock_trade, mock_stock_data):
        """PnL should be (current_price - entry_price) * shares."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [mock_trade]
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data

        result = trade_simulator.update_open_trades("test_strategy")

        current_price = mock_stock_data.get_latest_price()
        expected_pnl = (current_price - mock_trade.entryPrice) * mock_trade.shares
        expected_pnl_pct = (current_price - mock_trade.entryPrice) / mock_trade.entryPrice * 100

        assert result[0].pnl == pytest.approx(expected_pnl, rel=1e-6)
        assert result[0].pnlPercent == pytest.approx(expected_pnl_pct, rel=1e-6)

    def test_keeps_active_trade(self, trade_simulator, strategy, active_trade, mock_stock_data):
        """Trades within holding period should remain open (not closed)."""
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

    def test_returns_empty_when_no_open_trades(self, trade_simulator, strategy):
        """Should return empty when there are no open trades."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        result = trade_simulator.update_open_trades("test_strategy")

        assert result == []

    def test_handles_data_fetch_error(self, trade_simulator, strategy, mock_trade):
        """Should continue on data fetch errors without crashing."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [mock_trade]
        trade_simulator.data_engine.fetch_stock.side_effect = Exception("Timeout")

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 0
        trade_simulator.store.save_trade.assert_not_called()

    def test_handles_none_stock_data(self, trade_simulator, strategy, mock_trade):
        """Should skip trade when fetch_stock returns None."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [mock_trade]
        trade_simulator.data_engine.fetch_stock.return_value = None

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 0

    def test_closes_multiple_expired_trades(self, trade_simulator, strategy, mock_stock_data):
        """Should close all expired trades."""
        trade1 = SimulatedTrade(
            id="trade_1",
            strategyId="test_strategy",
            symbol="AAPL",
            entryDate=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            entryPrice=150.0,
            shares=66,
            status="open",
        )
        trade2 = SimulatedTrade(
            id="trade_2",
            strategyId="test_strategy",
            symbol="MSFT",
            entryDate=(datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d"),
            entryPrice=300.0,
            shares=33,
            status="open",
        )
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [trade1, trade2]
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 2
        for t in result:
            assert t.status == "closed"
        assert trade_simulator.store.save_trade.call_count == 2

    def test_mixed_expired_and_active_trades(self, trade_simulator, strategy, mock_stock_data):
        """Should close only expired trades, keeping active ones open."""
        expired = SimulatedTrade(
            id="expired",
            strategyId="test_strategy",
            symbol="AAPL",
            entryDate=(datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d"),
            entryPrice=150.0,
            shares=66,
            status="open",
        )
        active = SimulatedTrade(
            id="active",
            strategyId="test_strategy",
            symbol="MSFT",
            entryDate=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            entryPrice=300.0,
            shares=33,
            status="open",
        )
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [expired, active]
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 1
        assert result[0].id == "expired"
        assert result[0].status == "closed"

    def test_partial_fetch_failure(self, trade_simulator, strategy, mock_stock_data):
        """Should close trades with successful fetches, skip failed ones."""
        expired1 = SimulatedTrade(
            id="expired1",
            strategyId="test_strategy",
            symbol="AAPL",
            entryDate=(datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d"),
            entryPrice=150.0,
            shares=66,
            status="open",
        )
        expired2 = SimulatedTrade(
            id="expired2",
            strategyId="test_strategy",
            symbol="MSFT",
            entryDate=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            entryPrice=300.0,
            shares=33,
            status="open",
        )

        def mock_fetch(symbol):
            if symbol == "AAPL":
                return mock_stock_data
            raise Exception("Network error")

        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = [expired1, expired2]
        trade_simulator.data_engine.fetch_stock.side_effect = mock_fetch

        result = trade_simulator.update_open_trades("test_strategy")

        assert len(result) == 1
        assert result[0].symbol == "AAPL"


# ===========================================================================
# TestRunDaily
# ===========================================================================


class TestRunDaily:
    """Tests for run_daily method."""

    def test_creates_snapshot(self, trade_simulator, strategy, mock_stock_data, mock_signal):
        """Should create and save a daily snapshot."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
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

    def test_full_workflow_with_trades(self, trade_simulator, strategy, mock_stock_data, mock_signal):
        """Should run the full scan → execute → snapshot workflow."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        snapshot = trade_simulator.run_daily("test_strategy", ["AAPL", "MSFT"])

        assert snapshot.strategyId == "test_strategy"
        assert len(snapshot.selectedStocks) <= strategy.params.maxPositions
        assert snapshot.portfolioValue > 0

    def test_snapshot_has_correct_date(self, trade_simulator, strategy, mock_stock_data, mock_signal):
        """Snapshot date should be today."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        snapshot = trade_simulator.run_daily("test_strategy", ["AAPL"])

        assert snapshot.date == datetime.now().strftime("%Y-%m-%d")

    def test_portfolio_value_equals_initial_capital_with_no_trades(
        self, trade_simulator, strategy, mock_stock_data
    ):
        """When no trades are executed, portfolio value = initialCapital."""
        # Signal below minScore → no trades
        low_signal = SignalResult(
            symbol="AAPL", signal_type="观望", score=30.0, probability_up=20.0, reasons=[]
        )
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = low_signal

        snapshot = trade_simulator.run_daily("test_strategy", ["AAPL"])

        assert snapshot.portfolioValue == strategy.params.initialCapital
        assert snapshot.cash == strategy.params.initialCapital
        assert snapshot.invested == 0

    def test_portfolio_value_with_trades(self, trade_simulator, strategy, mock_stock_data, mock_signal):
        """Portfolio value should equal cash + invested after trades."""
        saved_trades = []

        def mock_save_trade(trade):
            saved_trades.append(trade)

        def mock_get_trades(sid, status=None):
            if status == "open":
                return [t for t in saved_trades if t.status == "open"]
            return saved_trades

        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.side_effect = mock_get_trades
        trade_simulator.store.save_trade.side_effect = mock_save_trade
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        snapshot = trade_simulator.run_daily("test_strategy", ["AAPL"])

        assert snapshot.portfolioValue == snapshot.cash + snapshot.invested
        assert snapshot.invested > 0
        assert snapshot.cash < strategy.params.initialCapital

    def test_includes_closed_trades_in_snapshot(
        self, trade_simulator, strategy, mock_stock_data, mock_signal, mock_trade
    ):
        """Snapshot should include trades closed during the run."""
        call_count = 0

        def mock_get_trades(sid, status=None):
            nonlocal call_count
            call_count += 1
            # First call: during update_open_trades → returns expired trade
            if call_count == 1 and status == "open":
                return [mock_trade]
            # Subsequent calls: empty
            return []

        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.side_effect = mock_get_trades
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        snapshot = trade_simulator.run_daily("test_strategy", ["AAPL"])

        # The mock_trade should appear in closedTrades
        assert any(t.id == mock_trade.id for t in snapshot.closedTrades)

    def test_workflow_calls_methods_in_order(self, trade_simulator, strategy, mock_stock_data, mock_signal):
        """run_daily should call update_open_trades, scan_stocks, execute_trades in sequence."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []
        trade_simulator.data_engine.fetch_stock.return_value = mock_stock_data
        trade_simulator.signal_engine.generate_signal.return_value = mock_signal

        # Spy on methods
        original_update = trade_simulator.update_open_trades
        original_scan = trade_simulator.scan_stocks
        original_execute = trade_simulator.execute_trades

        call_order = []

        def spy_update(*args, **kwargs):
            call_order.append("update_open_trades")
            return original_update(*args, **kwargs)

        def spy_scan(*args, **kwargs):
            call_order.append("scan_stocks")
            return original_scan(*args, **kwargs)

        def spy_execute(*args, **kwargs):
            call_order.append("execute_trades")
            return original_execute(*args, **kwargs)

        trade_simulator.update_open_trades = spy_update
        trade_simulator.scan_stocks = spy_scan
        trade_simulator.execute_trades = spy_execute

        trade_simulator.run_daily("test_strategy", ["AAPL"])

        assert call_order == ["update_open_trades", "scan_stocks", "execute_trades"]

    def test_empty_stock_list(self, trade_simulator, strategy):
        """Should handle empty stock list gracefully."""
        trade_simulator.strategy_manager.get_strategy.return_value = strategy
        trade_simulator.store.get_trades.return_value = []

        snapshot = trade_simulator.run_daily("test_strategy", [])

        assert isinstance(snapshot, DailySnapshot)
        assert len(snapshot.selectedStocks) == 0
        assert snapshot.portfolioValue == strategy.params.initialCapital


# ===========================================================================
# TestInit
# ===========================================================================


class TestInit:
    """Tests for TradeSimulator.__init__."""

    def test_initializes_all_engines(self, tmp_path):
        """Should initialize data_engine, indicator_engine, signal_engine, store, strategy_manager."""
        from src.core.trade_simulator import TradeSimulator

        with (
            patch("src.core.trade_simulator.get_data_engine") as mock_data,
            patch("src.core.trade_simulator.get_indicator_engine") as mock_indicator,
            patch("src.core.trade_simulator.get_signal_engine") as mock_signal_engine,
            patch("src.core.trade_simulator.SimulationStore") as mock_store_cls,
            patch("src.core.trade_simulator.StrategyManager") as mock_manager_cls,
        ):
            sim = TradeSimulator(data_dir=str(tmp_path))

            mock_data.assert_called_once()
            mock_indicator.assert_called_once()
            mock_signal_engine.assert_called_once()
            mock_store_cls.assert_called_once_with(str(tmp_path))
            mock_manager_cls.assert_called_once_with(str(tmp_path))

            assert sim.data_engine is not None
            assert sim.indicator_engine is not None
            assert sim.signal_engine is not None
            assert sim.store is not None
            assert sim.strategy_manager is not None
