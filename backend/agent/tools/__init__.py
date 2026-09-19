"""Typed, auditable tools exposed to the Agent."""

from .registry import ToolRegistry, ToolSpec, default_registry

# Import built-in adapters once so their versioned specs are registered.
from . import indicators as _indicators  # noqa: F401,E402
from . import market as _market  # noqa: F401,E402
from . import risk as _risk  # noqa: F401,E402
from . import backtest as _backtest  # noqa: F401,E402
from . import knowledge as _knowledge  # noqa: F401,E402

__all__ = ["ToolRegistry", "ToolSpec", "default_registry"]
