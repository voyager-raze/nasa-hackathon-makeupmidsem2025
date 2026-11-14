"""Build the coarse land-cell measurement table.

Reads only the June 2024 granules named in notes/data-log.md:

- data/raw/MOD13C2.A2024153.061.2024198104950.hdf
- data/raw/MOD11C3.A2024153.061.2024187024328.hdf
- data/raw/3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5

Writes data/processed/features.csv and notes/features.md.
Does not score, rank, or choose a site. Slope stays blank: the data log
records that no elevation file was downloaded.
"""

from __future__ import annotations

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


def require_files() -> None:
    missing = [str(path) for path in (NDVI_FILE, LST_FILE, PRECIP_FILE) if not path.is_file()]
    if missing:
        print("Stopping. Logged measurement files are missing:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        sys.exit(1)


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


def read_ndvi() -> tuple[np.ndarray, str]:
    hdf = SD(str(NDVI_FILE), SDC.READ)
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


def read_lst_and_land() -> tuple[np.ndarray, np.ndarray, str]:
    hdf = SD(str(LST_FILE), SDC.READ)
    try:
        lst_raw, lst_attrs = sds_array(hdf, "LST_Night_CMG")
        land_raw, land_attrs = sds_array(hdf, "Percent_land_in_grid")
    finally:
        hdf.end()
    if lst_raw.shape != (3600, 7200) or land_raw.shape != (3600, 7200):
        raise SystemExit("LST or land-fraction shape is not the 0.05° CMG.")
    lst, scaled_as = apply_modis_scale(lst_raw, lst_attrs, "lst")
    finite = lst[np.isfinite(lst)]
    if finite.size == 0 or not (150.0 <= float(np.median(finite)) <= 350.0):
        raise SystemExit("Night LST scale check failed. Stopping without writing a table.")

    fill = int(land_attrs["_FillValue"])
    valid_min, valid_max = (int(v) for v in land_attrs["valid_range"])
    land = (land_raw != fill) & (land_raw >= valid_min) & (land_raw <= valid_max)
    return lst, land, scaled_as


def read_precip() -> tuple[np.ndarray, str]:
    with h5py.File(PRECIP_FILE, "r") as handle:
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
    n_land: int,
    percents: list[tuple[str, float]],
    ndvi_scale_text: str,
    lst_scale_text: str,
    precip_fill: str,
    ndvi_south_note: str,
) -> None:
    ns_km = CELL_DEG * KM_PER_DEG
    percent_lines = "\n".join(f"| `{name}` | {pct:.2f}% |" for name, pct in percents)
    text = f"""# Feature grid

One row in `data/processed/features.csv` is one land cell. This file defines every column. It does not weight cells and it does not rank them.

June 2024 is one month. It is summer in the north and winter in the south. These columns are not a climate normal.

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
| `ndvi_median` | NDVI (native index) | `{NDVI_FILE.relative_to(ROOT).as_posix()}` layer `CMG 0.05 Deg Monthly NDVI` | {ndvi_scale_text}. Then the median of the finite pixels in the cell. |
| `ndvi_valid_count` | count of 0.05° pixels | same NDVI layer | pixels that are not `_FillValue` (−3000) and lie inside `valid_range` (−2000 to 10000). |
| `lst_night_median_k` | kelvin | `{LST_FILE.relative_to(ROOT).as_posix()}` layer `LST_Night_CMG` | {lst_scale_text}. Then the median of the finite pixels in the cell. This is the one temperature summary. `LST_Day_CMG` was not reduced into a second column. |
| `lst_night_valid_count` | count of 0.05° pixels | same night LST layer | pixels that are not `_FillValue` (0) and lie inside `valid_range` (7500 to 65535). |
| `precip_median_mm_hr` | mm/hr | `{PRECIP_FILE.relative_to(ROOT).as_posix()}` dataset `Grid/precipitation` | median of finite pixels. The file unit is mm/hr. `BinMethod=ARITHMETIC_MEAN` and `TimeInterval=MONTH`, so the stored value is already the June mean rate. It was not converted to a monthly millimetre total. This is the dryness measurement, left in the product unit. A lower rate is drier. |
| `precip_valid_count` | count of 0.1° pixels | same precipitation dataset | pixels that are not the fill value ({precip_fill}). |
| `land_pixel_count` | count of 0.05° pixels | `{LST_FILE.relative_to(ROOT).as_posix()}` layer `Percent_land_in_grid` | pixels inside `valid_range` 1 to 100. This is the land test, not an analog feature. |
| `slope_median_deg` | degrees | no file | not computed. Entirely blank. |
| `slope_valid_count` | count | no file | not computed. Entirely blank. |

{ndvi_south_note}

When a valid count is even, the median is the arithmetic mean of the two central values (NumPy `nanmedian`). The same rule is used for every cell of a column.

`land_pixel_count` is a coverage count. It is not vegetation, temperature, dryness, or slope, and it is not a score.

## What this table is not

No column is a weight, a rank, or a site choice. Slope was not filled from the locked lunar band. Missing vegetation, night temperature, or precipitation was not copied from a neighboring cell.
"""
    OUT_MD.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    require_files()
    if abs(CELL_DEG / MODIS_DEG - round(CELL_DEG / MODIS_DEG)) > 1e-9:
        raise SystemExit("Cell size does not tile the MODIS grid.")

    ndvi, ndvi_scale_text = read_ndvi()
    lst, land, lst_scale_text = read_lst_and_land()
    precip, precip_fill = read_precip()

    modis_factor = int(round(CELL_DEG / MODIS_DEG))
    imerg_factor = int(round(CELL_DEG / 0.1))

    ndvi_median, ndvi_count = block_median(ndvi, modis_factor)
    lst_median, lst_count = block_median(lst, modis_factor)
    land_count = (
        land.reshape(land.shape[0] // modis_factor, modis_factor, land.shape[1] // modis_factor, modis_factor)
        .transpose(0, 2, 1, 3)
        .reshape(ndvi_median.shape[0], ndvi_median.shape[1], modis_factor * modis_factor)
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
        "have a blank NDVI. That June gap, not a dropped column, is why "
        "`ndvi_median` is blank on a large share of the table."
    )

    frame = pd.DataFrame(
        {
            "lat_center_deg": np.round(lat[keep], 1),
            "lon_center_deg": np.round(lon[keep], 1),
            "ndvi_median": ndvi_median[keep],
            "ndvi_valid_count": ndvi_count[keep],
            "lst_night_median_k": lst_median[keep],
            "lst_night_valid_count": lst_count[keep],
            "precip_median_mm_hr": precip_median[keep],
            "precip_valid_count": precip_count[keep],
            "land_pixel_count": land_count[keep],
            "slope_median_deg": np.full(n_land, np.nan),
            "slope_valid_count": pd.array([pd.NA] * n_land, dtype="Int64"),
        }
    )
    for column in (
        "ndvi_valid_count",
        "lst_night_valid_count",
        "precip_valid_count",
        "land_pixel_count",
    ):
        frame[column] = frame[column].astype("Int64")

    value_columns = [
        "lat_center_deg",
        "lon_center_deg",
        "ndvi_median",
        "ndvi_valid_count",
        "lst_night_median_k",
        "lst_night_valid_count",
        "precip_median_mm_hr",
        "precip_valid_count",
        "land_pixel_count",
        "slope_median_deg",
        "slope_valid_count",
    ]
    percents = [(name, null_percent(frame[name])) for name in value_columns]
    frame["lat_center_deg"] = frame["lat_center_deg"].map(lambda value: f"{value:.1f}")
    frame["lon_center_deg"] = frame["lon_center_deg"].map(lambda value: f"{value:.1f}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        OUT_CSV,
        index=False,
        na_rep="",
        float_format="%.6f",
        columns=value_columns,
    )
    write_notes(
        n_land,
        percents,
        ndvi_scale_text,
        lst_scale_text,
        precip_fill,
        ndvi_south_note,
    )

    print(f"Land cells: {n_land}")
    print("Percent null:")
    for name, pct in percents:
        print(f"  {name}: {pct:.2f}%")
    print(f"Wrote {OUT_CSV.relative_to(ROOT).as_posix()}")
    print(f"Wrote {OUT_MD.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
