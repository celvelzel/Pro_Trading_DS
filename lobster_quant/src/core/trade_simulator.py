"""
Lobster Quant - Trade Simulator
Simulates daily trading based on strategy signals.
"""

from datetime import datetime
from typing import List, Dict, Any

from ..data.models import (
    SimulatedTrade,
    DailySnapshot,
    Strategy,
)
from ..storage.simulation_store import SimulationStore
from .strategy_manager import StrategyManager
from .data_engine import get_data_engine
from .indicator_engine import get_indicator_engine
from .signal_engine import get_signal_engine
from ..utils.logging import get_logger

logger = get_logger()


class TradeSimulator:
    """Simulates daily trading based on strategy signals."""

    def __init__(self, data_dir: str = "data"):
        self.data_engine = get_data_engine()
        self.indicator_engine = get_indicator_engine()
        self.signal_engine = get_signal_engine()
        self.store = SimulationStore(data_dir)
        self.strategy_manager = StrategyManager(data_dir)

    def scan_stocks(
        self, strategy: Strategy, stock_list: List[str]
    ) -> List[Dict[str, Any]]:
        """Scan stocks and return those meeting strategy criteria.

        Args:
            strategy: Strategy with parameters
            stock_list: List of stock symbols to scan

        Returns:
            List of dicts with stock info and signal:
            [{"symbol": str, "score": float, "signal_type": str, "price": float}, ...]
        """
        selected = []

        for symbol in stock_list:
            try:
                # Fetch stock data
                stock_data = self.data_engine.fetch_stock(symbol)
                if stock_data is None:
                    continue

                # Compute indicators
                df = self.indicator_engine.compute_all(stock_data.daily)

                # Generate signal
                signal = self.signal_engine.generate_signal(stock_data)

                # Check if meets strategy criteria
                if signal.score >= strategy.params.minScore:
                    selected.append(
                        {
                            "symbol": symbol,
                            "score": signal.score,
                            "signal_type": signal.signal_type,
                            "price": stock_data.get_latest_price(),
                            "reasons": signal.reasons,
                        }
                    )

            except Exception as e:
                logger.warning(f"Failed to scan {symbol}: {e}")
                continue

        # Sort by score (highest first)
        selected.sort(key=lambda x: x["score"], reverse=True)

        # Limit by maxPositions
        return selected[: strategy.params.maxPositions]

    def execute_trades(
        self, strategy_id: str, selected_stocks: List[Dict[str, Any]]
    ) -> List[SimulatedTrade]:
        """Execute buy trades for selected stocks.

        Args:
            strategy_id: Strategy ID
            selected_stocks: List of stock info dicts from scan_stocks()

        Returns:
            List of newly created SimulatedTrade objects
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if strategy is None:
            return []

        # Get current open trades
        open_trades = self.store.get_trades(strategy_id, status="open")

        # Calculate available capital
        initial_capital = strategy.params.initialCapital
        invested = sum(t.entryPrice * t.shares for t in open_trades)
        available = initial_capital - invested

        new_trades = []

        for stock in selected_stocks:
            # Check if already have open position for this stock
            if any(t.symbol == stock["symbol"] for t in open_trades):
                continue

            # Calculate position size
            if strategy.params.positionSizing == "fixed":
                position_value = initial_capital * strategy.params.positionSize
            else:
                # Dynamic: scale by score
                score_factor = stock["score"] / 100
                position_value = (
                    initial_capital * strategy.params.positionSize * score_factor
                )

            # Check if enough capital
            if position_value > available:
                continue

            # Calculate shares
            price = stock["price"]
            if price <= 0:
                continue

            shares = int(position_value / price)
            if shares <= 0:
                continue

            # Create trade
            trade = SimulatedTrade(
                id=f"trade_{int(datetime.now().timestamp())}_{stock['symbol']}",
                strategyId=strategy_id,
                symbol=stock["symbol"],
                entryDate=datetime.now().strftime("%Y-%m-%d"),
                entryPrice=price,
                shares=shares,
                status="open",
            )

            self.store.save_trade(trade)
            new_trades.append(trade)
            available -= price * shares

        return new_trades

    def update_open_trades(self, strategy_id: str) -> List[SimulatedTrade]:
        """Check open trades for exit conditions and close if met.

        Args:
            strategy_id: Strategy ID

        Returns:
            List of closed trades
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if strategy is None:
            return []

        open_trades = self.store.get_trades(strategy_id, status="open")
        closed_trades = []

        for trade in open_trades:
            try:
                # Fetch current stock data
                stock_data = self.data_engine.fetch_stock(trade.symbol)
                if stock_data is None:
                    continue

                current_price = stock_data.get_latest_price()

                # Check holding period
                entry_date = datetime.strptime(trade.entryDate, "%Y-%m-%d")
                days_held = (datetime.now() - entry_date).days

                if days_held >= strategy.params.holdingDays:
                    # Close trade
                    trade.exitDate = datetime.now().strftime("%Y-%m-%d")
                    trade.exitPrice = current_price
                    trade.status = "closed"
                    trade.pnl = (current_price - trade.entryPrice) * trade.shares
                    trade.pnlPercent = (
                        (current_price - trade.entryPrice) / trade.entryPrice * 100
                    )

                    self.store.save_trade(trade)
                    closed_trades.append(trade)

            except Exception as e:
                logger.warning(
                    f"Failed to update trade for {trade.symbol}: {e}"
                )
                continue

        return closed_trades

    def run_daily(
        self, strategy_id: str, stock_list: List[str]
    ) -> DailySnapshot:
        """Run daily simulation for a strategy.

        Args:
            strategy_id: Strategy ID
            stock_list: List of stock symbols to scan

        Returns:
            DailySnapshot with today's simulation results
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if strategy is None:
            raise ValueError(f"Strategy {strategy_id} not found")

        # 1. Update existing trades (check for exits)
        closed_trades = self.update_open_trades(strategy_id)

        # 2. Scan for new stocks
        selected_stocks = self.scan_stocks(strategy, stock_list)

        # 3. Execute new trades
        new_trades = self.execute_trades(strategy_id, selected_stocks)

        # 4. Get current portfolio state
        open_trades = self.store.get_trades(strategy_id, status="open")

        # Calculate portfolio value
        invested = sum(t.entryPrice * t.shares for t in open_trades)
        cash = strategy.params.initialCapital - invested
        portfolio_value = cash + invested

        # 5. Create snapshot
        snapshot = DailySnapshot(
            date=datetime.now().strftime("%Y-%m-%d"),
            strategyId=strategy_id,
            selectedStocks=selected_stocks,
            openTrades=open_trades,
            closedTrades=closed_trades,
            portfolioValue=portfolio_value,
            cash=cash,
            invested=invested,
        )

        self.store.save_snapshot(snapshot)

        return snapshot
