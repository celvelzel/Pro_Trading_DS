"""
Settings API Router
Endpoints for reading and updating application settings.
"""

from fastapi import APIRouter, HTTPException
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from api.models.settings import (
    AppSettings,
    SettingsUpdateRequest,
    SettingsResponse,
    MarketSettings,
    DataSettings,
    ScoringWeights,
    BacktestSettings,
    OFFFilterSettings,
    IndicatorSettings,
)

router = APIRouter()


def _build_settings_from_lobster() -> AppSettings:
    """Build AppSettings from the lobster_quant Settings singleton."""
    from lobster_quant.src.config.settings import get_settings

    s = get_settings()
    return AppSettings(
        markets=MarketSettings(
            enableUS=s.enable_us_stock,
            enableHK=s.enable_hk_stock,
            enableA=s.enable_a_stock,
        ),
        data=DataSettings(
            dataYears=s.data_years,
            cacheTTL=s.data_cache_ttl,
        ),
        scoring=ScoringWeights(
            trend=s.score_weight_trend,
            momentum=s.score_weight_momentum,
            volume=s.score_weight_volume,
            pattern=s.score_weight_pattern,
        ),
        backtest=BacktestSettings(
            holdingDays=s.backtest_holding_days,
            minScore=s.backtest_min_score,
            lookbackDays=s.backtest_lookback_days,
            slippagePct=s.backtest_slippage_pct,
            commissionPct=s.backtest_commission_pct,
        ),
        offFilter=OFFFilterSettings(
            vixThreshold=s.off_vix_threshold,
            atrPctThreshold=s.off_atr_pct_threshold,
            gapThreshold=s.off_gap_threshold,
            minVolumeRatio=s.off_min_volume_ratio,
            ma200RecoveryDays=s.off_ma200_recovery_days,
        ),
        indicators=IndicatorSettings(
            maShortPeriod=s.ma_short_period,
            maLongPeriod=s.ma_long_period,
            rsiPeriod=s.rsi_period,
            atrPeriod=s.atr_period,
            macdFast=s.macd_fast,
            macdSlow=s.macd_slow,
            macdSignal=s.macd_signal,
            bbPeriod=s.bb_period,
            bbStd=s.bb_std,
        ),
        benchmarkSymbol=s.benchmark_symbol,
    )


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """
    Get current application settings.

    Returns:
        Complete application settings grouped by category.
    """
    try:
        settings = _build_settings_from_lobster()
        return SettingsResponse(settings=settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/", response_model=SettingsResponse)
async def update_settings(request: SettingsUpdateRequest):
    """
    Update application settings (partial update).

    Only provided fields will be updated. Nested objects are merged.

    Args:
        request: Partial settings update

    Returns:
        Updated application settings.
    """
    try:
        from lobster_quant.src.config.settings import get_settings

        s = get_settings()

        # Apply market settings
        if request.markets is not None:
            s.enable_us_stock = request.markets.enableUS
            s.enable_hk_stock = request.markets.enableHK
            s.enable_a_stock = request.markets.enableA

        # Apply data settings
        if request.data is not None:
            s.data_years = request.data.dataYears
            s.data_cache_ttl = request.data.cacheTTL

        # Apply scoring weights
        if request.scoring is not None:
            s.score_weight_trend = request.scoring.trend
            s.score_weight_momentum = request.scoring.momentum
            s.score_weight_volume = request.scoring.volume
            s.score_weight_pattern = request.scoring.pattern

        # Apply backtest settings
        if request.backtest is not None:
            s.backtest_holding_days = request.backtest.holdingDays
            s.backtest_min_score = request.backtest.minScore
            s.backtest_lookback_days = request.backtest.lookbackDays
            s.backtest_slippage_pct = request.backtest.slippagePct
            s.backtest_commission_pct = request.backtest.commissionPct

        # Apply OFF filter settings
        if request.offFilter is not None:
            s.off_vix_threshold = request.offFilter.vixThreshold
            s.off_atr_pct_threshold = request.offFilter.atrPctThreshold
            s.off_gap_threshold = request.offFilter.gapThreshold
            s.off_min_volume_ratio = request.offFilter.minVolumeRatio
            s.off_ma200_recovery_days = request.offFilter.ma200RecoveryDays

        # Apply indicator settings
        if request.indicators is not None:
            s.ma_short_period = request.indicators.maShortPeriod
            s.ma_long_period = request.indicators.maLongPeriod
            s.rsi_period = request.indicators.rsiPeriod
            s.atr_period = request.indicators.atrPeriod
            s.macd_fast = request.indicators.macdFast
            s.macd_slow = request.indicators.macdSlow
            s.macd_signal = request.indicators.macdSignal
            s.bb_period = request.indicators.bbPeriod
            s.bb_std = request.indicators.bbStd

        # Apply benchmark
        if request.benchmarkSymbol is not None:
            s.benchmark_symbol = request.benchmarkSymbol

        settings = _build_settings_from_lobster()
        return SettingsResponse(
            settings=settings,
            message="Settings updated successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", response_model=SettingsResponse)
async def reset_settings():
    """
    Reset all settings to defaults.

    Returns:
        Default application settings.
    """
    try:
        from lobster_quant.src.config.settings import reload_settings

        reload_settings()
        settings = _build_settings_from_lobster()
        return SettingsResponse(
            settings=settings,
            message="Settings reset to defaults",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
