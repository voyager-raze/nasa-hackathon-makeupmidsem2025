"""Score the separate multi-year annualized feature product."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import score as scorer  # noqa: E402
from build_climatology import SOURCE_FEATURES  # noqa: E402
from export_map_data import rejected_center  # noqa: E402

CLIMATOLOGY_ROOT = ROOT / "data" / "processed" / "climatology"
RESULTS_ROOT = ROOT / "results"

CLIMATOLOGY_COLUMNS = {
    "slope_median_deg": None,
    "ndvi_median": "ndvi_annual_mean_10y",
    "precip_median_mm_hr": "precip_annual_mean_rate_mm_hr_10y",
    "lst_night_median_k": "lst_night_coldest_month_mean_k",
}
VARIABILITY_COLUMNS = {
    "ndvi_median": "ndvi_interannual_sd",
    "precip_median_mm_hr": "precip_interannual_sd_mm_hr",
    "lst_night_median_k": "lst_night_interannual_sd_k",
}
SEASONAL_COLUMNS = (
    "ndvi_typical_monthly_min",
    "ndvi_typical_monthly_max",
    "precip_typical_monthly_min_rate_mm_hr",
    "precip_typical_monthly_max_rate_mm_hr",
    "lst_night_warmest_month_mean_k",
)
COVERAGE_COLUMNS = {
    "ndvi_median": "ndvi_years_covered",
    "precip_median_mm_hr": "precip_years_covered",
    "lst_night_median_k": "lst_night_years_covered",
}
PIXEL_COLUMNS = {
    feature: definition["pixels"]
    for feature, definition in SOURCE_FEATURES.items()
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_scores(
    frame: pd.DataFrame, weights_payload: dict, slope_band: tuple[float, float]
) -> tuple[pd.DataFrame, dict]:
    missing_columns = [
        column
        for column in ("lat_center_deg", "lon_center_deg")
        if column not in frame.columns
    ]
    if missing_columns:
        raise ValueError(f"Climatology table is missing columns: {', '.join(missing_columns)}.")

    weights = weights_payload["features"]
    active = []
    skipped = []
    for score_feature in scorer.FEATURE_ORDER:
        weight = weights.get(score_feature, 0.0)
        column = CLIMATOLOGY_COLUMNS[score_feature]
        if weight <= 0:
            skipped.append((score_feature, "weight is zero"))
        elif column is None or column not in frame or frame[column].isna().all():
            skipped.append((score_feature, "no global climatology column"))
        else:
            active.append(score_feature)
    if not active:
        raise ValueError("No positively weighted climatology features are available.")

    if "lst_night_median_k" in active:
        cold_column = CLIMATOLOGY_COLUMNS["lst_night_median_k"]
        cold_target = float(
            frame[cold_column].quantile(
                weights_payload["cold_tail_percentile"] / 100.0
            )
        )
    else:
        cold_target = None

    score = pd.Series(0.0, index=frame.index, dtype=np.float64)
    denominator = pd.Series(0.0, index=frame.index, dtype=np.float64)
    scales = {}
    for score_feature in active:
        column = CLIMATOLOGY_COLUMNS[score_feature]
        distance_name = score_feature
        distance = scorer.raw_distance(
            frame[column], distance_name, cold_target, slope_band
        )
        scale = float(
            distance.quantile(
                weights_payload["distance_scale_percentile"] / 100.0
            )
        )
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError(f"Invalid normalization scale for {score_feature}: {scale}.")
        scales[score_feature] = scale
        present = frame[column].notna()
        weight = float(weights[score_feature])
        score += weight * distance / scale
        denominator += weight * present.astype(np.float64)

    result = frame.copy()
    result["score"] = score / denominator.where(denominator > 0)
    result["eligible"] = result[
        [CLIMATOLOGY_COLUMNS[name] for name in active]
    ].notna().all(axis=1)
    result["in_holdout"] = scorer.holdout_mask(result)
    result["rejected_ice_sheet"] = [
        rejected_center(float(lat), float(lon))
        for lat, lon in zip(
            result["lat_center_deg"], result["lon_center_deg"], strict=True
        )
    ]
    return result, {
        "active_features": active,
        "skipped_features": skipped,
        "cold_target_k": cold_target,
        "scales": scales,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score a built multi-year climatology without replacing the June baseline."
    )
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    args = parser.parse_args()
    period = f"{args.start_year}-{args.end_year}"
    data_dir = CLIMATOLOGY_ROOT / period
    feature_path = data_dir / "features.csv"
    manifest_path = data_dir / "manifest.json"
    if not feature_path.is_file() or not manifest_path.is_file():
        parser.error(f"Build the {period} climatology first with src/build_climatology.py.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("period") != {
        "start_year": args.start_year,
        "end_year": args.end_year,
    }:
        parser.error(f"{manifest_path} does not describe the requested period.")
    if manifest.get("input_count") != (args.end_year - args.start_year + 1) * 12:
        parser.error(f"{manifest_path} does not record one complete monthly table per month.")
    if manifest.get("method_version") != "annualized-grid-v1":
        parser.error(f"{manifest_path} was produced by an unsupported aggregation method.")
    expected_pixel_thresholds = {
        feature: {
            "minimum": definition["minimum_pixels"],
            "maximum": definition["maximum_pixels"],
        }
        for feature, definition in SOURCE_FEATURES.items()
    }
    if manifest.get("minimum_valid_pixels_per_month") != expected_pixel_thresholds:
        parser.error(f"{manifest_path} uses different spatial-support thresholds.")
    if manifest.get("feature_table_sha256") != sha256_file(feature_path):
        parser.error(f"{feature_path} does not match the hash recorded in {manifest_path}.")

    try:
        frame = pd.read_csv(feature_path)
        weights = scorer.load_weights()
        slope_band = scorer.read_slope_band(
            scorer.TARGETS_MD.read_text(encoding="utf-8")
        )
        min_years = int(manifest["minimum_years_required_per_cell"])
        for feature, column in CLIMATOLOGY_COLUMNS.items():
            if (
                weights["features"].get(feature, 0.0) > 0
                and column is not None
                and column in frame
            ):
                coverage_column = COVERAGE_COLUMNS[feature]
                if coverage_column not in frame:
                    raise ValueError(f"Missing coverage column {coverage_column}.")
                covered = frame[coverage_column] >= min_years
                present = frame[column].notna()
                if not covered.equals(present):
                    raise ValueError(
                        f"{column} values disagree with {coverage_column} "
                        f"and the {min_years}-year minimum."
                    )
                pixel_column = PIXEL_COLUMNS[feature]
                if pixel_column not in frame:
                    raise ValueError(f"Missing spatial-support column {pixel_column}.")
                pixel_support = frame[pixel_column]
                pixel_rule = SOURCE_FEATURES[feature]
                bad_support = present & (
                    pixel_support.isna()
                    | (pixel_support < pixel_rule["minimum_pixels"])
                    | (pixel_support > pixel_rule["maximum_pixels"])
                )
                if bad_support.any():
                    raise ValueError(
                        f"{column} values include invalid spatial support in "
                        f"{pixel_column}."
                    )
        scored, metadata = build_scores(frame, weights, slope_band)
    except (ValueError, KeyError) as exc:
        print(f"Stopping: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    eligible = scored["eligible"]
    discovery = scored.loc[
        eligible & ~scored["in_holdout"] & ~scored["rejected_ice_sheet"]
    ].sort_values(
        ["score", "lat_center_deg", "lon_center_deg"],
        ascending=True,
        kind="mergesort",
    )
    control = scored.loc[eligible & scored["in_holdout"]].sort_values(
        ["score", "lat_center_deg", "lon_center_deg"],
        ascending=True,
        kind="mergesort",
    )
    if discovery.empty or control.empty:
        raise SystemExit(
            "Stopping: climatology produced no eligible discovery cells or no eligible control cells."
        )

    output_dir = RESULTS_ROOT / "climatology" / period
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked_columns = [
        "lat_center_deg",
        "lon_center_deg",
        *CLIMATOLOGY_COLUMNS.values(),
        *VARIABILITY_COLUMNS.values(),
        *SEASONAL_COLUMNS,
        *COVERAGE_COLUMNS.values(),
        *PIXEL_COLUMNS.values(),
        "score",
        "eligible",
        "in_holdout",
        "rejected_ice_sheet",
    ]
    ranked_columns = [column for column in ranked_columns if column in scored.columns]
    scored.loc[:, ranked_columns].to_csv(
        output_dir / "scores.csv.gz",
        index=False,
        na_rep="",
        float_format="%.6f",
    )
    discovery.head(5).to_csv(
        output_dir / "top5.csv", index=False, na_rep="", float_format="%.6f"
    )
    control.head(1).to_csv(
        output_dir / "control.csv", index=False, na_rep="", float_format="%.6f"
    )

    summary = {
        "period": manifest["period"],
        "monthly_tables": manifest["input_count"],
        "feature_table_sha256": manifest["feature_table_sha256"],
        "weights_sha256": sha256_file(scorer.WEIGHTS_JSON),
        "targets_sha256": sha256_file(scorer.TARGETS_MD),
        "method_version": "annualized-climatology-score-v1",
        "minimum_valid_months_per_year": manifest[
            "minimum_valid_months_per_year"
        ],
        "minimum_valid_pixels_per_month": manifest[
            "minimum_valid_pixels_per_month"
        ],
        "minimum_years_required_per_cell": manifest[
            "minimum_years_required_per_cell"
        ],
        **metadata,
        "eligible_cells": int(eligible.sum()),
        "discovery_cells_after_exclusions": len(discovery),
        "control_cells": len(control),
        "discovery_top5": discovery.head(5)[
            ["lat_center_deg", "lon_center_deg", "score"]
        ].to_dict(orient="records"),
        "best_control": control.iloc[0][
            ["lat_center_deg", "lon_center_deg", "score"]
        ].to_dict(),
    }
    summary_path = output_dir / "run.json"
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Period: {period}")
    print(f"Eligible cells: {int(eligible.sum())}")
    print(f"Discovery cells after exclusions: {len(discovery)}")
    print(f"Best discovery: {summary['discovery_top5'][0]}")
    print(f"Best control: {summary['best_control']}")
    print(f"Wrote {summary_path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
