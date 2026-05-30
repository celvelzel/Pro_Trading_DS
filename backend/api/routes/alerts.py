"""
Alerts API Router
Endpoints for managing alert rules and checking triggered alerts.
"""

from fastapi import APIRouter, HTTPException
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from api.models.alerts import (
    CreateAlertRuleRequest,
    UpdateAlertRuleRequest,
    AlertRuleResponse,
    AlertRulesListResponse,
    TriggeredAlertResponse,
    TriggeredAlertsResponse,
    MarkReadResponse,
)

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "lobster_quant", "data")


def _get_store():
    """Lazy import to get the alert store."""
    from lobster_quant.src.storage.alert_store import AlertStore
    return AlertStore(data_dir=DATA_DIR)


def _get_stock_price(symbol: str) -> float:
    """Get current stock price."""
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        engine = get_data_engine()
        stock_data = engine.fetch_stock(symbol)
        if stock_data is None:
            return 0.0
        return float(stock_data.daily.iloc[-1]["close"])
    except Exception:
        return 0.0


def _get_stock_score(symbol: str) -> float:
    """Get current stock score."""
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.analysis.signals import SignalGenerator

        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()

        stock_data = data_engine.fetch_stock(symbol)
        if stock_data is None:
            return 0.0

        df = indicator_engine.compute_all(stock_data.daily)
        generator = SignalGenerator()
        signal = generator.generate(df, symbol)
        return float(signal.score)
    except Exception:
        return 0.0


def _get_stock_signal_type(symbol: str) -> str:
    """Get current stock signal type."""
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.analysis.signals import SignalGenerator

        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()

        stock_data = data_engine.fetch_stock(symbol)
        if stock_data is None:
            return "neutral"

        df = indicator_engine.compute_all(stock_data.daily)
        generator = SignalGenerator()
        signal = generator.generate(df, symbol)
        return str(signal.signal_type)
    except Exception:
        return "neutral"


# ============================================================================
# Alert Rules CRUD
# ============================================================================


@router.get("/rules", response_model=AlertRulesListResponse)
async def list_alert_rules():
    """List all alert rules."""
    try:
        store = _get_store()
        rules = store.list_rules()
        return AlertRulesListResponse(
            rules=[AlertRuleResponse(**r) for r in rules]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(request: CreateAlertRuleRequest):
    """Create a new alert rule."""
    try:
        store = _get_store()
        rule = store.create_rule(request.model_dump())
        return AlertRuleResponse(**rule)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """Delete an alert rule."""
    try:
        store = _get_store()
        deleted = store.delete_rule(rule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: str, request: UpdateAlertRuleRequest):
    """Update an alert rule."""
    try:
        store = _get_store()
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        rule = store.update_rule(rule_id, updates)
        if rule is None:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        return AlertRuleResponse(**rule)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Triggered Alerts
# ============================================================================


@router.get("/triggered", response_model=TriggeredAlertsResponse)
async def get_triggered_alerts():
    """
    Check all enabled alert rules against current data and return triggered alerts.
    Also returns the history of previously triggered alerts.
    """
    try:
        store = _get_store()
        rules = store.list_rules()
        newly_triggered = []

        # Check each enabled rule
        for rule in rules:
            if not rule.get("enabled", True):
                continue

            symbol = rule["symbol"]
            condition = rule["condition"]
            threshold = rule["threshold"]
            current_value = 0.0
            triggered = False
            message = ""

            if condition == "score_above":
                current_value = _get_stock_score(symbol)
                if current_value > threshold:
                    triggered = True
                    message = f"{symbol} score {current_value:.1f} is above threshold {threshold:.1f}"

            elif condition == "score_below":
                current_value = _get_stock_score(symbol)
                if current_value < threshold:
                    triggered = True
                    message = f"{symbol} score {current_value:.1f} is below threshold {threshold:.1f}"

            elif condition == "price_above":
                current_value = _get_stock_price(symbol)
                if current_value > threshold:
                    triggered = True
                    message = f"{symbol} price ${current_value:.2f} is above threshold ${threshold:.2f}"

            elif condition == "price_below":
                current_value = _get_stock_price(symbol)
                if current_value < threshold:
                    triggered = True
                    message = f"{symbol} price ${current_value:.2f} is below threshold ${threshold:.2f}"

            elif condition == "signal_change":
                current_signal = _get_stock_signal_type(symbol)
                current_value = 0.0
                # For signal_change, threshold stores the expected signal as a number
                # 1 = bullish, 0 = neutral, -1 = bearish
                signal_map = {"bullish": 1, "neutral": 0, "bearish": -1}
                current_signal_val = signal_map.get(current_signal, 0)
                if current_signal_val != threshold:
                    triggered = True
                    message = f"{symbol} signal changed to {current_signal}"

            if triggered:
                # Record the triggered alert
                entry = store.add_triggered({
                    "ruleId": rule["id"],
                    "symbol": symbol,
                    "condition": condition,
                    "threshold": threshold,
                    "currentValue": current_value,
                    "message": message,
                })
                newly_triggered.append(entry)

        # Get full history
        history = store.get_triggered_history(limit=50)
        unread_count = store.get_unread_count()

        return TriggeredAlertsResponse(
            alerts=[TriggeredAlertResponse(**a) for a in history],
            unreadCount=unread_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read", response_model=MarkReadResponse)
async def mark_alerts_read():
    """Mark all triggered alerts as read."""
    try:
        store = _get_store()
        store.mark_all_read()
        return MarkReadResponse(success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
