"""
Simulation Scheduler - Manages daily simulation execution.
"""

from datetime import datetime
from typing import Any, Dict, List

from .trade_simulator import TradeSimulator
from .strategy_manager import StrategyManager
from ..utils.logging import get_logger

logger = get_logger()


class SimulationScheduler:
    """Manages daily simulation execution."""

    # Default stock lists
    US_STOCK_LIST = [
        "AIPO", "AMZN", "COHR", "GLW", "GOOG", "ICLN", "LITE", "MU",
        "QQQ", "SPY", "TSLA", "URA", "VTI", "XLE", "XLU",
    ]

    HK_STOCK_LIST = [
        "0005.HK", "0700.HK", "1299.HK", "2318.HK", "3690.HK",
        "9988.HK", "1810.HK", "2269.HK", "2020.HK", "9618.HK",
    ]

    A_STOCK_LIST = [
        "600519", "000001", "300308", "002594", "600036",
        "000333", "300750", "601318", "600276", "002415",
    ]

    def __init__(self, data_dir: str = "data"):
        self.simulator = TradeSimulator(data_dir)
        self.strategy_manager = StrategyManager(data_dir)
        self._running = False

    def get_stock_list(self, market: str = "US") -> List[str]:
        """Get stock list for a market.

        Args:
            market: Market code ("US", "HK", "A")

        Returns:
            List of stock symbols for the given market.
        """
        if market == "US":
            return self.US_STOCK_LIST
        elif market == "HK":
            return self.HK_STOCK_LIST
        elif market == "A":
            return self.A_STOCK_LIST
        else:
            return self.US_STOCK_LIST

    def run_daily(self, market: str = "US") -> Dict[str, Any]:
        """Run daily simulation for all active strategies.

        Args:
            market: Market to scan ("US", "HK", "A")

        Returns:
            Dictionary with results per strategy:
            {
                "timestamp": str,
                "market": str,
                "results": [
                    {
                        "strategy_id": str,
                        "strategy_name": str,
                        "status": "success" | "error",
                        "snapshot": DailySnapshot | None,
                        "error": str | None
                    },
                    ...
                ]
            }
        """
        if self._running:
            return {"error": "Scheduler already running"}

        self._running = True
        results: List[Dict[str, Any]] = []

        try:
            strategies = self.strategy_manager.list_strategies()
            stock_list = self.get_stock_list(market)

            for strategy in strategies:
                try:
                    snapshot = self.simulator.run_daily(strategy.id, stock_list)
                    results.append({
                        "strategy_id": strategy.id,
                        "strategy_name": strategy.name,
                        "status": "success",
                        "snapshot": snapshot,
                        "error": None,
                    })
                except Exception as e:
                    logger.error(f"Simulation failed for {strategy.id}: {e}")
                    results.append({
                        "strategy_id": strategy.id,
                        "strategy_name": strategy.name,
                        "status": "error",
                        "snapshot": None,
                        "error": str(e),
                    })

            return {
                "timestamp": datetime.now().isoformat(),
                "market": market,
                "results": results,
            }

        finally:
            self._running = False

    def run_strategy(self, strategy_id: str, market: str = "US") -> Dict[str, Any]:
        """Run simulation for a specific strategy.

        Args:
            strategy_id: Strategy ID to run
            market: Market to scan

        Returns:
            Dictionary with result
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if strategy is None:
            return {"error": f"Strategy {strategy_id} not found"}

        stock_list = self.get_stock_list(market)

        try:
            snapshot = self.simulator.run_daily(strategy_id, stock_list)
            return {
                "timestamp": datetime.now().isoformat(),
                "market": market,
                "strategy_id": strategy_id,
                "strategy_name": strategy.name,
                "status": "success",
                "snapshot": snapshot,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Simulation failed for {strategy_id}: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "market": market,
                "strategy_id": strategy_id,
                "strategy_name": strategy.name,
                "status": "error",
                "snapshot": None,
                "error": str(e),
            }
