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
from api.routes import stocks, scanner, backtest

app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["scanner"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
