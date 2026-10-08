"""History-backed read-only anomaly tool."""
from typing import Literal
from pydantic import Field
from lobster_quant.src.analysis.market_anomaly import calculate_market_anomaly as calculate_metrics
from ..schemas import Citation
from .market_history import MarketHistoryInput, MarketDependencies, StrictModel, Symbol, UTC, get_market_history, stable_ref
from .registry import ToolRegistry, ToolSpec


class MarketAnomalyInput(MarketHistoryInput):
    benchmark: Symbol | None = None
    lookback: int = Field(default=21, ge=21, le=2520)


class MarketAnomalyOutput(StrictModel):
    symbol: Symbol
    as_of: UTC
    status: Literal["ok", "insufficient_data", "unavailable"]
    return_pct: float | None = None
    volume_ratio_20: float | None = None
    excess_return_pct: float | None = None
    relative_strength: float | None = None
    limitations: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    result_ref: str
    citations: list[Citation] = Field(default_factory=list)


def calculate_market_anomaly(payload: MarketAnomalyInput, dependencies: MarketDependencies) -> MarketAnomalyOutput:
    request = MarketHistoryInput(**payload.model_dump(exclude={"benchmark"}))
    history = get_market_history(request, dependencies)
    benchmark = get_market_history(request.model_copy(update={"symbol": payload.benchmark}), dependencies) if payload.benchmark else None
    bars = history.series.bars if history.series else []
    bbars = benchmark.series.bars if benchmark and benchmark.series else []
    metrics = calculate_metrics([str(b.session_date) for b in bars], [b.close for b in bars], [b.volume for b in bars], [str(b.session_date) for b in bbars], [b.close for b in bbars])
    limitations = history.limitations + metrics.pop("limitations")
    if history.gaps:
        metrics = {key: None for key in metrics}
        limitations.append("Metrics withheld across missing/suspended sessions")
    if benchmark and (benchmark.gaps or benchmark.status == "unavailable" or benchmark.series is None or history.series is None or benchmark.series.currency != history.series.currency):
        metrics["excess_return_pct"] = metrics["relative_strength"] = None
        limitations.append("Benchmark unavailable, gapped, or currency incompatible")
    sources = [history.result_ref] + ([benchmark.result_ref] if benchmark else [])
    ref = stable_ref("market-anomaly", {"request": payload.model_dump(mode="json"), "sources": sources, "metrics": metrics})
    return MarketAnomalyOutput(symbol=payload.symbol, as_of=payload.as_of, status="unavailable" if history.status == "unavailable" else "insufficient_data" if limitations else "ok", **metrics, limitations=limitations, source_ids=sources, result_ref=ref, citations=[Citation(type="tool_result", ref_id=ref, label="deterministic anomaly", metadata={"source_ids": sources})])


def register_tools(registry: ToolRegistry, dependencies: MarketDependencies) -> None:
    registry.register(ToolSpec(name="calculate_market_anomaly", version="1", description="Calculate same-date return, prior-20 volume and benchmark-relative facts", input_model=MarketAnomalyInput, output_model=MarketAnomalyOutput, handler=lambda p: calculate_market_anomaly(p, dependencies)))
