# Lobster Quant

🦞 **Lobster Quant** - Quantitative Trading Research Tool

A modular, production-grade quantitative trading analysis platform built with Python and Streamlit.

## Features

- **Multi-Market Scanner** - US, HK, A-share markets
- **Technical Analysis** - 15+ indicators with registry pattern
- **Signal Generation** - Multi-factor scoring system
- **OFF Filter** - Market condition risk assessment
- **Backtesting** - Enhanced with slippage and commission
- **Persistent Cache** - Disk + memory cache with TTL
- **Dark/Light Theme** - Full theme support

## Architecture

```
src/
├── core/           # Core engines (data, risk, indicators)
├── data/           # Data layer (models, providers, cache)
│   └── providers/  # yfinance, akshare, mock
├── analysis/       # Analysis layer
│   ├── indicators/ # Technical indicators
│   ├── signals/    # Signal generation
│   └── backtest/   # Backtesting engine
├── config/         # Configuration management
├── ui/             # Streamlit UI
│   ├── pages/      # Dashboard, Scanner, Analyzer, Backtest
│   └── components/ # Reusable UI components
└── utils/          # Logging, exceptions, validators
```

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the app
streamlit run app_v2.py

# Run tests
make test

# Code quality checks
make check
```

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key settings:
- `ENABLE_US_STOCK` / `ENABLE_HK_STOCK` / `ENABLE_A_STOCK` - Market toggles
- `SCORE_WEIGHT_*` - Scoring factor weights
- `OFF_ATR_PCT_THRESHOLD` - OFF filter ATR threshold
- `BACKTEST_HOLDING_DAYS` - Default holding period

## Development

```bash
make install      # Install dev dependencies
make test-unit    # Run unit tests
make test-cov     # Run with coverage
make lint         # Check code style
make format       # Auto-format code
make typecheck    # Type checking
make check        # All quality checks
```

## Migration from v1

The `src/compat.py` module provides a backward-compatible API:

```python
from src.compat import legacy

# Old-style API still works
df = legacy.fetch_daily("AAPL")
signal = legacy.get_signal("AAPL")
off_status = legacy.get_off_status(df)
```

## License

MIT
