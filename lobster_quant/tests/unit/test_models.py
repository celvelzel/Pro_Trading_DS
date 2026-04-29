"""
Tests for data models.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from data.models import (
    OHLCV,
    StockData,
    SignalResult,
    OFFStatus,
    Trade,
    BacktestResult,
    MarketSnapshot,
)


class TestOHLCV:
    def test_basic_creation(self):
        candle = OHLCV(
            timestamp=datetime.now(),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000
        )
        assert candle.close == 103.0
        assert candle.is_bullish is True
        assert candle.range == 7.0
    
    def test_bearish_candle(self):
        candle = OHLCV(
            timestamp=datetime.now(),
            open=100.0,
            high=102.0,
            low=95.0,
            close=97.0,
            volume=500000
        )
        assert candle.is_bullish is False


class TestStockData:
    def test_creation_with_dataframe(self):
        dates = pd.date_range('2024-01-01', periods=10)
        df = pd.DataFrame({
            'open': [100] * 10,
            'high': [105] * 10,
            'low': [95] * 10,
            'close': [102] * 10,
            'volume': [1000000] * 10
        }, index=dates)
        
        stock = StockData(
            symbol="AAPL",
            daily=df,
            source="test"
        )
        
        assert stock.symbol == "AAPL"
        assert stock.get_latest_price() == 102.0
        assert len(stock.daily) == 10


class TestSignalResult:
    def test_bullish_signal(self):
        signal = SignalResult(
            symbol="AAPL",
            signal_type="强烈推荐",
            score=85.0,
            probability_up=75.0,
            reasons=["Trend up", "Volume high"]
        )
        assert signal.is_bullish is True
        assert signal.strength == "强"
    
    def test_neutral_signal(self):
        signal = SignalResult(
            symbol="AAPL",
            signal_type="观望",
            score=25.0,
            probability_up=40.0
        )
        assert signal.is_bullish is False
        assert signal.strength == "无"


class TestOFFStatus:
    def test_on_status(self):
        status = OFFStatus(
            timestamp=datetime.now(),
            is_off=False,
            reasons=[]
        )
        assert status.is_on is True
        assert status.status_text == "ON"
        assert status.status_emoji == "✅"
    
    def test_off_status(self):
        status = OFFStatus(
            timestamp=datetime.now(),
            is_off=True,
            reasons=["ATR过高", "大盘风险"]
        )
        assert status.is_on is False
        assert status.status_text == "OFF"
        assert status.status_emoji == "❌"


class TestTrade:
    def test_open_trade(self):
        trade = Trade(
            symbol="AAPL",
            buy_date=datetime.now(),
            buy_price=100.0
        )
        assert trade.is_closed is False
        assert trade.pnl is None
    
    def test_closed_trade(self):
        trade = Trade(
            symbol="AAPL",
            buy_date=datetime.now(),
            buy_price=100.0,
            sell_date=datetime.now(),
            sell_price=110.0,
            return_pct=0.10
        )
        assert trade.is_closed is True
        assert trade.pnl == 0.10


class TestBacktestResult:
    def test_empty_result(self):
        result = BacktestResult(symbol="AAPL")
        assert result.total_trades == 0
        assert result.win_rate == 0.0
    
    def test_with_trades(self):
        trades = [
            Trade(
                symbol="AAPL",
                buy_date=datetime.now(),
                buy_price=100.0,
                sell_date=datetime.now(),
                sell_price=110.0,
                return_pct=0.10
            ),
            Trade(
                symbol="AAPL",
                buy_date=datetime.now(),
                buy_price=100.0,
                sell_date=datetime.now(),
                sell_price=95.0,
                return_pct=-0.05
            )
        ]
        result = BacktestResult(symbol="AAPL", trades=trades)
        assert result.total_trades == 2
        assert result.winning_trades == 1
        assert result.losing_trades == 1


class TestMarketSnapshot:
    def test_trend_direction(self):
        snapshot = MarketSnapshot(
            code="AAPL",
            price=150.0,
            score=75.0,
            slope_daily=0.05,
            slope_weekly=0.03,
            slope_monthly=0.02
        )
        assert snapshot.trend_direction == "strong_up"
    
    def test_down_trend(self):
        snapshot = MarketSnapshot(
            code="AAPL",
            price=150.0,
            score=30.0,
            slope_daily=-0.05,
            slope_weekly=-0.03
        )
        assert snapshot.trend_direction == "strong_down"
