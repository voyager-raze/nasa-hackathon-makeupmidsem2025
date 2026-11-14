"""Check the published distance rule against src/score.py.

The score is a partial match on measured features, not a probability of mission success.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np
import pytest
import h5py
from pyhdf.SD import SD, SDC

from src.score import (
    FEATURE_ORDER,
    TARGETS_MD,
    holdout_mask,
    eligible_mask,
    load_weights,
    raw_distance,
    read_slope_band,
)
from src.build_features import apply_modis_scale, block_median
from src.export_map_data import rejected_center

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "data" / "processed" / "features.csv"
MAP_HTML = ROOT / "web" / "index.html"
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


def test_modis_scale_rejects_fill_and_out_of_range_before_scaling():
    raw = pd.Series([-3000, -2001, -2000, 0, 10000, 10001], dtype="int16").to_numpy()
    attrs = {"_FillValue": -3000, "valid_range": [-2000, 10000], "scale_factor": 10000, "units": "NDVI"}
    physical, _ = apply_modis_scale(raw, attrs, "ndvi")
    assert pd.isna(physical[0])
    assert pd.isna(physical[1])
    assert physical[2] == pytest.approx(-0.2)
    assert physical[3] == 0.0
    assert physical[4] == pytest.approx(1.0)
    assert pd.isna(physical[5])


def test_block_median_keeps_missing_values_missing_and_counts_only_finite_pixels():
    values = np.array([[1.0, float("nan")], [3.0, 5.0]])
    medians, counts = block_median(values, 2)
    assert medians[0, 0] == pytest.approx(3.0)
    assert counts[0, 0] == 3
    all_missing, missing_counts = block_median(
        np.full((2, 2), float("nan")), 2
    )
    assert pd.isna(all_missing[0, 0])
    assert missing_counts[0, 0] == 0


def test_june_site_measurements_match_independent_raw_granule_windows():
    """Re-read each site window directly from original HDF granules."""
    raw = ROOT / "data" / "raw"
    ndvi_path = raw / "MOD13C2.A2024153.061.2024198104950.hdf"
    lst_path = raw / "MOD11C3.A2024153.061.2024187024328.hdf"
    imerg_path = raw / "3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5"
    if not all(path.is_file() for path in (ndvi_path, lst_path, imerg_path)):
        pytest.skip("Original June 2024 granules are unavailable")

    features = pd.read_csv(FEATURES)
    sites = [("Kunlun", 35.3, 81.1), ("Vinchina", -27.9, -68.9)]

    def modis_window(dataset_name: str, lat: float, lon: float) -> tuple[np.ndarray, dict]:
        row = round((90.0 - (lat + 0.1)) / 0.05)
        col = round((lon - 0.1 + 180.0) / 0.05)
        hdf = SD(str(ndvi_path if dataset_name.startswith("CMG") else lst_path), SDC.READ)
        try:
            ds = hdf.select(dataset_name)
            return np.array(ds.get()[row:row + 4, col:col + 4]), dict(ds.attributes())
        finally:
            hdf.end()

    def modis_physical(raw_values: np.ndarray, attrs: dict, divide: bool) -> np.ndarray:
        values = raw_values.astype(float)
        low, high = map(float, attrs["valid_range"])
        values[(raw_values == attrs["_FillValue"]) | (raw_values < low) | (raw_values > high)] = np.nan
        return values / float(attrs["scale_factor"]) if divide else values * float(attrs["scale_factor"])

    with h5py.File(imerg_path, "r") as imerg:
        rain = imerg["Grid/precipitation"]
        rain_fill = float(rain.attrs["_FillValue"])

        for site, lat, lon in sites:
            feature = features.loc[
                (features["lat_center_deg"] == lat) & (features["lon_center_deg"] == lon)
            ].iloc[0]
            ndvi_raw, ndvi_attrs = modis_window("CMG 0.05 Deg Monthly NDVI", lat, lon)
            ndvi = modis_physical(ndvi_raw, ndvi_attrs, divide=True)
            assert int(np.isfinite(ndvi).sum()) == int(feature["ndvi_valid_count"]) == 16
            assert float(np.nanmedian(ndvi)) == pytest.approx(float(feature["ndvi_median"]), abs=1e-9), site

            night_raw, night_attrs = modis_window("LST_Night_CMG", lat, lon)
            night = modis_physical(night_raw, night_attrs, divide=False)
            assert int(np.isfinite(night).sum()) == int(feature["lst_night_valid_count"]) == 16
            assert float(np.nanmedian(night)) == pytest.approx(float(feature["lst_night_median_k"]), abs=1e-9), site

            day_raw, day_attrs = modis_window("LST_Day_CMG", lat, lon)
            day = modis_physical(day_raw, day_attrs, divide=False)
            assert int(np.isfinite(day).sum()) == int(feature["lst_day_valid_count"]) == 16
            assert float(np.nanmedian(day)) == pytest.approx(float(feature["lst_day_median_k"]), abs=1e-9), site
            paired = np.isfinite(day) & np.isfinite(night)
            day_night = day[paired] - night[paired]
            assert int(paired.sum()) == int(feature["lst_day_night_range_valid_count"]) == 16
            assert float(np.median(day_night)) == pytest.approx(
                float(feature["lst_day_night_range_median_k"]), abs=1e-9
            ), site

            north_row = round((90.0 - (lat + 0.1)) / 0.1)
            west_col = round((lon - 0.1 + 180.0) / 0.1)
            south_row_in_source = 1800 - (north_row + 2)
            rain_window = np.array(rain[0, west_col:west_col + 2, south_row_in_source:south_row_in_source + 2], dtype=float)
            rain_window[np.isclose(rain_window, rain_fill) | (rain_window < -9000)] = np.nan
            assert int(np.isfinite(rain_window).sum()) == int(feature["precip_valid_count"]) == 4
            assert float(np.nanmedian(rain_window)) == pytest.approx(float(feature["precip_median_mm_hr"]), abs=1e-9), site


def test_eligibility_fails_closed_when_any_active_feature_is_missing():
    frame = pd.DataFrame({"ndvi_median": [0.1, 0.2], "precip_median_mm_hr": [0.0, float("nan")]})
    assert eligible_mask(frame, ["ndvi_median", "precip_median_mm_hr"]).tolist() == [True, False]
    assert eligible_mask(frame, []).tolist() == [False, False]


def test_greenland_cluster_exclusion_is_separate_from_atacama_holdout():
    named_ice_cells = [(73.5, -40.5), (73.5, -40.7), (73.9, -40.1), (73.5, -40.9), (74.1, -39.9)]
    for lat, lon in named_ice_cells:
        assert rejected_center(lat, lon)
    # The four edge checks and broad August context support the documented
    # cluster box; a nearby cell outside it stays eligible for discovery.
    assert rejected_center(74.0, -39.0)
    assert not rejected_center(74.0, -28.7)
    assert not rejected_center(-27.9, -68.9)
    assert bool(holdout_mask(pd.DataFrame({"lat_center_deg": [-27.9], "lon_center_deg": [-68.9]})).iloc[0])


def test_rank_ties_resolve_by_latitude_then_longitude():
    tied = pd.DataFrame(
        {"score": [0.2, 0.1, 0.1, 0.1], "lat_center_deg": [0.0, 1.0, -1.0, -1.0], "lon_center_deg": [0.0, 1.0, 2.0, -2.0]}
    )
    ranked = tied.sort_values(
        ["score", "lat_center_deg", "lon_center_deg"],
        ascending=[True, True, True],
        kind="mergesort",
    )
    assert list(ranked.index) == [3, 2, 1, 0]


def test_generated_dashboard_keeps_targets_gaps_and_custom_weights_visible():
    page = MAP_HTML.read_text(encoding="utf-8")
    for required in (
        "Moon target",
        "Mars target · ground ice",
        "Target reference · Earth status",
        "No comparable target value",
        "valid pixels",
        "MOD11 quality flags were not additional filters",
        "Moon and Mars targets remain fixed",
        "candidate mission success: <strong>not calibrated</strong>",
        "historical mobility reference: curiosity drive completion",
        "95% wilson interval",
        "evidence grade: <strong>low</strong>",
        "Physical limits:",
        "Customize score",
        "Reset defaults",
        "../results/score-notes.md",
        "../notes/data-log.md",
        "../notes/credibility.md",
        "@media (min-width: 981px)",
    ):
        assert required in page
    assert "confidence %" not in page.lower()
