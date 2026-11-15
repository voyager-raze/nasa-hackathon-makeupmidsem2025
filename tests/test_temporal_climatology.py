from __future__ import annotations

import calendar
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import build_features, build_monthly_range, score as score_module
from src import score_climatology as climatology_scorer
from src.build_climatology import build_climatology, input_path
from src.score_climatology import build_scores


MONTHLY_COLUMNS = (
    "lat_center_deg",
    "lon_center_deg",
    "ndvi_median",
    "ndvi_valid_count",
    "precip_median_mm_hr",
    "precip_valid_count",
    "lst_night_median_k",
    "lst_night_valid_count",
)


def write_synthetic_months(root: Path, years: range) -> None:
    for year in years:
        for month in range(1, 13):
            year_offset = year - years.start
            ndvi_second = np.nan if month <= 3 else 0.2 + year_offset * 0.1
            table = pd.DataFrame(
                {
                    "lat_center_deg": [0.0, 10.0],
                    "lon_center_deg": [0.0, 10.0],
                    "ndvi_median": [month / 100 + year_offset * 0.1, ndvi_second],
                    "ndvi_valid_count": [16, 0 if np.isnan(ndvi_second) else 16],
                    "precip_median_mm_hr": [
                        month / 1000 + year_offset * 0.01,
                        0.1 + year_offset * 0.01,
                    ],
                    "precip_valid_count": [4, 4],
                    "lst_night_median_k": [
                        200.0 + month + year_offset,
                        220.0 + month + year_offset,
                    ],
                    "lst_night_valid_count": [16, 16],
                },
                columns=MONTHLY_COLUMNS,
            )
            path = input_path(year, month, root)
            path.parent.mkdir(parents=True, exist_ok=True)
            table.to_csv(path, index=False, compression="gzip")
            write_month_manifest(path, year, month)


def write_month_manifest(path: Path, year: int, month: int) -> None:
    manifest_path = path.parent / "manifest.json"
    manifest = {
        "method_version": "monthly-cell-grid-v1",
        "period": {"year": year, "month": month},
        "feature_table": path.name,
        "feature_table_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "quality_filters": {
            "MOD13C2_VI_quality": "not applied",
            "MOD11C3_QC_Day_and_QC_Night": "not applied",
        },
        "raw_inputs": [
            {
                "filename": f"synthetic-{index}.hdf",
                "sha256": hashlib.sha256(f"{year}-{month}-{index}".encode()).hexdigest(),
            }
            for index in range(3)
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_monthly_builder_resolves_exact_product_granules(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(build_features, "RAW", tmp_path)
    names = (
        "MOD13C2.A2024153.061.test.hdf",
        "MOD11C3.A2024153.061.test.hdf",
        "3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5",
    )
    for name in names:
        (tmp_path / name).touch()

    assert tuple(path.name for path in build_features.monthly_input_files(2024, 6)) == names

    (tmp_path / "MOD13C2.A2024153.061.duplicate.hdf").touch()
    with pytest.raises(SystemExit, match="Expected exactly one MOD13C2 NDVI"):
        build_features.monthly_input_files(2024, 6)


def test_range_builder_preflights_every_month_before_processing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(build_features, "RAW", tmp_path)
    for name in (
        "MOD13C2.A2024153.061.test.hdf",
        "MOD11C3.A2024153.061.test.hdf",
        "3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5",
    ):
        (tmp_path / name).touch()

    months, missing = build_monthly_range.plan_months(2024, 2024)

    assert months == [(2024, 6)]
    assert len(missing) == 11
    assert any("2024-07" in item for item in missing)
    monkeypatch.setattr(
        sys,
        "argv",
        ["build_monthly_range.py", "--start-year", "2024", "--end-year", "2024"],
    )
    monkeypatch.setattr(
        build_monthly_range.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("processing started before range preflight"),
    )
    with pytest.raises(SystemExit, match="Stopping before processing"):
        build_monthly_range.main()


def test_multi_year_aggregation_is_weighted_by_days_and_keeps_temporal_spread(
    tmp_path: Path,
):
    write_synthetic_months(tmp_path, range(2023, 2025))

    frame, manifest = build_climatology(
        2023,
        2024,
        min_months_per_year=10,
        min_years=2,
        monthly_root=tmp_path,
    )

    annual_ndvi_means = []
    for year, year_offset in ((2023, 0), (2024, 1)):
        days = [calendar.monthrange(year, month)[1] for month in range(1, 13)]
        annual_ndvi_means.append(
            sum(
                (month / 100 + year_offset * 0.1) * days[month - 1]
                for month in range(1, 13)
            )
            / sum(days)
        )
    assert frame.loc[0, "ndvi_multi_year_mean"] == pytest.approx(
        sum(annual_ndvi_means) / 2
    )
    assert frame.loc[0, "ndvi_interannual_sd"] == pytest.approx(
        abs(annual_ndvi_means[1] - annual_ndvi_means[0]) / math.sqrt(2)
    )
    assert frame.loc[0, "ndvi_typical_monthly_min"] == pytest.approx(0.06)
    assert frame.loc[0, "ndvi_typical_monthly_max"] == pytest.approx(0.17)
    assert frame.loc[0, "lst_night_coldest_month_mean_k"] == pytest.approx(201.5)
    assert frame.loc[0, "lst_night_warmest_month_mean_k"] == pytest.approx(212.5)
    assert frame.loc[0, "ndvi_years_covered"] == 2
    assert frame.loc[0, "ndvi_mean_valid_months_per_year"] == pytest.approx(12)
    assert frame.loc[0, "ndvi_mean_valid_pixels_per_month"] == pytest.approx(16)
    assert pd.isna(frame.loc[1, "ndvi_multi_year_mean"])
    assert frame.loc[1, "ndvi_years_covered"] == 0
    assert manifest["input_count"] == 24
    assert all(len(entry["sha256"]) == 64 for entry in manifest["inputs"])


def test_five_year_period_uses_four_year_default_coverage_and_neutral_labels(
    tmp_path: Path,
):
    write_synthetic_months(tmp_path, range(2019, 2024))

    frame, manifest = build_climatology(2019, 2023, monthly_root=tmp_path)

    assert manifest["minimum_valid_months_per_year"] == 10
    assert manifest["minimum_years_required_per_cell"] == 4
    assert manifest["method_version"] == "annualized-grid-v2"
    assert "ndvi_multi_year_mean" in frame
    assert "ndvi_annual_mean_10y" not in frame


def test_multi_year_aggregation_rejects_misaligned_monthly_grids(tmp_path: Path):
    write_synthetic_months(tmp_path, range(2023, 2024))
    february = input_path(2023, 2, tmp_path)
    table = pd.read_csv(february)
    table.loc[:, ["lat_center_deg", "lon_center_deg"]] = table.loc[
        ::-1, ["lat_center_deg", "lon_center_deg"]
    ].to_numpy()
    table.to_csv(february, index=False, compression="gzip")
    write_month_manifest(february, 2023, 2)

    with pytest.raises(ValueError, match="different coordinate grid or row order"):
        build_climatology(2023, 2023, min_months_per_year=10, monthly_root=tmp_path)


def test_multi_year_aggregation_fails_when_any_month_is_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Missing 12 of 12 monthly feature tables"):
        build_climatology(2023, 2023, monthly_root=tmp_path)


def test_multi_year_aggregation_rejects_a_monthly_table_that_changed_after_manifest(
    tmp_path: Path,
):
    write_synthetic_months(tmp_path, range(2023, 2024))
    february = input_path(2023, 2, tmp_path)
    table = pd.read_csv(february)
    table.loc[0, "ndvi_median"] = 0.99
    table.to_csv(february, index=False, compression="gzip")

    with pytest.raises(ValueError, match="does not match its monthly source manifest"):
        build_climatology(2023, 2023, min_months_per_year=10, monthly_root=tmp_path)


def test_multi_year_aggregation_discards_months_below_half_cell_pixel_support(
    tmp_path: Path,
):
    write_synthetic_months(tmp_path, range(2023, 2024))
    february = input_path(2023, 2, tmp_path)
    table = pd.read_csv(february)
    table.loc[0, "ndvi_valid_count"] = 1
    table.to_csv(february, index=False, compression="gzip")
    write_month_manifest(february, 2023, 2)

    frame, manifest = build_climatology(
        2023,
        2023,
        min_months_per_year=11,
        monthly_root=tmp_path,
    )

    days = [
        calendar.monthrange(2023, month)[1]
        for month in range(1, 13)
        if month != 2
    ]
    expected = sum(
        month / 100 * calendar.monthrange(2023, month)[1]
        for month in range(1, 13)
        if month != 2
    ) / sum(days)
    assert frame.loc[0, "ndvi_multi_year_mean"] == pytest.approx(expected)
    assert frame.loc[0, "ndvi_mean_valid_pixels_per_month"] == pytest.approx(16)
    assert manifest["minimum_valid_pixels_per_month"]["ndvi_median"]["minimum"] == 8


def test_climatology_scoring_uses_coldest_month_proxy_and_fails_closed_on_missing_data():
    frame = pd.DataFrame(
        {
            "lat_center_deg": [0.0, 1.0, 2.0],
            "lon_center_deg": [0.0, 1.0, 2.0],
            "ndvi_multi_year_mean": [0.0, 0.1, np.nan],
            "precip_multi_year_mean_rate_mm_hr": [0.0, 0.01, 0.02],
            "lst_night_coldest_month_mean_k": [190.0, 200.0, 210.0],
            "ndvi_interannual_sd": [0.01, 0.02, np.nan],
        }
    )
    weights = {
        "cold_tail_percentile": 10,
        "distance_scale_percentile": 95,
        "features": {
            "slope_median_deg": 1.0,
            "ndvi_median": 1.0,
            "precip_median_mm_hr": 1.0,
            "lst_night_median_k": 1.0,
        },
    }

    scored, metadata = build_scores(frame, weights, (8.0, 16.7))

    assert metadata["active_features"] == [
        "ndvi_median",
        "precip_median_mm_hr",
        "lst_night_median_k",
    ]
    assert metadata["cold_target_k"] == pytest.approx(192.0)
    assert scored["eligible"].tolist() == [True, True, False]
    assert scored["score"].iloc[:2].notna().all()
    assert pd.isna(scored["score"].iloc[2])


def test_climatology_scoring_writes_separate_hash_checked_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    period = "2019-2023"
    data_root = tmp_path / "climatology"
    data_dir = data_root / period
    data_dir.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "lat_center_deg": [0.0, 35.0, -25.0, 10.0],
            "lon_center_deg": [0.0, 80.0, -70.0, 30.0],
            "ndvi_multi_year_mean": [0.0, 0.1, 0.2, 0.05],
            "ndvi_interannual_sd": [0.01, 0.02, 0.03, 0.01],
            "ndvi_typical_monthly_min": [-0.1, 0.0, 0.1, 0.0],
            "ndvi_typical_monthly_max": [0.2, 0.3, 0.4, 0.2],
            "ndvi_years_covered": [5, 5, 5, 5],
            "ndvi_mean_valid_months_per_year": [12, 12, 12, 12],
            "ndvi_mean_valid_pixels_per_month": [16, 16, 16, 16],
            "precip_multi_year_mean_rate_mm_hr": [0.0, 0.01, 0.02, 0.03],
            "precip_interannual_sd_mm_hr": [0.001, 0.002, 0.003, 0.004],
            "precip_typical_monthly_min_rate_mm_hr": [0.0, 0.0, 0.01, 0.01],
            "precip_typical_monthly_max_rate_mm_hr": [0.01, 0.02, 0.03, 0.04],
            "precip_years_covered": [5, 5, 5, 5],
            "precip_mean_valid_months_per_year": [12, 12, 12, 12],
            "precip_mean_valid_pixels_per_month": [4, 4, 4, 4],
            "lst_night_multi_year_mean_k": [230.0, 240.0, 250.0, 260.0],
            "lst_night_interannual_sd_k": [1.0, 2.0, 3.0, 4.0],
            "lst_night_coldest_month_mean_k": [190.0, 200.0, 210.0, 220.0],
            "lst_night_warmest_month_mean_k": [240.0, 250.0, 260.0, 270.0],
            "lst_night_years_covered": [5, 5, 5, 5],
            "lst_night_mean_valid_months_per_year": [12, 12, 12, 12],
            "lst_night_mean_valid_pixels_per_month": [16, 16, 16, 16],
        }
    )
    feature_path = data_dir / "features.csv"
    frame.to_csv(feature_path, index=False)
    (data_dir / "manifest.json").write_text(
        json.dumps(
            {
                "period": {"start_year": 2019, "end_year": 2023},
                "input_count": 60,
                "method_version": "annualized-grid-v2",
                "minimum_valid_months_per_year": 10,
                "minimum_years_required_per_cell": 4,
                "minimum_valid_pixels_per_month": {
                    "ndvi_median": {"minimum": 8, "maximum": 16},
                    "precip_median_mm_hr": {"minimum": 2, "maximum": 4},
                    "lst_night_median_k": {"minimum": 8, "maximum": 16},
                },
                "feature_table_sha256": hashlib.sha256(feature_path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    weights_path = tmp_path / "weights.json"
    weights_path.write_text(
        json.dumps(
            {
                "cold_tail_percentile": 10,
                "distance_scale_percentile": 95,
                "features": {
                    "slope_median_deg": {"weight": 1.0},
                    "ndvi_median": {"weight": 1.0},
                    "precip_median_mm_hr": {"weight": 1.0},
                    "lst_night_median_k": {"weight": 1.0},
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(climatology_scorer, "CLIMATOLOGY_ROOT", data_root)
    monkeypatch.setattr(climatology_scorer, "RESULTS_ROOT", tmp_path / "results")
    monkeypatch.setattr(climatology_scorer, "ROOT", tmp_path)
    monkeypatch.setattr(score_module, "WEIGHTS_JSON", weights_path)
    monkeypatch.setattr(
        "sys.argv",
        ["score_climatology.py", "--start-year", "2019", "--end-year", "2023"],
    )

    climatology_scorer.main()

    output_dir = tmp_path / "results" / "climatology" / period
    assert (output_dir / "scores.csv.gz").is_file()
    assert (output_dir / "top5.csv").is_file()
    assert (output_dir / "control.csv").is_file()
    summary = json.loads((output_dir / "run.json").read_text(encoding="utf-8"))
    assert summary["monthly_tables"] == 60
    assert summary["discovery_cells_after_exclusions"] == 3
    assert summary["best_control"]["lat_center_deg"] == -25.0
