"""
Lobster Quant - Risk Engine (OFF Filter)
Market condition assessment and risk management.
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
import numpy as np

from src.data.models import OFFStatus
from src.config.settings import get_settings
from src.utils.logging import get_logger
from src.utils.exceptions import OFFFilterError

logger = get_logger()


class RiskEngine:
    """Risk engine for market condition assessment.
    
    Implements OFF filter logic:
    - ATR% threshold (high volatility)
    - MA200 recovery (trend deterioration)
    - Gap analysis (extreme moves)
    - Benchmark risk (market-wide conditions)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.atr_threshold = self.settings.off_atr_pct_threshold
        self.gap_threshold = self.settings.off_gap_threshold
        self.min_volume_ratio = self.settings.off_min_volume_ratio
        self.ma200_recovery_days = self.settings.off_ma200_recovery_days
    
    def assess(self, 
               data: pd.DataFrame, 
               benchmark_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Assess market conditions and generate OFF status.
        
        Args:
            data: Stock OHLCV data with indicators
            benchmark_data: Benchmark OHLCV data (e.g., SPY)
        
        Returns:
            DataFrame with OFF status columns
        """
        if len(data) < 60:
            logger.warning("Insufficient data for OFF filter assessment")
            return pd.DataFrame(index=data.index)
        
        results = pd.DataFrame(index=data.index)
        results['is_off'] = False
        
        # Individual checks
        checks = self._run_checks(data, benchmark_data)
        
        for check_name, check_series in checks.items():
            results[check_name] = check_series
            results['is_off'] |= check_series
        
        return results
    
    def _run_checks(self, 
                    data: pd.DataFrame, 
                    benchmark_data: Optional[pd.DataFrame]) -> Dict[str, pd.Series]:
        """Run individual risk checks."""
        checks = {}
        
        # 1. ATR% check
        if 'atr_pct' in data.columns:
            atr_pct = pd.to_numeric(data['atr_pct'], errors='coerce')
            checks['ATR过高'] = atr_pct > self.atr_threshold
        
        # 2. MA200 recovery check
        if 'ma200' in data.columns and 'close' in data.columns:
            close = pd.to_numeric(data['close'], errors='coerce')
            ma200 = pd.to_numeric(data['ma200'], errors='coerce')
            below_ma200 = close < ma200
            ma200_falling = ma200.diff() < 0
            checks['MA200恢复'] = below_ma200 & ma200_falling
        
        # 3. Gap check
        if 'open' in data.columns and 'close' in data.columns:
            close = pd.to_numeric(data['close'], errors='coerce')
            open_price = pd.to_numeric(data['open'], errors='coerce')
            prev_close = close.shift(1)
            gap = (open_price - prev_close) / prev_close
            gap_std = gap.rolling(window=60).std()
            checks['Gap过大'] = gap.abs() > 2.0 * gap_std
        
        # 4. Benchmark risk
        if benchmark_data is not None and len(benchmark_data) > 20:
            bench_risk = self._assess_benchmark_risk(benchmark_data)
            if bench_risk is not None:
                checks['大盘风险'] = bench_risk.reindex(data.index, method='ffill').fillna(False)
        
        # 5. Volume check
        if 'volume_ratio' in data.columns:
            volume_ratio = pd.to_numeric(data['volume_ratio'], errors='coerce')
            checks['流动性不足'] = volume_ratio < self.min_volume_ratio
        
        return checks
    
    def _assess_benchmark_risk(self, benchmark_data: pd.DataFrame) -> Optional[pd.Series]:
        """Assess benchmark (e.g., SPY) risk."""
        try:
            df = benchmark_data.copy()
            close = pd.to_numeric(df['close'], errors='coerce')
            # Defensive: compute ma20 if not provided by IndicatorEngine
            if 'ma20' not in df.columns:
                df['ma20'] = close.rolling(window=20).mean()
            ma20 = pd.to_numeric(df['ma20'], errors='coerce')
            bench_slope = ma20.diff()
            return bench_slope < 0
        except Exception as e:
            logger.warning(f"Benchmark risk assessment failed: {e}")
            return None
    
    def get_stats(self, 
                  data: pd.DataFrame, 
                  off_results: pd.DataFrame) -> Dict[str, Any]:
        """Calculate ON/OFF statistics.
        
        Args:
            data: Original data
            off_results: OFF filter results
        
        Returns:
            Statistics dictionary
        """
        total = len(off_results)
        off_days = off_results['is_off'].sum()
        
        stats = {
            'total_days': int(total),
            'off_days': int(off_days),
            'on_days': int(total - off_days),
            'on_pct': (total - off_days) / total * 100 if total > 0 else 0,
            'off_pct': off_days / total * 100 if total > 0 else 0,
            'reasons': {}
        }
        
        # Reason distribution
        off_mask = off_results['is_off']
        for col in off_results.columns:
            if col == 'is_off':
                continue
            count = int((off_results[col] & off_mask).sum())
            if count > 0:
                stats['reasons'][col] = count
        
        return stats
    
    def get_latest_status(self, 
                          data: pd.DataFrame, 
                          benchmark_data: Optional[pd.DataFrame] = None) -> OFFStatus:
        """Get latest OFF status.
        
        Args:
            data: Stock data
            benchmark_data: Benchmark data
        
        Returns:
            OFFStatus for the most recent day
        """
        results = self.assess(data, benchmark_data)
        
        if results.empty:
            return OFFStatus(
                timestamp=datetime.now(),
                is_off=False,
                reasons=["Insufficient data"]
            )
        
        latest = results.iloc[-1]
        reasons = []
        
        for col in results.columns:
            if col == 'is_off':
                continue
            if latest.get(col, False):
                reasons.append(col)
        
        return OFFStatus(
            timestamp=data.index[-1] if hasattr(data.index[-1], 'isoformat') else datetime.now(),
            is_off=latest.get('is_off', False),
            reasons=reasons
        )
    
    def should_trade(self, 
                     data: pd.DataFrame, 
                     benchmark_data: Optional[pd.DataFrame] = None) -> Tuple[bool, List[str]]:
        """Quick check if trading should be allowed.
        
        Args:
            data: Stock data
            benchmark_data: Benchmark data
        
        Returns:
            (should_trade, reasons_list)
        """
        status = self.get_latest_status(data, benchmark_data)
        return status.is_on, status.reasons


# Global risk engine instance
_risk_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    """Get global risk engine instance (singleton)."""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine

