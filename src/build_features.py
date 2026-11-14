"""Build a coarse land-cell table for one month of MODIS and IMERG data.

With no arguments, this preserves the published June 2024 baseline outputs.
With ``--year`` and ``--month``, it resolves that month's granules and writes
a compressed, versioned table under data/processed/monthly/.
"""

from __future__ import annotations

import argparse
import calendar
from datetime import date
import hashlib
import json
import sys
import warnings
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from pyhdf.SD import SD, SDC

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

NDVI_FILE = RAW / "MOD13C2.A2024153.061.2024198104950.hdf"
LST_FILE = RAW / "MOD11C3.A2024153.061.2024187024328.hdf"
PRECIP_FILE = RAW / "3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5"

OUT_CSV = ROOT / "data" / "processed" / "features.csv"
OUT_MD = ROOT / "notes" / "features.md"

# 4 x 4 MODIS 0.05° pixels and 2 x 2 IMERG 0.1° pixels.
CELL_DEG = 0.2
MODIS_DEG = 0.05
KM_PER_DEG = 111.32


def require_files(paths: tuple[Path, Path, Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        print("Stopping. Logged measurement files are missing:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        sys.exit(1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def monthly_input_files(year: int, month: int) -> tuple[Path, Path, Path]:
    """Find the three logged product granules for one calendar month."""
    first = date(year, month, 1)
    year_day = f"{year}{first.timetuple().tm_yday:03d}"
    year_month = f"{year}{month:02d}"
    patterns = (
        f"MOD13C2.A{year_day}.061.*.hdf",
        f"MOD11C3.A{year_day}.061.*.hdf",
        f"3B-MO.MS.MRG.3IMERG.{year_month}01-S000000-E235959.*.HDF5",
    )
    labels = ("MOD13C2 NDVI", "MOD11C3 LST", "monthly IMERG precipitation")
    selected = []
    for label, pattern in zip(labels, patterns, strict=True):
        matches = sorted(RAW.glob(pattern))
        if len(matches) != 1:
            found = ", ".join(path.name for path in matches) or "none"
            raise SystemExit(
                f"Expected exactly one {label} granule for {year:04d}-{month:02d}; "
                f"found {len(matches)} ({found})."
            )
        selected.append(matches[0])
    return selected[0], selected[1], selected[2]


def sds_array(hdf: SD, name: str) -> tuple[np.ndarray, dict]:
    dataset = hdf.select(name)
    values = np.array(dataset.get())
    return values, dict(dataset.attributes())


def apply_modis_scale(raw: np.ndarray, attrs: dict, kind: str) -> tuple[np.ndarray, str]:
    """Convert a MODIS CMG layer using the attributes stored on that layer."""
    fill = attrs["_FillValue"]
    valid_min, valid_max = (int(v) for v in attrs["valid_range"])
    scale = float(attrs["scale_factor"])
    physical = raw.astype(np.float64)
    invalid = (raw == fill) | (raw < valid_min) | (raw > valid_max)
    physical[invalid] = np.nan

    formula = str(attrs.get("LST", ""))
    units = str(attrs.get("units", "")).strip()
    if "LST data * scale_factor" in formula:
        physical = physical * scale
        scaled_as = f"stored integer * scale_factor ({scale}), as the layer attribute states"
    elif kind == "ndvi" and units == "NDVI" and abs(scale) > 2.0:
        # valid_range is the stored integer range. Dividing by this scale_factor
        # is what puts those integers into the NDVI interval the units name.
        physical = physical / scale
        scaled_as = f"stored integer / scale_factor ({scale:g})"
    else:
        raise SystemExit(
            f"Refusing to scale {kind}: units={units!r}, scale_factor={scale}, formula={formula!r}"
        )
    return physical, scaled_as


def block_median(north_up: np.ndarray, factor: int) -> tuple[np.ndarray, np.ndarray]:
    """Median and valid-pixel count on a north-up grid, into factor x factor cells."""
    rows, cols = north_up.shape
    if rows % factor or cols % factor:
        raise SystemExit(f"Grid shape {north_up.shape} is not divisible by {factor}.")
    nlat = rows // factor
    nlon = cols // factor
    blocks = (
        north_up.reshape(nlat, factor, nlon, factor)
        .transpose(0, 2, 1, 3)
        .reshape(nlat, nlon, factor * factor)
    )
    count = np.sum(np.isfinite(blocks), axis=2).astype(np.int32)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="All-NaN slice encountered")
        median = np.nanmedian(blocks, axis=2)
    median[count == 0] = np.nan
    return median, count


def read_ndvi(path: Path) -> tuple[np.ndarray, str]:
    hdf = SD(str(path), SDC.READ)
    try:
        raw, attrs = sds_array(hdf, "CMG 0.05 Deg Monthly NDVI")
    finally:
        hdf.end()
    if raw.shape != (3600, 7200):
        raise SystemExit(f"NDVI shape {raw.shape} is not the 0.05° CMG (3600, 7200).")
    physical, scaled_as = apply_modis_scale(raw, attrs, "ndvi")
    finite = physical[np.isfinite(physical)]
    if finite.size == 0 or not (-1.0 <= float(np.median(finite)) <= 1.0):
        raise SystemExit("NDVI scale check failed. Stopping without writing a table.")
    return physical, scaled_as


def read_lst_and_land(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, str, str]:
    hdf = SD(str(path), SDC.READ)
    try:
        day_raw, day_attrs = sds_array(hdf, "LST_Day_CMG")
        lst_raw, lst_attrs = sds_array(hdf, "LST_Night_CMG")
        land_raw, land_attrs = sds_array(hdf, "Percent_land_in_grid")
    finally:
        hdf.end()
    if day_raw.shape != (3600, 7200) or lst_raw.shape != (3600, 7200) or land_raw.shape != (3600, 7200):
        raise SystemExit("LST or land-fraction shape is not the 0.05° CMG.")
    day, day_scaled_as = apply_modis_scale(day_raw, day_attrs, "lst")
    lst, night_scaled_as = apply_modis_scale(lst_raw, lst_attrs, "lst")
    del day_raw, lst_raw
    for label, values in (("Day", day), ("Night", lst)):
        finite = values[np.isfinite(values)]
        if finite.size == 0 or not (150.0 <= float(np.median(finite)) <= 350.0):
            raise SystemExit(f"{label} LST scale check failed. Stopping without writing a table.")

    fill = int(land_attrs["_FillValue"])
    valid_min, valid_max = (int(v) for v in land_attrs["valid_range"])
    land = (land_raw != fill) & (land_raw >= valid_min) & (land_raw <= valid_max)
    return day, lst, land, day_scaled_as, night_scaled_as


def read_precip(path: Path) -> tuple[np.ndarray, str]:
    with h5py.File(path, "r") as handle:
        data = handle["Grid/precipitation"]
        raw = np.array(data[0], dtype=np.float64)  # (lon, lat), southwest origin
        fill = float(data.attrs["_FillValue"])
        units = data.attrs.get("units", b"")
        if isinstance(units, bytes):
            units = units.decode("utf-8", "replace")
        missing_code = data.attrs.get("CodeMissingValue", b"")
        if isinstance(missing_code, bytes):
            missing_code = missing_code.decode("utf-8", "replace").strip()
        header = handle["Grid"].attrs["GridHeader"]
        if isinstance(header, bytes):
            header = header.decode("utf-8", "replace")
    if units.strip() != "mm/hr":
        raise SystemExit(f"Precipitation units are {units!r}, not mm/hr. Stopping.")
    fields = {}
    for part in header.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            fields[key.strip()] = value.strip()
    if fields.get("LatitudeResolution") != "0.1" or fields.get("LongitudeResolution") != "0.1":
        raise SystemExit(f"IMERG resolution is not 0.1°. Header fields: {fields}")
    if raw.shape != (3600, 1800):
        raise SystemExit(f"Precipitation shape {raw.shape} is not (lon 3600, lat 1800).")
    # Flip to north-up (lat, lon) so it matches the MODIS CMG orientation.
    north_up = np.flipud(raw.T)
    north_up[np.isclose(north_up, fill) | (north_up < -9000)] = np.nan
    return north_up, missing_code or str(fill)


def cell_centers(nlat: int, nlon: int) -> tuple[np.ndarray, np.ndarray]:
    # Centers of 0.2° cells covering [90, -90] and [-180, 180], north-up.
    lat = 90.0 - (np.arange(nlat) + 0.5) * CELL_DEG
    lon = -180.0 + (np.arange(nlon) + 0.5) * CELL_DEG
    lat_grid, lon_grid = np.meshgrid(lat, lon, indexing="ij")
    return lat_grid, lon_grid


def null_percent(series: pd.Series) -> float:
    return float(series.isna().mean() * 100.0)


def write_notes(
    ndvi_file: Path,
    lst_file: Path,
    precip_file: Path,
    out_md: Path,
    year: int,
    month: int,
    n_land: int,
    percents: list[tuple[str, float]],
    ndvi_scale_text: str,
    lst_day_scale_text: str,
    lst_night_scale_text: str,
    precip_fill: str,
    ndvi_south_note: str,
) -> None:
    ns_km = CELL_DEG * KM_PER_DEG
    percent_lines = "\n".join(f"| `{name}` | {pct:.2f}% |" for name, pct in percents)
    month_label = f"{calendar.month_name[month]} {year}"
    text = f"""# Feature grid

One row in this feature table is one land cell. This file defines every column. It does not weight cells and it does not rank them.

{month_label} is one month. It is not a climate normal.

## Grid

| Item | Value |
| --- | --- |
| Cell size | {CELL_DEG}° by {CELL_DEG}° |
| North–south length | {ns_km:.1f} km ({CELL_DEG} × {KM_PER_DEG} km per degree) |
| East–west length | {ns_km:.1f} km × cos(latitude). About {ns_km:.1f} km at the equator and about {ns_km * 0.5:.1f} km at 60° latitude |
| MODIS pixels per cell | 4 × 4 pixels of the 0.05° CMG |
| IMERG pixels per cell | 2 × 2 pixels of the 0.1° grid |
| Land cells | {n_land} |

The cell is an integer multiple of both logged grids, so no pixel is split and no gap is interpolated.

## Land rule

A cell is written only when at least one of its 16 MODIS `Percent_land_in_grid` pixels falls in that layer’s valid range (1 to 100). The fill value on that layer is 0, so open ocean is left out of the table. A coastal cell with any valid land pixel is kept. Ocean pixels inside that cell stay out of the vegetation and temperature medians because those layers are fill over water.

## Null rule

A blank measurement means the layer did not cover that cell: the valid-pixel count is 0. A blank is not a zero, not a neighbor’s value, and not an interpolated fill.

`slope_median_deg` and `slope_valid_count` are blank on every row. `notes/data-log.md` records that global elevation was not downloaded. This script does not estimate slope.

## Summary

Land cells: {n_land}

Percent null (blank values among land cells):

| Column | Percent null |
| --- | --- |
{percent_lines}

## Columns

| Column | Unit | Source file | Method |
| --- | --- | --- | --- |
| `lat_center_deg` | degrees north | cell geometry of the logged CMG | center of the {CELL_DEG}° cell. Row 0 of each MODIS grid is the north edge. |
| `lon_center_deg` | degrees east | cell geometry of the logged CMG | center of the {CELL_DEG}° cell. Column 0 is the dateline at 180°W, increasing east. |
| `ndvi_median` | NDVI (native index) | `{ndvi_file.relative_to(ROOT).as_posix()}` layer `CMG 0.05 Deg Monthly NDVI` | {ndvi_scale_text}. Then the median of the finite pixels in the cell. |
| `ndvi_valid_count` | count of 0.05° pixels | same NDVI layer | pixels that are not `_FillValue` (−3000) and lie inside `valid_range` (−2000 to 10000). |
| `lst_day_median_k` | kelvin | `{lst_file.relative_to(ROOT).as_posix()}` layer `LST_Day_CMG` | {lst_day_scale_text}. Then the median of valid pixels in the cell. |
| `lst_day_valid_count` | count of 0.05° pixels | same day LST layer | pixels that are not `_FillValue` and lie inside that layer’s `valid_range`. |
| `lst_night_median_k` | kelvin | `{lst_file.relative_to(ROOT).as_posix()}` layer `LST_Night_CMG` | {lst_night_scale_text}. Then the median of valid pixels in the cell. This remains the only temperature feature in the score. |
| `lst_night_valid_count` | count of 0.05° pixels | same night LST layer | pixels that are not `_FillValue` and lie inside that layer’s `valid_range`. |
| `lst_day_night_range_median_k` | kelvin | same file, layers `LST_Day_CMG` and `LST_Night_CMG` | Median of paired valid-pixel differences `day - night` within the cell. This is a descriptive measure, not a score term. |
| `lst_day_night_range_valid_count` | count of paired 0.05° pixels | same day and night LST layers | Pixels valid in both layers; a missing day or night value stays missing. |
| `precip_median_mm_hr` | mm/hr | `{precip_file.relative_to(ROOT).as_posix()}` dataset `Grid/precipitation` | median of finite pixels. The file unit is mm/hr. `BinMethod=ARITHMETIC_MEAN` and `TimeInterval=MONTH`, so the stored value is the month's mean rate. It was not converted to a monthly millimetre total. This is the dryness measurement, left in the product unit. A lower rate is drier. |
| `precip_valid_count` | count of 0.1° pixels | same precipitation dataset | pixels that are not the fill value ({precip_fill}). |
| `land_pixel_count` | count of 0.05° pixels | `{lst_file.relative_to(ROOT).as_posix()}` layer `Percent_land_in_grid` | pixels inside `valid_range` 1 to 100. This is the land test, not an analog feature. |
| `slope_median_deg` | degrees | no file | not computed. Entirely blank. |
| `slope_valid_count` | count | no file | not computed. Entirely blank. |

{ndvi_south_note}

When a valid count is even, the median is the arithmetic mean of the two central values (NumPy `nanmedian`). The same rule is used for every cell of a column.

`land_pixel_count` is a coverage count. It is not vegetation, temperature, dryness, or slope, and it is not a score. The day and day–night columns are descriptive; they have no target referent or weight in this run.

## What this table is not

No column is a weight, a rank, or a site choice. Slope was not filled from the locked lunar band. Missing vegetation, night temperature, or precipitation was not copied from a neighboring cell.
"""
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one monthly Earth feature table.")
    parser.add_argument("--year", type=int, help="Year of the monthly granules.")
    parser.add_argument("--month", type=int, choices=range(1, 13), help="Calendar month (1-12).")
    args = parser.parse_args()

    if (args.year is None) != (args.month is None):
        parser.error("--year and --month must be supplied together.")
    if args.year is None:
        year, month = 2024, 6
        input_files = (NDVI_FILE, LST_FILE, PRECIP_FILE)
        out_csv, out_md = OUT_CSV, OUT_MD
    else:
        assert args.month is not None
        year, month = args.year, args.month
        if year < 2000:
            parser.error("MOD13C2 monthly inputs are required from year 2000 onward.")
        input_files = monthly_input_files(year, month)
        output_dir = ROOT / "data" / "processed" / "monthly" / f"{year:04d}-{month:02d}"
        out_csv = output_dir / "features.csv.gz"
        out_md = output_dir / "features.md"

    require_files(input_files)
    if abs(CELL_DEG / MODIS_DEG - round(CELL_DEG / MODIS_DEG)) > 1e-9:
        raise SystemExit("Cell size does not tile the MODIS grid.")

    ndvi_file, lst_file, precip_file = input_files
    ndvi, ndvi_scale_text = read_ndvi(ndvi_file)
    lst_day, lst_night, land, lst_day_scale_text, lst_night_scale_text = read_lst_and_land(lst_file)
    precip, precip_fill = read_precip(precip_file)

    modis_factor = int(round(CELL_DEG / MODIS_DEG))
    imerg_factor = int(round(CELL_DEG / 0.1))

    ndvi_median, ndvi_count = block_median(ndvi, modis_factor)
    lst_day_median, lst_day_count = block_median(lst_day, modis_factor)
    lst_night_median, lst_night_count = block_median(lst_night, modis_factor)
    paired = np.isfinite(lst_day) & np.isfinite(lst_night)
    lst_day_night = np.full(lst_day.shape, np.nan, dtype=np.float64)
    np.subtract(lst_day, lst_night, out=lst_day_night, where=paired)
    del lst_day, lst_night
    lst_day_night_median, lst_day_night_count = block_median(lst_day_night, modis_factor)
    del lst_day_night
    land_count = (
        land.reshape(land.shape[0] // modis_factor, modis_factor, land.shape[1] // modis_factor, modis_factor)
        .transpose(0, 2, 1, 3)
        .reshape(lst_night_median.shape[0], lst_night_median.shape[1], modis_factor * modis_factor)
        .sum(axis=2)
        .astype(np.int32)
    )
    precip_median, precip_count = block_median(precip, imerg_factor)

    if land_count.shape != precip_median.shape:
        raise SystemExit(
            f"Land grid {land_count.shape} does not match precipitation grid {precip_median.shape}."
        )

    keep = land_count > 0
    lat, lon = cell_centers(*land_count.shape)
    n_land = int(keep.sum())
    south = lat < -60.0
    south_land = int((keep & south).sum())
    south_ndvi_blank = int((keep & south & ~np.isfinite(ndvi_median)).sum())
    ndvi_south_note = (
        f"Of the land cells south of 60°S, {south_ndvi_blank} of {south_land} "
        "have a blank NDVI. That month’s gap, not a dropped column, is why "
        "`ndvi_median` is blank on a large share of the table."
    )

    frame = pd.DataFrame(
        {
            "lat_center_deg": np.round(lat[keep], 1),
            "lon_center_deg": np.round(lon[keep], 1),
            "ndvi_median": ndvi_median[keep],
            "ndvi_valid_count": ndvi_count[keep],
            "lst_day_median_k": lst_day_median[keep],
            "lst_day_valid_count": lst_day_count[keep],
            "lst_night_median_k": lst_night_median[keep],
            "lst_night_valid_count": lst_night_count[keep],
            "lst_day_night_range_median_k": lst_day_night_median[keep],
            "lst_day_night_range_valid_count": lst_day_night_count[keep],
            "precip_median_mm_hr": precip_median[keep],
            "precip_valid_count": precip_count[keep],
            "land_pixel_count": land_count[keep],
            "slope_median_deg": np.full(n_land, np.nan),
            "slope_valid_count": pd.array([pd.NA] * n_land, dtype="Int64"),
        }
    )
    for column in (
        "ndvi_valid_count",
        "lst_day_valid_count",
        "lst_night_valid_count",
        "lst_day_night_range_valid_count",
        "precip_valid_count",
        "land_pixel_count",
        "slope_valid_count",
    ):
        frame[column] = frame[column].astype("Int64")

    value_columns = [
        "lat_center_deg",
        "lon_center_deg",
        "ndvi_median",
        "ndvi_valid_count",
        "lst_day_median_k",
        "lst_day_valid_count",
        "lst_night_median_k",
        "lst_night_valid_count",
        "lst_day_night_range_median_k",
        "lst_day_night_range_valid_count",
        "precip_median_mm_hr",
        "precip_valid_count",
        "land_pixel_count",
        "slope_median_deg",
        "slope_valid_count",
    ]
    percents = [(name, null_percent(frame[name])) for name in value_columns]
    frame["lat_center_deg"] = frame["lat_center_deg"].map(lambda value: f"{value:.1f}")
    frame["lon_center_deg"] = frame["lon_center_deg"].map(lambda value: f"{value:.1f}")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        out_csv,
        index=False,
        na_rep="",
        float_format="%.6f",
        columns=value_columns,
    )
    if args.year is not None:
        monthly_manifest = {
            "method_version": "monthly-cell-grid-v1",
            "period": {"year": year, "month": month},
            "feature_table": out_csv.relative_to(ROOT).as_posix(),
            "feature_table_sha256": sha256_file(out_csv),
            "quality_filters": {
                "MOD13C2_VI_quality": "not applied",
                "MOD11C3_QC_Day_and_QC_Night": "not applied",
            },
            "raw_inputs": [
                {
                    "filename": path.name,
                    "sha256": sha256_file(path),
                }
                for path in input_files
            ],
        }
        manifest_path = out_csv.parent / "manifest.json"
        manifest_path.write_text(
            json.dumps(monthly_manifest, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    write_notes(
        ndvi_file,
        lst_file,
        precip_file,
        out_md,
        year,
        month,
        n_land,
        percents,
        ndvi_scale_text,
        lst_day_scale_text,
        lst_night_scale_text,
        precip_fill,
        ndvi_south_note,
    )

    print(f"Land cells: {n_land}")
    print("Percent null:")
    for name, pct in percents:
        print(f"  {name}: {pct:.2f}%")
    print(f"Wrote {out_csv.relative_to(ROOT).as_posix()}")
    print(f"Wrote {out_md.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
