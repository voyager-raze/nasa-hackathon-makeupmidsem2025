"""Median slope from the two local elevation patches.

Reads data/raw/cop30_N35.3_E81.1.tif and data/raw/cop30_S27.9_W68.9.tif.
Updates the slope and elevation rows in results/sources.csv.
Does not edit notes/targets.md, results/top5.csv, or the weights.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SOURCES = ROOT / "results" / "sources.csv"

SITES = (
    {"lat": 35.3, "lon": 81.1, "path": RAW / "cop30_N35.3_E81.1.tif"},
    {"lat": -27.9, "lon": -68.9, "path": RAW / "cop30_S27.9_W68.9.tif"},
)

HEADER = [
    "quantity",
    "value",
    "unit",
    "dataset",
    "version",
    "date range",
    "url",
    "patch longitude",
    "patch latitude",
    "patch size",
    "method",
]


def meters_per_degree(lat_deg: float) -> tuple[float, float]:
    """WGS84 meridional and parallel scale, metres per degree, at lat_deg."""
    lat = math.radians(lat_deg)
    m_lat = (
        111132.92
        - 559.82 * math.cos(2 * lat)
        + 1.175 * math.cos(4 * lat)
        - 0.0023 * math.cos(6 * lat)
    )
    m_lon = (
        111412.84 * math.cos(lat)
        - 93.5 * math.cos(3 * lat)
        + 0.118 * math.cos(5 * lat)
    )
    return m_lat, m_lon


def measure(path: Path, lat: float) -> dict:
    if not path.is_file():
        raise SystemExit(f"Missing elevation tile {path}. Slope was not computed.")
    with rasterio.open(path) as src:
        elev = src.read(1).astype(np.float64)
        nodata = src.nodata
        res_lon, res_lat = src.res
        source_url = src.tags().get("source_url", "")
    if nodata is not None:
        elev[np.isclose(elev, nodata)] = np.nan
    elev[elev < -500] = np.nan
    elev[elev > 9000] = np.nan
    finite = np.isfinite(elev)
    if int(finite.sum()) == 0:
        raise SystemExit(f"No finite elevation in {path}. Slope was not computed.")

    m_lat, m_lon = meters_per_degree(lat)
    dy = abs(res_lat) * m_lat
    dx = abs(res_lon) * m_lon
    # Row 0 is north. A step to the next row moves south, so northing decreases.
    dz_drow, dz_dcol = np.gradient(elev, -dy, dx)
    slope = np.degrees(np.arctan(np.hypot(dz_drow, dz_dcol)))
    slope[~finite] = np.nan
    interior = np.isfinite(slope)
    interior[0, :] = False
    interior[-1, :] = False
    interior[:, 0] = False
    interior[:, -1] = False
    used = slope[interior]
    if used.size == 0:
        raise SystemExit(f"No finite slope pixels in {path}.")
    return {
        "slope": float(np.median(used)),
        "n": int(used.size),
        "elevation": float(np.nanmedian(elev)),
        "dy": dy,
        "dx": dx,
        "url": source_url,
        "tile": path.relative_to(ROOT).as_posix(),
    }


def coord_key(lat: str, lon: str) -> tuple[float, float]:
    return (round(float(lat), 1), round(float(lon), 1))


def upsert(measured: list[tuple[dict, dict]]) -> None:
    if not SOURCES.is_file():
        raise SystemExit(f"Missing {SOURCES}. Slope rows were not written.")
    with SOURCES.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and list(rows[0]) != HEADER and set(HEADER) - set(rows[0]):
        raise SystemExit(f"{SOURCES} is missing required columns. Nothing was written.")

    for site, stats in measured:
        lat = f"{site['lat']:.1f}"
        lon = f"{site['lon']:.1f}"
        slope_value = f"{stats['slope']:.2f}"
        elev_value = f"{stats['elevation']:.1f}"
        slope_method = (
            f"median slope of finite interior 1 arc-second pixels in {stats['tile']}; "
            f"numpy.gradient; pixel spacing {stats['dy']:.2f} m north-south and "
            f"{stats['dx']:.2f} m east-west; {stats['n']} pixels; "
            f"rounded from {stats['slope']:.3f} degrees; src/local_slope.py"
        )
        elev_method = (
            f"median of finite elevation pixels in {stats['tile']}; "
            f"rounded from {stats['elevation']:.3f} m; src/local_slope.py"
        )
        updates = {
            "slope_median_deg": (slope_value, "degrees", slope_method),
            "elevation_median": (elev_value, "m", elev_method),
        }
        for quantity, (value, unit, method) in updates.items():
            matches = [
                row
                for row in rows
                if row["quantity"] == quantity and coord_key(row["patch latitude"], row["patch longitude"]) == (site["lat"], site["lon"])
            ]
            if matches:
                row = matches[0]
                row["value"] = value
                row["unit"] = unit
                row["method"] = method
                if stats["url"]:
                    row["url"] = stats["url"]
            else:
                rows.append(
                    {
                        "quantity": quantity,
                        "value": value,
                        "unit": unit,
                        "dataset": "Copernicus DEM",
                        "version": "GLO-30 Public",
                        "date range": "2021 release",
                        "url": stats["url"],
                        "patch longitude": lon,
                        "patch latitude": lat,
                        "patch size": "0.2 deg x 0.2 deg",
                        "method": method,
                    }
                )
    with SOURCES.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    measured = []
    for site in SITES:
        stats = measure(site["path"], site["lat"])
        measured.append((site, stats))
        print(
            f"{site['lat']:.1f}, {site['lon']:.1f}: "
            f"median slope {stats['slope']:.2f} degrees "
            f"from {stats['n']} pixels, "
            f"elevation median {stats['elevation']:.1f} m"
        )
    upsert(measured)
    print(f"Updated slope and elevation rows in {SOURCES.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
