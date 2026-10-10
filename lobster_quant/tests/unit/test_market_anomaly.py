import pytest
from lobster_quant.src.analysis.market_anomaly import calculate_market_anomaly


def test_hand_calculated_prior_volume_and_same_date_benchmark():
    dates = [f"2026-09-{i:02}" for i in range(1, 22)]
    result = calculate_market_anomaly(dates, [100.] * 20 + [110.], [10.] * 20 + [30.], dates[-2:], [100., 105.])
    assert result["return_pct"] == pytest.approx(10)
    assert result["volume_ratio_20"] == 3
    assert result["excess_return_pct"] == pytest.approx(5)
    assert result["relative_strength"] == pytest.approx(1.1 / 1.05 - 1)


def test_missing_date_does_not_compare_ordinal_benchmark():
    result = calculate_market_anomaly(["a", "b"], [100, 90], [1, 1], ["b", "c"], [100, 110])
    assert result["excess_return_pct"] is None


def test_zero_prior_volume_and_short_history():
    result = calculate_market_anomaly([str(i).zfill(2) for i in range(21)], [1.] * 21, [0.] * 20 + [1.])
    assert result["volume_ratio_20"] is None
    assert calculate_market_anomaly([], [], [])["return_pct"] is None


@pytest.mark.parametrize("closes,volumes", [([0, 1], [1, 1]), ([float('nan'), 1], [1, 1]), ([1, 1], [-1, 1]), ([float('inf'), 1], [1, 1])])
def test_invalid_numbers(closes, volumes):
    with pytest.raises(ValueError):
        calculate_market_anomaly(["a", "b"], closes, volumes)


def test_duplicate_or_unsorted_dates():
    for dates in (["a", "a"], ["b", "a"]):
        with pytest.raises(ValueError):
            calculate_market_anomaly(dates, [1, 1], [1, 1])
