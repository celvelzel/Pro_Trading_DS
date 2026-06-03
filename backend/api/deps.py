"""
FastAPI dependency providers for engine singletons.

Eliminates per-request lazy imports by returning pre-warmed instances
that were created during application startup (lifespan).
"""

from lobster_quant.src.core.data_engine import get_data_engine
from lobster_quant.src.core.indicator_engine import get_indicator_engine


def get_data_engine_dep():
    """FastAPI dependency: returns the singleton DataEngine instance."""
    return get_data_engine()


def get_indicator_engine_dep():
    """FastAPI dependency: returns the singleton IndicatorEngine instance."""
    return get_indicator_engine()
