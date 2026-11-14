"""Median slope on the two chosen 0.2 degree cells.

Reads Copernicus DEM GLO-30 cloud-optimized GeoTIFFs. Writes one elevation
patch per site under data/raw/. Prints the median slope. Does not edit
notes/targets.md, results/top5.csv, or the weights.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif"
os.environ["GDAL_HTTP_TIMEOUT"] = "180"
os.environ["GDAL_HTTP_MAX_RETRY"] = "3"

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
from rasterio.transform import array_bounds

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CELL_DEG = 0.2

# Public Copernicus DEM GLO-30 COGs. One degree tile, 1 arc-second.
COP_BASE = "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com"


def tile_url(lat: float, lon: float) -> str:
    """Tile whose southwest corner is the floor of the coordinate."""
    lat_sw = math.floor(lat)
    lon_sw = math.floor(lon)
    lat_tag = f"{'N' if lat_sw >= 0 else 'S'}{abs(lat_sw):02d}_00"
    lon_tag = f"{'E' if lon_sw >= 0 else 'W'}{abs(lon_sw):03d}_00"
    name = f"Copernicus_DSM_COG_10_{lat_tag}_{lon_tag}_DEM"
    return f"{COP_BASE}/{name}/{name}.tif"


def meters_per_degree(lat_deg: float) -> tuple[float, float]:
    """WGS84 meridional and parallel radii, metres per degree, at lat_deg."""
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


def read_window(lat: float, lon: float) -> dict:
    half = CELL_DEG / 2.0
    south, north = lat - half, lat + half
    west, east = lon - half, lon + half
    # Pad by a little more than one pixel so the slope gradient is centered
    # on every pixel whose center lies inside the cell.
    pad = 0.0006
    url = tile_url(lat, lon)
    with rasterio.open("/vsicurl/" + url) as src:
        if src.crs is None or src.crs.to_epsg() != 4326:
            raise SystemExit(f"{url} is not EPSG:4326. Slope was not computed.")
        window = from_bounds(west - pad, south - pad, east + pad, north + pad, src.transform)
        window = window.round_offsets().round_lengths()
        # Clip to the tile. A cell that crosses a tile edge is reported, not guessed.
        full = Window(0, 0, src.width, src.height)
        clipped = window.intersection(full)
        if clipped.width < 100 or clipped.height < 100:
            raise SystemExit(
                f"The cell at {lat}, {lon} is outside {url}. "
                f"Tile bounds are {src.bounds}. Slope was not computed."
            )
        elev = src.read(1, window=clipped).astype(np.float64)
        transform = src.window_transform(clipped)
        res_lon, res_lat = src.res
        nodata = src.nodata
    if nodata is not None:
        elev[elev == nodata] = np.nan
    elev[elev < -500] = np.nan
    elev[elev > 9000] = np.nan

    rows = np.arange(elev.shape[0])
    cols = np.arange(elev.shape[1])
    # Pixel-center coordinates from the window transform.
    lon_centers = transform.c + (cols + 0.5) * transform.a + (rows[0] + 0.5) * transform.b
    # transform.b is the row rotation, normally 0. Longitude does not depend on row.
    lon_centers = transform.c + (cols + 0.5) * transform.a
    lat_centers = transform.f + (rows + 0.5) * transform.e
    inside = (
        (lat_centers[:, None] >= south)
        & (lat_centers[:, None] < north)
        & (lon_centers[None, :] >= west)
        & (lon_centers[None, :] < east)
    )
    # Slope needs a neighbor on every side, so the median uses interior pixels only.
    interior = np.zeros_like(inside)
    interior[1:-1, 1:-1] = inside[1:-1, 1:-1]

    m_lat, m_lon = meters_per_degree(lat)
    dy = abs(res_lat) * m_lat
    dx = abs(res_lon) * m_lon
    # Row 0 is north. A step to the next row moves south, so northing decreases.
    dz_drow, dz_dcol = np.gradient(elev, -dy, dx)
    slope = np.degrees(np.arctan(np.hypot(dz_drow, dz_dcol)))
    slope[~np.isfinite(elev)] = np.nan
    used = slope[interior & np.isfinite(slope)]
    if used.size == 0:
        raise SystemExit(f"No finite slope pixels inside {lat}, {lon}.")

    # Elevation patch saved for the cell only, not the gradient pad.
    cell_rows = np.where(inside.any(axis=1))[0]
    cell_cols = np.where(inside.any(axis=0))[0]
    r0, r1 = int(cell_rows[0]), int(cell_rows[-1]) + 1
    c0, c1 = int(cell_cols[0]), int(cell_cols[-1]) + 1
    patch = elev[r0:r1, c0:c1]
    patch_transform = rasterio.Affine(
        transform.a,
        transform.b,
        transform.c + c0 * transform.a,
        transform.d,
        transform.e,
        transform.f + r0 * transform.e,
    )
    return {
        "url": url,
        "south": south,
        "north": north,
        "west": west,
        "east": east,
        "pixel_m_lat": dy,
        "pixel_m_lon": dx,
        "n_slope": int(used.size),
        "slope_median_deg": float(np.median(used)),
        "slope_p25_deg": float(np.percentile(used, 25)),
        "slope_p75_deg": float(np.percentile(used, 75)),
        "elev_median_m": float(np.nanmedian(patch)),
        "patch": patch,
        "patch_transform": patch_transform,
        "res_deg": abs(res_lon),
    }


def write_patch(path: Path, result: dict) -> None:
    patch = result["patch"]
    profile = {
        "driver": "GTiff",
        "height": patch.shape[0],
        "width": patch.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": result["patch_transform"],
        "compress": "deflate",
        "nodata": -32768.0,
    }
    out = patch.astype(np.float32)
    out[~np.isfinite(out)] = -32768.0
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(out, 1)
        dst.update_tags(
            source_url=result["url"],
            cell_south=str(result["south"]),
            cell_north=str(result["north"]),
            cell_west=str(result["west"]),
            cell_east=str(result["east"]),
        )


def main() -> None:
    sites = {
        "site_a": (35.3, 81.1, RAW / "cop30_N35.3_E81.1.tif"),
        "site_b": (-27.9, -68.9, RAW / "cop30_S27.9_W68.9.tif"),
    }
    summary = {}
    for key, (lat, lon, path) in sites.items():
        result = read_window(lat, lon)
        write_patch(path, result)
        left, bottom, right, top = array_bounds(
            result["patch"].shape[0],
            result["patch"].shape[1],
            result["patch_transform"],
        )
        summary[key] = {
            "lat": lat,
            "lon": lon,
            "url": result["url"],
            "local_tile": path.relative_to(ROOT).as_posix(),
            "cell_bounds": [result["west"], result["south"], result["east"], result["north"]],
            "patch_bounds": [left, bottom, right, top],
            "patch_shape": list(result["patch"].shape),
            "pixel_m_lat": result["pixel_m_lat"],
            "pixel_m_lon": result["pixel_m_lon"],
            "n_slope": result["n_slope"],
            "slope_median_deg": result["slope_median_deg"],
            "slope_p25_deg": result["slope_p25_deg"],
            "slope_p75_deg": result["slope_p75_deg"],
            "elev_median_m": result["elev_median_m"],
        }
        print(
            f"{key} median slope {result['slope_median_deg']:.2f} deg "
            f"from {result['n_slope']} pixels, elevation median {result['elev_median_m']:.1f} m"
        )
    out = ROOT / "results" / "slope-patches.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
