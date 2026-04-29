"""
pytest configuration and shared fixtures.
"""

import pytest
import sys
import os

# Add parent (lobster_quant/) to path so we can import from src.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set test environment
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
