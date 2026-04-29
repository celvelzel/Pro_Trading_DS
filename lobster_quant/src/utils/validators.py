"""
Lobster Quant - Data Validators
Universal validation utilities for stock data, symbols, dates, and DataFrames.
"""

import re
import pandas as pd
from datetime import date, datetime
from typing import Optional

from .exceptions import ValidationError


def validate_symbol(symbol: str) -> str:
    """Validate and normalize stock symbol.
    
    Validates that the symbol contains only alphanumeric characters,
    dots, and hyphens. Strips whitespace and converts to uppercase.
    
    Args:
        symbol: Raw stock symbol string
        
    Returns:
        Uppercase, stripped symbol
        
    Raises:
        ValidationError: If symbol is empty or contains invalid characters
    """
    if not symbol:
        raise ValidationError("Symbol cannot be empty")
    
    # Strip whitespace
    symbol = symbol.strip()
    
    if not symbol:
        raise ValidationError("Symbol cannot be empty after stripping whitespace")
    
    # Check valid characters: alphanumeric, dots, hyphens
    if not re.match(r'^[A-Za-z0-9.-]+$', symbol):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Only alphanumeric characters, dots, and hyphens allowed"
        )
    
    return symbol.upper()


def validate_date_range(
    start: date,
    end: date,
    max_years: int = 10
) -> tuple[date, date]:
    """Validate date range for data fetching.
    
    Ensures start date is before end date, and the range
    does not exceed the maximum allowed years.
    
    Args:
        start: Start date
        end: End date
        max_years: Maximum years allowed (default 10)
        
    Returns:
        Tuple of (start, end) dates
        
    Raises:
        ValidationError: If dates are invalid or range exceeds max_years
    """
    if start is None or end is None:
        raise ValidationError("Start and end dates must be provided")
    
    if start > end:
        raise ValidationError(
            f"Start date {start} must be before end date {end}"
        )
    
    # Calculate years difference
    delta = end.year - start.year
    if delta > max_years:
        raise ValidationError(
            f"Date range {delta} years exceeds maximum {max_years} years"
        )
    
    # Check for future dates
    today = date.today()
    if start > today:
        raise ValidationError(f"Start date {start} cannot be in the future")
    if end > today:
        raise ValidationError(f"End date {end} cannot be in the future")
    
    return (start, end)


def validate_dataframe_columns(
    df: pd.DataFrame,
    required_columns: list[str],
    name: str = "DataFrame"
) -> bool:
    """Validate that DataFrame contains all required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        name: Name of the DataFrame for error messages
        
    Returns:
        True if all columns present
        
    Raises:
        ValidationError: If any required columns are missing
    """
    if df is None:
        raise ValidationError(f"{name} cannot be None")
    
    if not isinstance(df, pd.DataFrame):
        raise ValidationError(f"{name} must be a pandas DataFrame")
    
    missing = [col for col in required_columns if col not in df.columns]
    
    if missing:
        raise ValidationError(
            f"{name} missing required columns: {missing}",
            details={"missing_columns": missing}
        )
    
    return True


def validate_timeframe(timeframe: str) -> str:
    """Validate timeframe string.
    
    Validates that the timeframe is one of the allowed values:
    daily, weekly, or monthly.
    
    Args:
        timeframe: Timeframe string
        
    Returns:
        Lowercase normalized timeframe
        
    Raises:
        ValidationError: If timeframe is invalid
    """
    if not timeframe:
        raise ValidationError("Timeframe cannot be empty")
    
    # Normalize
    timeframe = timeframe.strip().lower()
    
    valid_timeframes = ["daily", "weekly", "monthly"]
    
    if timeframe not in valid_timeframes:
        raise ValidationError(
            f"Invalid timeframe: '{timeframe}'. "
            f"Must be one of: {valid_timeframes}"
        )
    
    return timeframe