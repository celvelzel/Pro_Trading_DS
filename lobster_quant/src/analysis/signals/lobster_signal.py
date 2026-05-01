"""
Lobster Quant - Lobster Signal Generator
Multi-factor scoring and signal generation.
"""

from typing import Tuple, List
from datetime import datetime
import pandas as pd
import numpy as np

from src.data.models import SignalResult
from src.config.settings import get_settings
from src.utils.logging import get_logger
from ..indicators.base import rolling_slope

logger = get_logger()


class SignalGenerator:
    """Multi-factor signal generator.
    
    Generates trading signals based on:
    - Trend strength (MA slopes)
    - Momentum (RSI, ROC)
    - Volume confirmation
    - Technical patterns (MACD, MA alignment)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.weights = self.settings.scoring_weights
    
    def calculate_score(self, data: pd.DataFrame) -> float:
        """Calculate composite score (0-100).
        
        Args:
            data: DataFrame with computed indicators
        
        Returns:
            Score from 0 to 100
        """
        if len(data) < 50:
            return 0.0
        
        latest = data.iloc[-1]
        
        # 1. Trend Score (40%)
        trend_score = self._calc_trend_score(data, latest)
        
        # 2. Momentum Score (20%)
        momentum_score = self._calc_momentum_score(data, latest)
        
        # 3. Volume Score (15%)
        volume_score = self._calc_volume_score(data, latest)
        
        # 4. Pattern Score (25%)
        pattern_score = self._calc_pattern_score(data, latest)
        
        # Weighted total
        total = (
            trend_score * self.weights['trend'] +
            momentum_score * self.weights['momentum'] +
            volume_score * self.weights['volume'] +
            pattern_score * self.weights['pattern']
        )
        
        return round(min(100, max(0, total)), 2)
    
    def _calc_trend_score(self, data: pd.DataFrame, latest: pd.Series) -> float:
        """Calculate trend strength score (0-100)."""
        score = 50.0  # Neutral
        
        # Daily slope
        if 'slope_daily' in data.columns:
            slope = pd.to_numeric(latest.get('slope_daily', 0), errors='coerce')
            if pd.isna(slope):
                slope = 0
            # Normalize slope: typical range -0.03 to +0.03
            slope_score = min(100, max(0, (slope + 0.03) / 0.06 * 100))
            score = slope_score
        
        # Weekly slope confirmation
        if 'slope_weekly' in data.columns:
            w_slope = pd.to_numeric(latest.get('slope_weekly', 0), errors='coerce')
            if pd.notna(w_slope):
                if w_slope > 0 and score > 50:
                    score = min(100, score + 10)
                elif w_slope < 0 and score < 50:
                    score = max(0, score - 10)
        
        # Monthly slope confirmation
        if 'slope_monthly' in data.columns:
            m_slope = pd.to_numeric(latest.get('slope_monthly', 0), errors='coerce')
            if pd.notna(m_slope):
                if m_slope > 0 and score > 50:
                    score = min(100, score + 10)
                elif m_slope < 0 and score < 50:
                    score = max(0, score - 10)
        
        return score
    
    def _calc_momentum_score(self, data: pd.DataFrame, latest: pd.Series) -> float:
        """Calculate momentum score (0-100)."""
        score = 50.0
        
        # RSI
        if 'rsi' in data.columns:
            rsi = pd.to_numeric(latest.get('rsi', 50), errors='coerce')
            if pd.isna(rsi):
                rsi = 50
            
            # RSI 30-70 is neutral zone
            if rsi < 30:
                score = 80  # Oversold = potential bounce
            elif rsi < 50:
                score = 50 + (50 - rsi) * 0.6
            elif rsi < 70:
                score = 50 - (rsi - 50) * 0.6
            else:
                score = 20  # Overbought = caution
        
        # 20-day return
        if len(data) >= 21:
            close_last = pd.to_numeric(data['close'].iloc[-1], errors='coerce')
            close_prev = pd.to_numeric(data['close'].iloc[-21], errors='coerce')
            if pd.notna(close_last) and pd.notna(close_prev) and close_prev != 0:
                ret_20d = (close_last / close_prev - 1) * 100
                if ret_20d > 10:
                    score = min(100, score + 15)
                elif ret_20d > 0:
                    score = min(100, score + ret_20d * 0.5)
                elif ret_20d > -10:
                    score = max(0, score + ret_20d * 0.5)
                else:
                    score = max(0, score - 15)
        
        return score
    
    def _calc_volume_score(self, data: pd.DataFrame, latest: pd.Series) -> float:
        """Calculate volume confirmation score (0-100)."""
        score = 50.0
        
        if 'volume_ratio' in data.columns:
            vr = pd.to_numeric(latest.get('volume_ratio', 1.0), errors='coerce')
            if pd.isna(vr):
                vr = 1.0
            
            if vr > 2.0:
                score = 90  # Very high volume
            elif vr > 1.5:
                score = 75  # High volume
            elif vr > 1.0:
                score = 60  # Above average
            elif vr > 0.8:
                score = 50  # Normal
            elif vr > 0.5:
                score = 35  # Low volume
            else:
                score = 20  # Very low volume
        
        return score
    
    def _calc_pattern_score(self, data: pd.DataFrame, latest: pd.Series) -> float:
        """Calculate technical pattern score (0-100)."""
        score = 0.0
        
        # MACD golden cross
        if 'macd_golden' in data.columns:
            if latest.get('macd_golden', False):
                score += 25
        
        # MA bullish alignment
        if 'ma_bullish' in data.columns:
            if latest.get('ma_bullish', False):
                score += 25
        
        # Price above BB mid
        if 'bb_position' in data.columns:
            bb_pos = pd.to_numeric(latest.get('bb_position', 0.5), errors='coerce')
            if pd.isna(bb_pos):
                bb_pos = 0.5
            if bb_pos > 0.5:
                score += 25
            elif bb_pos > 0.3:
                score += 15
        
        # Price above MA20
        if 'ma20' in data.columns:
            close_val = pd.to_numeric(latest.get('close', 0), errors='coerce')
            ma20_val = pd.to_numeric(latest.get('ma20', 0), errors='coerce')
            if pd.notna(close_val) and pd.notna(ma20_val) and close_val > ma20_val:
                score += 25
        
        return min(100, score)
    
    def calculate_probability_up(self, data: pd.DataFrame) -> float:
        """Calculate probability of price going up.
        
        Args:
            data: DataFrame with indicators
        
        Returns:
            Probability 0-100
        """
        if len(data) < 50:
            return 50.0
        
        score = self.calculate_score(data)
        
        # Map score to probability
        # Score 0-30: probability 20-40
        # Score 30-70: probability 40-60
        # Score 70-100: probability 60-90
        if score < 30:
            prob = 20 + score * (20/30)
        elif score < 70:
            prob = 40 + (score - 30) * (20/40)
        else:
            prob = 60 + (score - 70) * (30/30)
        
        return round(min(100, max(0, prob)), 1)
    
    def generate_signal(self, data: pd.DataFrame) -> SignalResult:
        """Generate complete trading signal.
        
        Args:
            data: DataFrame with computed indicators
        
        Returns:
            SignalResult with signal type, score, and reasons
        """
        score = self.calculate_score(data)
        prob_up = self.calculate_probability_up(data)
        
        latest = data.iloc[-1]
        reasons = self._generate_reasons(data, latest, score)
        
        # Determine signal type
        if score >= 70 and prob_up >= 60:
            signal_type = "强烈推荐"
        elif score >= 50 and prob_up >= 50:
            signal_type = "推荐"
        elif score >= 30:
            signal_type = "持有"
        else:
            signal_type = "观望"
        
        return SignalResult(
            symbol="",  # Will be set by caller
            signal_type=signal_type,
            score=score,
            probability_up=prob_up,
            reasons=reasons
        )
    
    def _generate_reasons(self, data: pd.DataFrame, latest: pd.Series, score: float) -> List[str]:
        """Generate human-readable reasons for the signal."""
        reasons = []
        
        # Trend reasons
        if 'slope_daily' in data.columns:
            slope = pd.to_numeric(latest.get('slope_daily', 0), errors='coerce')
            if pd.notna(slope):
                if slope > 0.01:
                    reasons.append(f"日线趋势向上 (斜率: {slope:.4f})")
                elif slope < -0.01:
                    reasons.append(f"日线趋势向下 (斜率: {slope:.4f})")
        
        if 'slope_weekly' in data.columns:
            w_slope = pd.to_numeric(latest.get('slope_weekly', 0), errors='coerce')
            if pd.notna(w_slope):
                if w_slope > 0:
                    reasons.append("周线趋势向上")
                elif w_slope < 0:
                    reasons.append("周线趋势向下")
        
        # Momentum reasons
        if 'rsi' in data.columns:
            rsi = pd.to_numeric(latest.get('rsi', 50), errors='coerce')
            if pd.notna(rsi):
                if rsi < 30:
                    reasons.append(f"RSI超卖 ({rsi:.1f})")
                elif rsi > 70:
                    reasons.append(f"RSI超买 ({rsi:.1f})")
        
        # Volume reasons
        if 'volume_ratio' in data.columns:
            vr = pd.to_numeric(latest.get('volume_ratio', 1.0), errors='coerce')
            if pd.notna(vr):
                if vr > 1.5:
                    reasons.append(f"成交量放大({vr:.1f}x)")
                elif vr < 0.5:
                    reasons.append(f"成交量萎缩({vr:.1f}x)")
        
        # Pattern reasons
        if 'macd_golden' in data.columns and latest.get('macd_golden', False):
            reasons.append("MACD金叉")
        
        if 'ma_bullish' in data.columns and latest.get('ma_bullish', False):
            reasons.append("MA多头排列")
        
        if score < 30:
            reasons.append("综合评分偏低")
        elif score > 70:
            reasons.append("综合评分优秀")
        
        return reasons

