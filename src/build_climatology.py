"""Build a multi-year annualized feature table from monthly feature grids.

The input tables are created by ``src/build_features.py --year Y --month M``.
This script does not read raw rasters, fill gaps, score cells, or alter the
published June 2024 baseline.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MONTHLY_ROOT = ROOT / "data" / "processed" / "monthly"
OUTPUT_ROOT = ROOT / "data" / "processed" / "climatology"

SOURCE_FEATURES = {
    "ndvi_median": {
        "valid_count": "ndvi_valid_count",
        "minimum_pixels": 8,
        "maximum_pixels": 16,
        "mean": "ndvi_multi_year_mean",
        "std": "ndvi_interannual_sd",
        "seasonal_low": "ndvi_typical_monthly_min",
        "seasonal_high": "ndvi_typical_monthly_max",
        "years": "ndvi_years_covered",
        "months": "ndvi_mean_valid_months_per_year",
        "pixels": "ndvi_mean_valid_pixels_per_month",
    },
    "precip_median_mm_hr": {
        "valid_count": "precip_valid_count",
        "minimum_pixels": 2,
        "maximum_pixels": 4,
        "mean": "precip_multi_year_mean_rate_mm_hr",
        "std": "precip_interannual_sd_mm_hr",
        "seasonal_low": "precip_typical_monthly_min_rate_mm_hr",
        "seasonal_high": "precip_typical_monthly_max_rate_mm_hr",
        "years": "precip_years_covered",
        "months": "precip_mean_valid_months_per_year",
        "pixels": "precip_mean_valid_pixels_per_month",
    },
    "lst_night_median_k": {
        "valid_count": "lst_night_valid_count",
        "minimum_pixels": 8,
        "maximum_pixels": 16,
        "mean": "lst_night_multi_year_mean_k",
        "std": "lst_night_interannual_sd_k",
        "seasonal_low": "lst_night_coldest_month_mean_k",
        "seasonal_high": "lst_night_warmest_month_mean_k",
        "years": "lst_night_years_covered",
        "months": "lst_night_mean_valid_months_per_year",
        "pixels": "lst_night_mean_valid_pixels_per_month",
    },
}
BASE_COLUMNS = ("lat_center_deg", "lon_center_deg")
INPUT_COLUMNS = (
    *BASE_COLUMNS,
    *(
        column
        for feature, definition in SOURCE_FEATURES.items()
        for column in (feature, definition["valid_count"])
    ),
)


def input_path(year: int, month: int, monthly_root: Path = MONTHLY_ROOT) -> Path:
    return monthly_root / f"{year:04d}-{month:02d}" / "features.csv.gz"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sha256_digest(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        return len(bytes.fromhex(value)) == 32
    except ValueError:
        return False


def build_climatology(
    start_year: int,
    end_year: int,
    min_months_per_year: int = 10,
    min_years: int | None = None,
    monthly_root: Path = MONTHLY_ROOT,
) -> tuple[pd.DataFrame, dict]:
    if start_year < 2000 or end_year < start_year:
        raise ValueError("Years must be ordered and start no earlier than 2000.")
    year_count = end_year - start_year + 1
    if not 1 <= min_months_per_year <= 12:
        raise ValueError("min_months_per_year must be between 1 and 12.")
    required_years = min_years if min_years is not None else math.ceil(year_count * 0.8)
    if not 1 <= required_years <= year_count:
        raise ValueError("min_years must be between 1 and the number of requested years.")

    expected = [
        input_path(year, month, monthly_root)
        for year in range(start_year, end_year + 1)
        for month in range(1, 13)
    ]
    missing = [path for path in expected if not path.is_file()]
    missing_manifests = [
        path.parent / "manifest.json"
        for path in expected
        if path.is_file() and not (path.parent / "manifest.json").is_file()
    ]
    if missing:
        rendered = "\n".join(f"  {path}" for path in missing)
        raise FileNotFoundError(
            f"Missing {len(missing)} of {len(expected)} monthly feature tables. "
            "No climatology was written. Build every month first:\n" + rendered
        )
    if missing_manifests:
        rendered = "\n".join(f"  {path}" for path in missing_manifests)
        raise FileNotFoundError(
            f"Missing {len(missing_manifests)} monthly source manifests. "
            "No climatology was written:\n" + rendered
        )

    first_table = pd.read_csv(input_path(start_year, 1, monthly_root), usecols=BASE_COLUMNS)
    coordinates = first_table.loc[:, BASE_COLUMNS].to_numpy(dtype=np.float64)
    cell_count = len(coordinates)
    if cell_count == 0 or not np.isfinite(coordinates).all():
        raise ValueError(f"{input_path(start_year, 1, monthly_root)} has no valid coordinate grid.")
    if pd.DataFrame(coordinates).duplicated().any():
        raise ValueError(f"{input_path(start_year, 1, monthly_root)} contains duplicate cell coordinates.")
    del first_table

    annual_state: dict[str, dict[str, np.ndarray]] = {}
    seasonal_state: dict[str, dict[str, np.ndarray]] = {}
    input_manifest = []

    for feature in SOURCE_FEATURES:
        annual_state[feature] = {
            "count": np.zeros(cell_count, dtype=np.int16),
            "mean": np.zeros(cell_count, dtype=np.float64),
            "m2": np.zeros(cell_count, dtype=np.float64),
        }
        seasonal_state[feature] = {
            "low_sum": np.zeros(cell_count, dtype=np.float64),
            "high_sum": np.zeros(cell_count, dtype=np.float64),
            "year_count": np.zeros(cell_count, dtype=np.int16),
            "month_sum": np.zeros(cell_count, dtype=np.float64),
            "pixel_sum": np.zeros(cell_count, dtype=np.float64),
            "pixel_month_count": np.zeros(cell_count, dtype=np.int32),
        }

    for year in range(start_year, end_year + 1):
        annual_sum = {
            feature: np.zeros(cell_count, dtype=np.float64)
            for feature in SOURCE_FEATURES
        }
        annual_days = {
            feature: np.zeros(cell_count, dtype=np.float64)
            for feature in SOURCE_FEATURES
        }
        annual_months = {
            feature: np.zeros(cell_count, dtype=np.int16)
            for feature in SOURCE_FEATURES
        }
        annual_low = {
            feature: np.full(cell_count, np.inf, dtype=np.float64)
            for feature in SOURCE_FEATURES
        }
        annual_high = {
            feature: np.full(cell_count, -np.inf, dtype=np.float64)
            for feature in SOURCE_FEATURES
        }

        for month in range(1, 13):
            path = input_path(year, month, monthly_root)
            source_manifest_path = path.parent / "manifest.json"
            source_manifest = json.loads(
                source_manifest_path.read_text(encoding="utf-8")
            )
            if not isinstance(source_manifest, dict):
                raise ValueError(f"{source_manifest_path} is not a JSON object.")
            if source_manifest.get("method_version") != "monthly-cell-grid-v1":
                raise ValueError(f"{source_manifest_path} has an unsupported method version.")
            if source_manifest.get("period") != {"year": year, "month": month}:
                raise ValueError(f"{source_manifest_path} records the wrong calendar month.")
            if source_manifest.get("feature_table_sha256") != sha256_file(path):
                raise ValueError(f"{path} does not match its monthly source manifest.")
            if source_manifest.get("quality_filters") != {
                "MOD13C2_VI_quality": "not applied",
                "MOD11C3_QC_Day_and_QC_Night": "not applied",
            }:
                raise ValueError(f"{source_manifest_path} has unexpected quality-filter metadata.")
            raw_inputs = source_manifest.get("raw_inputs")
            if (
                not isinstance(raw_inputs, list)
                or len(raw_inputs) != 3
                or any(
                    not isinstance(item, dict)
                    or not isinstance(item.get("filename"), str)
                    or not is_sha256_digest(item.get("sha256"))
                    for item in raw_inputs
                )
            ):
                raise ValueError(f"{source_manifest_path} has incomplete raw-input hashes.")
            table = pd.read_csv(path, usecols=INPUT_COLUMNS)
            current_coordinates = table.loc[:, BASE_COLUMNS].to_numpy(dtype=np.float64)
            if current_coordinates.shape != coordinates.shape or not np.array_equal(
                current_coordinates, coordinates
            ):
                raise ValueError(f"{path} has a different coordinate grid or row order.")

            days = calendar.monthrange(year, month)[1]
            for feature in SOURCE_FEATURES:
                definition = SOURCE_FEATURES[feature]
                values = pd.to_numeric(table[feature], errors="raise").to_numpy(
                    dtype=np.float64
                )
                pixels = pd.to_numeric(
                    table[definition["valid_count"]], errors="raise"
                ).to_numpy(dtype=np.float64)
                max_pixels = definition["maximum_pixels"]
                if (
                    not np.isfinite(pixels).all()
                    or np.any(pixels < 0)
                    or np.any(pixels > max_pixels)
                    or np.any(pixels != np.floor(pixels))
                ):
                    raise ValueError(
                        f"{path} has invalid {definition['valid_count']} values."
                    )
                valid = (
                    np.isfinite(values)
                    & (pixels >= definition["minimum_pixels"])
                )
                annual_sum[feature][valid] += values[valid] * days
                annual_days[feature][valid] += days
                annual_months[feature][valid] += 1
                annual_low[feature][valid] = np.minimum(
                    annual_low[feature][valid], values[valid]
                )
                annual_high[feature][valid] = np.maximum(
                    annual_high[feature][valid], values[valid]
                )
                seasonal_state[feature]["pixel_sum"][valid] += pixels[valid]
                seasonal_state[feature]["pixel_month_count"][valid] += 1

            input_manifest.append(
                {
                    "path": path.relative_to(ROOT).as_posix()
                    if path.is_relative_to(ROOT)
                    else str(path),
                    "sha256": sha256_file(path),
                    "source_manifest_sha256": sha256_file(source_manifest_path),
                    "raw_inputs": raw_inputs,
                }
            )
            del table

        for feature in SOURCE_FEATURES:
            month_coverage = annual_months[feature]
            valid_year = month_coverage >= min_months_per_year
            valid_year &= annual_days[feature] > 0
            annual_mean = np.full(cell_count, np.nan, dtype=np.float64)
            annual_mean[valid_year] = (
                annual_sum[feature][valid_year] / annual_days[feature][valid_year]
            )

            state = annual_state[feature]
            old_count = state["count"][valid_year]
            new_count = old_count + 1
            delta = annual_mean[valid_year] - state["mean"][valid_year]
            updated_mean = state["mean"][valid_year] + delta / new_count
            state["m2"][valid_year] += delta * (
                annual_mean[valid_year] - updated_mean
            )
            state["mean"][valid_year] = updated_mean
            state["count"][valid_year] = new_count

            seasonal = seasonal_state[feature]
            seasonal["low_sum"][valid_year] += annual_low[feature][valid_year]
            seasonal["high_sum"][valid_year] += annual_high[feature][valid_year]
            seasonal["year_count"][valid_year] += 1
            seasonal["month_sum"][valid_year] += month_coverage[valid_year]

    output: dict[str, np.ndarray] = {
        "lat_center_deg": coordinates[:, 0],
        "lon_center_deg": coordinates[:, 1],
    }
    for feature, names in SOURCE_FEATURES.items():
        state = annual_state[feature]
        valid = state["count"] >= required_years
        mean = np.full(cell_count, np.nan, dtype=np.float64)
        mean[valid] = state["mean"][valid]
        std = np.full(cell_count, np.nan, dtype=np.float64)
        enough_for_std = valid & (state["count"] > 1)
        std[enough_for_std] = np.sqrt(
            state["m2"][enough_for_std] / (state["count"][enough_for_std] - 1)
        )

        seasonal = seasonal_state[feature]
        low = np.full(cell_count, np.nan, dtype=np.float64)
        high = np.full(cell_count, np.nan, dtype=np.float64)
        mean_months = np.full(cell_count, np.nan, dtype=np.float64)
        mean_pixels = np.full(cell_count, np.nan, dtype=np.float64)
        low[valid] = seasonal["low_sum"][valid] / seasonal["year_count"][valid]
        high[valid] = seasonal["high_sum"][valid] / seasonal["year_count"][valid]
        mean_months[valid] = (
            seasonal["month_sum"][valid] / seasonal["year_count"][valid]
        )
        has_pixel_support = seasonal["pixel_month_count"] > 0
        mean_pixels[has_pixel_support] = (
            seasonal["pixel_sum"][has_pixel_support]
            / seasonal["pixel_month_count"][has_pixel_support]
        )

        output[names["mean"]] = mean
        output[names["std"]] = std
        output[names["seasonal_low"]] = low
        output[names["seasonal_high"]] = high
        output[names["years"]] = state["count"]
        output[names["months"]] = mean_months
        output[names["pixels"]] = mean_pixels

    metadata = {
        "method_version": "annualized-grid-v2",
        "period": {"start_year": start_year, "end_year": end_year},
        "annualization": "calendar-day-weighted mean of monthly cell medians/rates",
        "minimum_valid_months_per_year": min_months_per_year,
        "minimum_years_required_per_cell": required_years,
        "minimum_valid_pixels_per_month": {
            feature: {
                "minimum": definition["minimum_pixels"],
                "maximum": definition["maximum_pixels"],
            }
            for feature, definition in SOURCE_FEATURES.items()
        },
        "yearly_variability": "sample standard deviation across valid annual means",
        "seasonal_extremes": (
            "mean across years of each year's lowest/highest valid monthly cell value; "
            "years must meet the monthly-coverage threshold"
        ),
        "input_count": len(input_manifest),
        "inputs": input_manifest,
    }
    return pd.DataFrame(output), metadata


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an annualized multi-year grid from monthly feature tables."
    )
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--min-months-per-year", type=int, default=10)
    parser.add_argument(
        "--min-years",
        type=int,
        help="Minimum valid annual values per cell (default: 80%% of requested years).",
    )
    args = parser.parse_args()

    try:
        frame, metadata = build_climatology(
            args.start_year,
            args.end_year,
            args.min_months_per_year,
            args.min_years,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"Stopping: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    period = f"{args.start_year}-{args.end_year}"
    output_dir = OUTPUT_ROOT / period
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "features.csv"
    output_json = output_dir / "manifest.json"
    frame.to_csv(output_csv, index=False, na_rep="", float_format="%.6f")
    metadata["feature_table_sha256"] = sha256_file(output_csv)
    output_json.write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Cells: {len(frame)}")
    for feature, names in SOURCE_FEATURES.items():
        valid = int(frame[names["mean"]].notna().sum())
        print(f"{feature}: annualized values available for {valid} cells")
    print(f"Wrote {output_csv.relative_to(ROOT).as_posix()}")
    print(f"Wrote {output_json.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
