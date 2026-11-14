"""Build a contiguous sequence of monthly grids from locally available granules."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_features import monthly_input_files


def plan_months(
    start_year: int, end_year: int
) -> tuple[list[tuple[int, int]], list[str]]:
    months = []
    missing = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            try:
                monthly_input_files(year, month)
            except SystemExit as exc:
                missing.append(f"{year:04d}-{month:02d}: {exc}")
            else:
                months.append((year, month))
    return months, missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build every monthly feature grid in a year range."
    )
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    args = parser.parse_args()
    if args.start_year < 2000 or args.end_year < args.start_year:
        parser.error("Years must be ordered and start no earlier than 2000.")

    months, missing = plan_months(args.start_year, args.end_year)
    if missing:
        details = "\n".join(f"  {item}" for item in missing)
        raise SystemExit(
            f"Stopping before processing. {len(missing)} monthly granule sets are incomplete:\n"
            f"{details}"
        )

    command_base = [
        sys.executable,
        str(ROOT / "src" / "build_features.py"),
    ]
    for year, month in months:
        subprocess.run(
            [
                *command_base,
                "--year",
                str(year),
                "--month",
                str(month),
            ],
            check=True,
            cwd=ROOT,
        )

    print(f"Built {len(months)} monthly feature grids for {args.start_year}-{args.end_year}.")


if __name__ == "__main__":
    main()
