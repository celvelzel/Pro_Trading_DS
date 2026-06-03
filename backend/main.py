"""
Lobster Quant - FastAPI Backend
REST API for the quantitative trading analysis platform.
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
import os
import uuid

logger = logging.getLogger("lobster_quant")


@asynccontextmanager
async def lifespan(app):
    """Warm up engine singletons at startup to eliminate per-request lazy imports."""
    logger.info("Warming up DataEngine/IndicatorEngine/SignalEngine...")
    from lobster_quant.src.core.data_engine import get_data_engine
    from lobster_quant.src.core.indicator_engine import get_indicator_engine
    from lobster_quant.src.core.signal_engine import get_signal_engine

    get_data_engine()
    get_indicator_engine()
    get_signal_engine()
    logger.info("Engine warmup complete.")

    # Start the background alert monitor for WebSocket push
    from services.alert_monitor import start_alert_monitor, stop_alert_monitor

    start_alert_monitor()

    yield

    stop_alert_monitor()


app = FastAPI(
    title="Lobster Quant API",
    description="REST API for quantitative trading analysis",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",  # Alternative port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression — only compress responses > 500 bytes (ships with Starlette, no new deps)
app.add_middleware(GZipMiddleware, minimum_size=500)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------

# Map common HTTP status codes to machine-readable error codes
_HTTP_STATUS_TO_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


def _build_error_response(
    status_code: int,
    code: str,
    message: str,
    detail: str | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Build a unified error JSONResponse."""
    from api.models.common import ErrorResponse, ErrorDetail

    rid = request_id or str(uuid.uuid4())
    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message, detail=detail),
        detail=message,
        request_id=rid,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with unified error format."""
    request_id = str(uuid.uuid4())
    code = _HTTP_STATUS_TO_CODE.get(exc.status_code, "HTTP_ERROR")
    detail_msg = str(exc.detail)

    logger.warning(
        "[%s] HTTP %s: %s | %s %s",
        request_id,
        exc.status_code,
        detail_msg,
        request.method,
        request.url.path,
    )

    return _build_error_response(
        status_code=exc.status_code,
        code=code,
        message=detail_msg,
        detail=detail_msg,
        request_id=request_id,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors with unified format."""
    request_id = str(uuid.uuid4())
    errors = exc.errors()
    # Flatten the first error message for the user
    messages = []
    for err in errors:
        loc = " → ".join(str(l) for l in err.get("loc", []))
        messages.append(f"{loc}: {err.get('msg', 'Invalid')}")
    detail_msg = "; ".join(messages)

    logger.warning(
        "[%s] Validation error: %s | %s %s",
        request_id,
        detail_msg,
        request.method,
        request.url.path,
    )

    return _build_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        detail=detail_msg,
        request_id=request_id,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    request_id = str(uuid.uuid4())

    logger.error(
        "[%s] Unhandled exception: %s | %s %s",
        request_id,
        exc,
        request.method,
        request.url.path,
        exc_info=True,
    )

    return _build_error_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="Internal server error",
        detail=str(exc),
        request_id=request_id,
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Lobster Quant API", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# WebSocket: Alert Notifications
# ---------------------------------------------------------------------------


@app.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket):
    """WebSocket endpoint for real-time alert notifications.

    Clients receive JSON messages of the form:
        {"type": "alert_triggered", "alert": { ... }}

    Falls back gracefully — the frontend should use polling when WS is unavailable.
    """
    from services.alert_monitor import register_ws_client, unregister_ws_client

    await register_ws_client(ws)
    try:
        # Keep the connection alive; ignore incoming messages
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await unregister_ws_client(ws)


# Import and include routers
from api.routes import stocks, scanner, backtest, settings, strategy, strategy_history, simulation, health, help, watchlist, alerts, cache, portfolio, signals_stats

app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["scanner"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["strategy"])
app.include_router(strategy_history.router, prefix="/api/strategy", tags=["strategy-history"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(help.router, prefix="/api/help", tags=["help"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(cache.router, prefix="/api/cache", tags=["cache"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(signals_stats.router, prefix="/api/signals", tags=["signals-stats"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
