"""Download complete monthly NASA granule sets through Earthdata Login."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Callable
from urllib.parse import unquote, urlparse

import earthaccess

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
HDF4_SIGNATURE = b"\x0e\x03\x13\x01"
HDF5_SIGNATURE = b"\x89HDF\r\n\x1a\n"
PRODUCTS = (
    ("MOD13C2", "061"),
    ("MOD11C3", "061"),
    ("GPM_3IMERGM", "07"),
)


def _month_range(start_year: int, end_year: int) -> list[tuple[int, int]]:
    if start_year < 2000 or end_year < start_year:
        raise ValueError("Years must be ordered and start no earlier than 2000.")
    return [
        (year, month)
        for year in range(start_year, end_year + 1)
        for month in range(1, 13)
    ]


def _expected_prefix(product: str, year: int, month: int) -> str:
    if product == "GPM_3IMERGM":
        return f"3B-MO.MS.MRG.3IMERG.{year}{month:02d}01-S000000-E235959."
    doy = date(year, month, 1).timetuple().tm_yday
    return f"{product}.A{year}{doy:03d}.061."


def _granule_month(granule: earthaccess.DataGranule) -> tuple[int, int]:
    try:
        beginning = granule["umm"]["TemporalExtent"]["RangeDateTime"][
            "BeginningDateTime"
        ]
        parsed = date.fromisoformat(beginning[:10])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("CMR granule is missing a valid beginning date.") from exc
    return parsed.year, parsed.month


def resolve_monthly_granules(
    start_year: int,
    end_year: int,
    search_data: Callable[..., list[earthaccess.DataGranule]] | None = None,
) -> list[earthaccess.DataGranule]:
    """Resolve exactly one correctly dated granule for each product and month."""
    if search_data is None:
        search_data = earthaccess.search_data
    months = _month_range(start_year, end_year)
    expected_months = set(months)
    granules = []
    for short_name, version in PRODUCTS:
        matches = search_data(
            short_name=short_name,
            version=version,
            temporal=(f"{start_year:04d}-01", f"{end_year:04d}-12"),
            count=len(months) + 1,
        )
        by_month = {}
        for granule in matches:
            month_key = _granule_month(granule)
            if month_key not in expected_months:
                raise ValueError(
                    f"CMR returned an out-of-range {short_name} granule for "
                    f"{month_key[0]:04d}-{month_key[1]:02d}."
                )
            if month_key in by_month:
                raise ValueError(
                    f"CMR returned multiple {short_name} granules for "
                    f"{month_key[0]:04d}-{month_key[1]:02d}."
                )
            by_month[month_key] = granule

        missing = sorted(expected_months - by_month.keys())
        if missing:
            rendered = ", ".join(f"{year:04d}-{month:02d}" for year, month in missing)
            raise ValueError(f"CMR is missing {short_name} granules for: {rendered}.")

        for year, month in months:
            granule = by_month[(year, month)]
            links = granule.data_links()
            if len(links) != 1:
                raise ValueError(
                    f"Expected exactly one data link for {short_name} "
                    f"{year:04d}-{month:02d}; found {len(links)}."
                )
            filename = PurePosixPath(unquote(urlparse(links[0]).path)).name
            if not filename.startswith(_expected_prefix(short_name, year, month)):
                raise ValueError(
                    f"CMR returned an unexpected {short_name} filename for "
                    f"{year:04d}-{month:02d}: {filename}"
                )
            granules.append(granule)
    return granules


def _login_locally() -> None:
    if os.environ.get("EARTHDATA_TOKEN") or (
        os.environ.get("EARTHDATA_USERNAME")
        and os.environ.get("EARTHDATA_PASSWORD")
    ):
        strategy = "environment"
    else:
        configured_netrc = os.environ.get("NETRC")
        netrc_paths = (
            [Path(configured_netrc)]
            if configured_netrc
            else [Path.home() / "_netrc", Path.home() / ".netrc"]
        )
        if not any(path.is_file() for path in netrc_paths):
            raise RuntimeError(
                "No local Earthdata credentials found. Configure EARTHDATA_TOKEN, "
                "EARTHDATA_USERNAME and EARTHDATA_PASSWORD, or a Windows _netrc "
                "file. Do not put credentials in the repository or command history."
            )
        strategy = "netrc"
    earthaccess.login(strategy=strategy, persist=False)


def verify_downloads(
    granules: list[earthaccess.DataGranule], raw_root: Path = RAW
) -> None:
    for granule in granules:
        links = granule.data_links()
        if len(links) != 1:
            raise ValueError(
                f"Expected exactly one data link after download; found {len(links)}."
            )
        filename = PurePosixPath(unquote(urlparse(links[0]).path)).name
        path = raw_root / filename
        if not path.is_file():
            raise FileNotFoundError(f"Downloaded NASA granule is missing: {path}")
        with path.open("rb") as stream:
            signature = stream.read(8)
        expected_signature = (
            HDF5_SIGNATURE if filename.lower().endswith(".hdf5") else HDF4_SIGNATURE
        )
        if not signature.startswith(expected_signature):
            raise ValueError(f"{path} does not have the expected HDF signature.")

        expected_size_mb = float(granule.size)
        actual_size = path.stat().st_size
        actual_size_mb = actual_size / 1_000_000
        actual_size_mib = actual_size / (1024 * 1024)
        size_error = min(
            abs(actual_size_mb - expected_size_mb),
            abs(actual_size_mib - expected_size_mb),
        )
        if size_error > max(0.02, expected_size_mb * 0.002):
            raise ValueError(
                f"{path} size does not match CMR metadata "
                f"({actual_size} bytes; expected about {expected_size_mb:.4f} MB)."
            )


def download_range(
    start_year: int, end_year: int, raw_root: Path = RAW
) -> int:
    granules = resolve_monthly_granules(start_year, end_year)
    expected_count = (end_year - start_year + 1) * 12 * len(PRODUCTS)
    if len(granules) != expected_count:
        raise ValueError(
            f"Resolved {len(granules)} granules; expected {expected_count}."
        )

    _login_locally()
    raw_root.mkdir(parents=True, exist_ok=True)
    earthaccess.download(granules, local_path=raw_root, threads=4, force=False)
    verify_downloads(granules, raw_root)
    return len(granules)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download complete MODIS and IMERG monthly granule sets."
    )
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    args = parser.parse_args()

    try:
        count = download_range(args.start_year, args.end_year)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Stopping: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        f"Downloaded and verified {count} NASA granules for "
        f"{args.start_year}-{args.end_year}."
    )


if __name__ == "__main__":
    main()
