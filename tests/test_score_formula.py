"""Check the published distance rule against src/score.py.

The score is a partial match on measured features, not a probability of mission success.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.score import (
    FEATURE_ORDER,
    TARGETS_MD,
    holdout_mask,
    load_weights,
    raw_distance,
    read_slope_band,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "data" / "processed" / "features.csv"
COLD_TARGET = 214.3
SLOPE_BAND = (8.0, 16.7)


def restated_distance(name: str, value: float) -> float:
    """The distance rule written in results/score-notes.md."""
    if name == "ndvi_median":
        return abs(value - 0.0)
    if name == "precip_median_mm_hr":
        return max(value - 0.0, 0.0)
    if name == "lst_night_median_k":
        return max(value - COLD_TARGET, 0.0)
    if name == "slope_median_deg":
        low, high = SLOPE_BAND
        return max(low - value, 0.0) + max(value - high, 0.0)
    raise AssertionError(name)


def code_distance(name: str, value: float) -> float:
    series = raw_distance(pd.Series([value]), name, COLD_TARGET, SLOPE_BAND)
    return float(series.iloc[0])


def test_restated_rule_agrees_with_score_py():
    samples = {
        "ndvi_median": [-0.032, -0.01995, 0.0, 0.00925, 0.8304],
        "precip_median_mm_hr": [-0.1, 0.0, 0.006, 0.008, 0.296],
        "lst_night_median_k": [200.0, 214.3, 252.94, 254.45, 258.8],
        "slope_median_deg": [0.0, 7.08, 8.0, 9.48, 12.3, 16.7, 20.0],
    }
    for name, values in samples.items():
        for value in values:
            assert code_distance(name, value) == pytest.approx(restated_distance(name, value))


def test_ndvi_distance_is_absolute_departure_from_zero():
    assert code_distance("ndvi_median", -0.032) == pytest.approx(0.032)
    assert code_distance("ndvi_median", 0.00925) == pytest.approx(0.00925)
    assert code_distance("ndvi_median", 0.0) == 0.0


def test_rain_distance_is_the_rate_above_zero():
    assert code_distance("precip_median_mm_hr", 0.006) == pytest.approx(0.006)
    assert code_distance("precip_median_mm_hr", 0.0) == 0.0
    assert code_distance("precip_median_mm_hr", -0.1) == 0.0


def test_night_temperature_distance_is_kelvin_above_214_3():
    assert code_distance("lst_night_median_k", 214.3) == 0.0
    assert code_distance("lst_night_median_k", 200.0) == 0.0
    assert code_distance("lst_night_median_k", 252.94) == pytest.approx(38.64)


def test_slope_distance_is_zero_inside_the_band_and_degrees_to_the_edge_outside():
    assert read_slope_band(TARGETS_MD.read_text(encoding="utf-8")) == SLOPE_BAND
    assert code_distance("slope_median_deg", 8.0) == 0.0
    assert code_distance("slope_median_deg", 12.3) == 0.0
    assert code_distance("slope_median_deg", 16.7) == 0.0
    assert code_distance("slope_median_deg", 7.08) == pytest.approx(0.92)
    assert code_distance("slope_median_deg", 20.0) == pytest.approx(3.3)


def test_rank1_worked_example_averages_to_0_162265():
    ndvi_gap = round(code_distance("ndvi_median", -0.032) / 0.8304, 6)
    rain_gap = round(code_distance("precip_median_mm_hr", 0.0) / 0.296, 6)
    temperature_gap = round(code_distance("lst_night_median_k", 252.94) / 86.2, 6)
    gaps = [ndvi_gap, rain_gap, temperature_gap]
    assert gaps == [0.038536, 0.0, 0.448260]
    assert round(sum(gaps) / 3, 6) == 0.162265


def test_equal_weights_divide_by_three():
    gaps = [0.038536, 0.0, 0.448260]
    weights = [1.0, 1.0, 1.0]
    weighted = sum(weight * gap for weight, gap in zip(weights, gaps, strict=True)) / sum(weights)
    assert len(gaps) == 3
    assert weighted == pytest.approx(sum(gaps) / 3)
    assert round(weighted, 6) == 0.162265


def test_published_site_scores_match_the_feature_table():
    if not FEATURES.is_file():
        pytest.skip("data/processed/features.csv is not on this machine")
    weights = load_weights()
    frame = pd.read_csv(FEATURES)
    assert float(frame["slope_median_deg"].isna().mean()) == 1.0
    active = [
        name
        for name in FEATURE_ORDER
        if name in weights["features"]
        and weights["features"][name] > 0
        and not frame[name].isna().all()
    ]
    assert active == ["ndvi_median", "precip_median_mm_hr", "lst_night_median_k"]
    cold_target = float(
        frame["lst_night_median_k"].quantile(weights["cold_tail_percentile"] / 100.0)
    )
    assert cold_target == pytest.approx(COLD_TARGET)
    scales = {}
    parts = []
    for name in active:
        distance = raw_distance(frame[name], name, cold_target, SLOPE_BAND)
        scale = float(distance.quantile(weights["distance_scale_percentile"] / 100.0))
        scales[name] = scale
        parts.append(distance / scale)
    score = sum(parts) / len(active)
    assert scales["ndvi_median"] == pytest.approx(0.8304)
    assert scales["precip_median_mm_hr"] == pytest.approx(0.296)
    assert scales["lst_night_median_k"] == pytest.approx(86.2)
    kunlun = frame[(frame["lat_center_deg"] == 35.3) & (frame["lon_center_deg"] == 81.1)]
    vinchina = frame[(frame["lat_center_deg"] == -27.9) & (frame["lon_center_deg"] == -68.9)]
    assert abs(float(score.loc[kunlun.index[0]]) - 0.186845) < 0.000001
    assert abs(float(score.loc[vinchina.index[0]]) - 0.167981) < 0.000001
    assert bool(holdout_mask(vinchina).iloc[0])
    assert not bool(holdout_mask(kunlun).iloc[0])
