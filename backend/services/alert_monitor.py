"""
Alert Monitor - Background service that checks alert rules every 60s
and pushes triggered alerts to connected WebSocket clients.
"""

import asyncio
import logging
from typing import Any, Set

from starlette.websockets import WebSocket

logger = logging.getLogger("lobster_quant.alert_monitor")

# Connected WebSocket clients
_ws_clients: Set[WebSocket] = set()

# Background task handle
_monitor_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# WebSocket Client Management
# ---------------------------------------------------------------------------


async def register_ws_client(ws: WebSocket) -> None:
    """Accept and register a new WebSocket client for alert notifications."""
    await ws.accept()
    _ws_clients.add(ws)
    logger.info("Alert WS client connected. Total: %d", len(_ws_clients))


async def unregister_ws_client(ws: WebSocket) -> None:
    """Remove a disconnected WebSocket client."""
    _ws_clients.discard(ws)
    logger.info("Alert WS client disconnected. Total: %d", len(_ws_clients))


async def broadcast_alert(alert_data: dict[str, Any]) -> None:
    """Push alert data to all connected WebSocket clients. Cleans up dead connections."""
    dead: set[WebSocket] = set()
    for client in _ws_clients:
        try:
            await client.send_json(alert_data)
        except Exception:
            dead.add(client)
    if dead:
        _ws_clients.difference_update(dead)
        logger.debug("Cleaned up %d dead WS connections", len(dead))


# ---------------------------------------------------------------------------
# Alert Checking Logic
# ---------------------------------------------------------------------------


async def _check_and_broadcast() -> None:
    """Check all enabled alert rules against current market data.
    Broadcasts new triggers to all connected WebSocket clients."""
    from fastapi.responses import JSONResponse

    from api.routes.alerts import (
        _get_stock_price,
        _get_stock_score,
        _get_stock_signal_type,
        _get_store,
    )

    store = _get_store()
    rules = store.list_rules()

    for rule in rules:
        if not rule.get("enabled", True):
            continue

        symbol: str = rule["symbol"]
        condition: str = rule["condition"]
        threshold: float = rule["threshold"]
        current_value = 0.0
        triggered = False
        message = ""

        try:
            if condition == "score_above":
                result = _get_stock_score(symbol)
                if isinstance(result, JSONResponse):
                    continue
                if result["error"]:
                    continue
                current_value = result["value"]
                if current_value > threshold:
                    triggered = True
                    message = (
                        f"{symbol} score {current_value:.1f} "
                        f"is above threshold {threshold:.1f}"
                    )

            elif condition == "score_below":
                result = _get_stock_score(symbol)
                if isinstance(result, JSONResponse):
                    continue
                if result["error"]:
                    continue
                current_value = result["value"]
                if current_value < threshold:
                    triggered = True
                    message = (
                        f"{symbol} score {current_value:.1f} "
                        f"is below threshold {threshold:.1f}"
                    )

            elif condition == "price_above":
                result = _get_stock_price(symbol)
                if isinstance(result, JSONResponse):
                    continue
                if result["error"]:
                    continue
                current_value = result["value"]
                if current_value > threshold:
                    triggered = True
                    message = (
                        f"{symbol} price ${current_value:.2f} "
                        f"is above threshold ${threshold:.2f}"
                    )

            elif condition == "price_below":
                result = _get_stock_price(symbol)
                if isinstance(result, JSONResponse):
                    continue
                if result["error"]:
                    continue
                current_value = result["value"]
                if current_value < threshold:
                    triggered = True
                    message = (
                        f"{symbol} price ${current_value:.2f} "
                        f"is below threshold ${threshold:.2f}"
                    )

            elif condition == "signal_change":
                result = _get_stock_signal_type(symbol)
                if isinstance(result, JSONResponse):
                    continue
                if result["error"]:
                    continue
                current_signal = result["value"]
                current_value = 0.0
                signal_map = {"bullish": 1, "neutral": 0, "bearish": -1}
                current_signal_val = signal_map.get(current_signal, 0)
                if current_signal_val != threshold:
                    triggered = True
                    message = f"{symbol} signal changed to {current_signal}"

        except Exception as exc:
            logger.warning("Error checking rule %s for %s: %s", rule["id"], symbol, exc)
            continue

        if triggered:
            entry = store.add_triggered(
                {
                    "ruleId": rule["id"],
                    "symbol": symbol,
                    "condition": condition,
                    "threshold": threshold,
                    "currentValue": current_value,
                    "message": message,
                }
            )
            logger.info("Alert triggered: %s", message)

            # Push to all connected WebSocket clients
            await broadcast_alert({"type": "alert_triggered", "alert": entry})


# ---------------------------------------------------------------------------
# Background Monitor Loop
# ---------------------------------------------------------------------------


async def _monitor_loop(interval_seconds: int = 60) -> None:
    """Background loop that checks alerts at a fixed interval."""
    logger.info("Alert monitor loop started (interval=%ds)", interval_seconds)
    while True:
        try:
            await _check_and_broadcast()
        except asyncio.CancelledError:
            logger.info("Alert monitor loop cancelled")
            raise
        except Exception as exc:
            logger.error("Alert monitor cycle failed: %s", exc, exc_info=True)
        await asyncio.sleep(interval_seconds)


def start_alert_monitor() -> None:
    """Start the background alert monitor task (call from lifespan)."""
    global _monitor_task
    if _monitor_task is None or _monitor_task.done():
        _monitor_task = asyncio.create_task(_monitor_loop())
        logger.info("Alert monitor background task created")


def stop_alert_monitor() -> None:
    """Stop the background alert monitor task (call from lifespan)."""
    global _monitor_task
    if _monitor_task is not None and not _monitor_task.done():
        _monitor_task.cancel()
        _monitor_task = None
        logger.info("Alert monitor background task cancelled")
