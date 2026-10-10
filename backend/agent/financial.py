"""Explicit application assembly for the two reviewed financial drivers.

Default data and providers are synthetic demonstrations. Caller-supplied
adapters/providers require ``demo=False``, a versioned execution profile and
complete explicit dependencies. Queue workers only reconstruct their trusted
deployment mapping; an unsupported profile never falls back to synthetic data.
No global tool registry, user holdings or provider credentials are modified.
"""
from __future__ import annotations

from agent.shared import FinancialMASDispatcher, WorkflowRegistry, RunBudget, ArtifactStore
from agent.tools.registry import ToolRegistry


def build_financial_dispatcher(session_factory, *,
        enabled=("market_investigation", "portfolio_rebalance"),
        demo=True, providers=None, market_dependencies=None,
        event_dependencies=None, portfolio_dependencies=None,
        portfolio_artifact_resolver=None, execution_profile=None, clock=None, lease_seconds=30,
        market_mode="autonomous", portfolio_mode="full"):
    enabled = tuple(enabled)
    allowed = {"market_investigation", "portfolio_rebalance"}
    if len(set(enabled)) != len(enabled) or not set(enabled) <= allowed:
        raise ValueError("Unknown or duplicate financial workflow")
    if market_mode not in {"autonomous", "fixed", "single"}:
        raise ValueError("Unknown Market execution mode")
    if portfolio_mode not in {"full", "fixed", "single", "no_verifier", "no_independent_risk_critic"}:
        raise ValueError("Unknown Portfolio execution mode")
    if demo:
        if execution_profile not in (None, "synthetic-demo-v1"):
            raise ValueError("Demo assembly requires the reserved synthetic-demo-v1 profile")
        if any(value is not None for value in (providers, market_dependencies,
                event_dependencies, portfolio_dependencies)):
            raise ValueError("Synthetic profile cannot contain custom providers or data adapters")
        execution_profile = "synthetic-demo-v1"
    elif execution_profile is None or execution_profile == "synthetic-demo-v1":
        raise ValueError("Configured assembly requires an explicit non-demo execution profile")
    if not demo and providers is None:
        raise ValueError("Explicit providers and trusted adapters required outside demo mode")
    providers = providers or {}
    registry, tools = WorkflowRegistry(), ToolRegistry()
    options = {"lease_seconds": lease_seconds, "execution_profile": execution_profile}
    if clock is not None:
        options["clock"] = clock
    dispatcher = FinancialMASDispatcher(session_factory, registry, tools, **options)

    if "market_investigation" in enabled:
        from agent.market_mas import create_market_driver, SyntheticMarketModel
        from agent.tools import market_history, anomaly, market_events
        if market_dependencies is None or event_dependencies is None:
            if not demo:
                raise ValueError("Explicit Market history and evidence adapters required")
            from agent.financial_demo import demo_market_dependencies
            default_history, default_events = demo_market_dependencies()
            market_dependencies = market_dependencies or default_history
            event_dependencies = event_dependencies or default_events
        market_history.register_tools(tools, market_dependencies)
        anomaly.register_tools(tools, market_dependencies)
        market_events.register_tools(tools, event_dependencies)
        roles = ("coordinator", "price_volume", "macro_sector", "event", "critic")
        market_providers = providers.get("market_investigation")
        if market_providers is None:
            if not demo:
                raise ValueError("Explicit Market role providers required")
            market_providers = {role: SyntheticMarketModel(role) for role in roles}
        registry.register(create_market_driver(market_providers,
            mode=market_mode,
            budget_reader=lambda run_id: RunBudget.model_validate(dispatcher.snapshot(run_id)["budget"])))

    if "portfolio_rebalance" in enabled:
        from agent.portfolio_mas import PortfolioDriver, PortfolioDependencies, SyntheticPortfolioModel
        from agent.tools import portfolio_snapshot, portfolio_risk, allocation
        if portfolio_dependencies is None:
            if not demo:
                raise ValueError("Explicit immutable Portfolio snapshot/history adapters required")
            from agent.financial_demo import demo_snapshot_loader, demo_histories, demo_classifications
            portfolio_dependencies = PortfolioDependencies(demo_snapshot_loader,
                lambda snapshot, as_of: demo_histories(), demo_classifications())
        portfolio_snapshot.register_tools(tools, portfolio_dependencies)
        portfolio_risk.register_tools(tools)
        allocation.register_tools(tools)
        roles = ("coordinator", "opportunity", "risk", "constraint", "verifier")
        portfolio_providers = providers.get("portfolio_rebalance")
        if portfolio_providers is None:
            if not demo:
                raise ValueError("Explicit Portfolio role providers required")
            portfolio_providers = {role: SyntheticPortfolioModel(role) for role in roles}
        registry.register(PortfolioDriver(portfolio_providers, portfolio_dependencies,
            artifact_store=ArtifactStore(session_factory), artifact_resolver=portfolio_artifact_resolver,
            mode=portfolio_mode))
    return dispatcher
