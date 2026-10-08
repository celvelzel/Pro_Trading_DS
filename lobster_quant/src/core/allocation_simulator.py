"""Deterministic close-to-close allocation simulation, independent of strategy backtests."""
from __future__ import annotations
from decimal import Decimal, localcontext
from datetime import date
from typing import Mapping
from .portfolio_risk import align_prices, decimal_value


class AllocationSimulator:
    def simulate(self, histories: Mapping[str, Mapping[date, object]], target_weights: Mapping[str, object],
                 initial_value: object, rebalance_every: int = 1, fee_bps: object = 0,
                 slippage_bps: object = 0) -> dict:
        weights = {s: decimal_value(v) for s, v in target_weights.items()}
        if "CASH" not in weights or abs(sum(weights.values()) - 1) > Decimal("1e-8"):
            raise ValueError("Explicit CASH and weights summing to one required")
        total_weight = sum(weights.values())
        with localcontext() as ctx:
            ctx.prec = 28
            weights = {s:w/total_weight for s,w in weights.items()}
            weights["CASH"] = Decimal(1)-sum((w for s,w in weights.items() if s != "CASH"), Decimal(0))
        if isinstance(rebalance_every, bool) or not isinstance(rebalance_every, int) or rebalance_every < 1:
            raise ValueError("Invalid rebalance cadence")
        fee = decimal_value(fee_bps)
        slippage = decimal_value(slippage_bps)
        rate = (fee + slippage) / 10000
        if rate >= 1:
            raise ValueError("Total cost rate must be below 10000 bps")
        initial = decimal_value(initial_value, positive=True)
        assets = sorted(s for s, w in weights.items() if s != "CASH" and w > 0)
        if not set(assets).issubset(histories):
            raise ValueError("Positive target asset histories required")
        days, prices, dropped = align_prices({s: histories[s] for s in assets} if assets else histories)
        with localcontext() as ctx:
            ctx.prec = 28
            # Self-financing cost equation: posttrade NAV + cost(traded notional) = pretrade NAV.
            def rebalance(values: dict[str, Decimal]) -> tuple[dict[str, Decimal], Decimal, Decimal]:
                nav = sum(values.values())
                lo, hi = Decimal(0), nav
                for _ in range(120):
                    post = (lo + hi) / 2
                    turnover = sum(abs(post * weights[s] - values.get(s, Decimal(0))) for s in assets)
                    if post + turnover * rate > nav:
                        hi = post
                    else:
                        lo = post
                post = (lo + hi) / 2
                turnover = sum(abs(post * weights[s] - values.get(s, Decimal(0))) for s in assets)
                return {s: post*w for s,w in weights.items()}, turnover*rate, turnover
            values, cost, turnover = rebalance({"CASH": initial})
            total_cost, total_turnover = cost, turnover
            path = [dict(date=days[0], net_value=sum(values.values()), cost=cost, turnover=turnover)]
            # Target is fixed before the first bar; day i gains use holdings fixed at day i-1.
            for i in range(1, len(days)):
                for symbol in assets:
                    values[symbol] *= prices[symbol][i] / prices[symbol][i-1]
                cost = turnover = Decimal(0)
                if i % rebalance_every == 0 and i < len(days)-1:
                    values, cost, turnover = rebalance(values)
                    total_cost += cost
                    total_turnover += turnover
                path.append(dict(date=days[i], net_value=sum(values.values()), cost=cost, turnover=turnover))
            final = path[-1]["net_value"]
            return dict(path=path, total_cost=total_cost, total_turnover=total_turnover,
                        total_return=final/initial-1, final_weights={s:v/final for s,v in values.items()},
                        warnings=["noncommon_dates_excluded"] if dropped else [])
