"""
Lobster Quant - FastAPI Backend
REST API for the quantitative trading analysis platform.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os

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


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Lobster Quant API", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
from api.routes import stocks, scanner, backtest, settings, strategy, simulation

app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["scanner"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["strategy"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
