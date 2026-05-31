"""
Lobster Quant - FastAPI Backend
REST API for the quantitative trading analysis platform.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
import os
import uuid

# Add the parent directory to the path to import existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Explicitly fix for sub-module imports inside lobster_quant
# This helps when files inside lobster_quant use "from src... import"
lobster_quant_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lobster_quant")
if os.path.exists(lobster_quant_path):
    sys.path.insert(0, lobster_quant_path)

app = FastAPI(
    title="Lobster Quant API",
    description="REST API for quantitative trading analysis",
    version="2.0.0",
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


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------

logger = logging.getLogger("lobster_quant")

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


# Import and include routers
from api.routes import stocks, scanner, backtest, settings, strategy, simulation, health, help

app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["scanner"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["strategy"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(help.router, prefix="/api/help", tags=["help"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
