"""June 2024 nighttime-LST medians for the two candidate cells under QC tiers.

Reads the 4x4 pixel blocks already saved by src/inspect_mod11c3_qc.py in
results/qc_robustness/hdf_inspection.json (so it needs neither the HDF file nor pyhdf).
Writes three small CSVs next to it. It does not touch the scoring code, features.csv
or any existing result.

    python src/qc_site_tiers.py

What the numbers are: the median of the kept pixels' LST in kelvin, using the same
median rule as the project (a median of the valid pixels, scaled by 0.02). A tier that
keeps no pixel gives an empty median: missing is never turned into 0.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

from mod11c3_qc import (EXPLORATORY_TIERS, LST_SCALE, TIERS, decode_qc, tier_mask, to_kelvin)

JSON_PATH = Path("results/qc_robustness/hdf_inspection.json")
OUT_DIR = Path("results/qc_robustness")
# Reproduction check only: the project's published unfiltered medians (T0).
PUBLISHED_T0 = {"Kunlun": 258.80, "Vinchina": 254.45}
ALL_TIERS = {**TIERS, **EXPLORATORY_TIERS}


def _arrays(lst_raw, qc_raw):
    lst = np.asarray(lst_raw, dtype=np.int64)
    qc = np.asarray(qc_raw, dtype=np.int64)
    if lst.shape != qc.shape:
        raise ValueError("LST and QC blocks have different shapes")
    if lst.min() < 0 or lst.max() > 65535 or qc.min() < 0 or qc.max() > 255:
        raise ValueError("raw values outside uint16 (LST) / uint8 (QC) range")
    return lst.astype(np.uint16), qc.astype(np.uint8)


def tier_summary(site, lst_raw, qc_raw, fill_value=0, valid_range=(7500, 65535)):
    """One row per tier: pixels kept/lost and the median of the kept pixels."""
    lst, qc = _arrays(lst_raw, qc_raw)
    rows, base = [], None
    for tier, desc in ALL_TIERS.items():
        mask = tier_mask(qc, lst, tier, fill_value, valid_range)
        kelvin = to_kelvin(lst, mask)[mask]
        n_kept, n_t0 = int(mask.sum()), int(tier_mask(qc, lst, "T0", fill_value, valid_range).sum())
        median = round(float(np.median(kelvin)), 4) if n_kept else None
        if tier == "T0":
            base = median
        rows.append({
            "tier": tier, "kind": "primary" if tier in TIERS else "exploratory", "site": site,
            "n_pixels": int(lst.size), "n_kept": n_kept, "n_lost_vs_t0": n_t0 - n_kept,
            "median_k": median,
            "delta_vs_t0_k": None if median is None or base is None else round(median - base, 4),
            "min_k": round(float(kelvin.min()), 4) if n_kept else None,
            "max_k": round(float(kelvin.max()), 4) if n_kept else None,
            "description": desc})
    return rows


def pixel_table(site, lst_raw, qc_raw, fill_value=0, valid_range=(7500, 65535)):
    """One row per pixel with its decoded QC fields and tier membership (audit trail)."""
    lst, qc = _arrays(lst_raw, qc_raw)
    fields = decode_qc(qc)
    masks = {t: tier_mask(qc, lst, t, fill_value, valid_range) for t in ALL_TIERS}
    rows = []
    for i in range(lst.size):
        idx = np.unravel_index(i, lst.shape)
        row = {"site": site, "row_in_block": int(idx[0]), "col_in_block": int(idx[1]),
               "lst_raw": int(lst[idx]), "lst_k": round(float(lst[idx]) * LST_SCALE, 4), "qc": int(qc[idx])}
        row.update({k: int(v[idx]) for k, v in fields.items()})
        row.update({f"keep_{t}": int(m[idx]) for t, m in masks.items()})
        rows.append(row)
    return rows


def gap_table(summaries):
    """Vinchina minus Kunlun median per tier, and how much it moved vs T0."""
    by = {(r["site"], r["tier"]): r for rows in summaries.values() for r in rows}
    out, base = [], None
    for tier in ALL_TIERS:
        v, k = by[("Vinchina", tier)]["median_k"], by[("Kunlun", tier)]["median_k"]
        gap = None if v is None or k is None else round(v - k, 4)
        if tier == "T0":
            base = gap
        out.append({"tier": tier, "vinchina_median_k": v, "kunlun_median_k": k, "gap_k": gap,
                    "gap_change_vs_t0_k": None if gap is None or base is None else round(gap - base, 4)})
    return out


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def run(json_path=JSON_PATH, out_dir=OUT_DIR, published=PUBLISHED_T0):
    rep = json.loads(Path(json_path).read_text())
    attrs = rep["datasets"]["LST_Night_CMG"]["attrs"]
    fill, vrange = attrs["_FillValue"], tuple(attrs["valid_range"])
    summaries, pixels = {}, []
    for site, blk in rep["sites"].items():
        summaries[site] = tier_summary(site, blk["lst_raw"], blk["qc_raw"], fill, vrange)
        pixels += pixel_table(site, blk["lst_raw"], blk["qc_raw"], fill, vrange)
        t0 = summaries[site][0]["median_k"]
        if site in published and (t0 is None or abs(t0 - published[site]) > 0.005):
            raise SystemExit(f"T0 for {site} is {t0}, published {published[site]}: investigate before using any tier")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "site_tiers_june2024.csv", [r for rows in summaries.values() for r in rows])
    _write(out_dir / "site_pixels_june2024.csv", pixels)
    gaps = gap_table(summaries) if {"Kunlun", "Vinchina"} <= set(summaries) else []
    if gaps:
        _write(out_dir / "site_gap_june2024.csv", gaps)
    return summaries, gaps


def main():
    summaries, gaps = run(sys.argv[1] if len(sys.argv) > 1 else JSON_PATH)
    print(f"{'tier':4} {'site':9} {'kept':>6} {'median_K':>9} {'delta_K':>8}")
    for rows in summaries.values():
        for r in rows:
            m = "n/a" if r["median_k"] is None else f"{r['median_k']:.2f}"
            d = "n/a" if r["delta_vs_t0_k"] is None else f"{r['delta_vs_t0_k']:+.2f}"
            print(f"{r['tier']:4} {r['site']:9} {r['n_kept']:>3}/{r['n_pixels']:<2} {m:>9} {d:>8}")
    print("\nVinchina minus Kunlun (K):")
    for g in gaps:
        print(" ", g["tier"], "n/a" if g["gap_k"] is None else f"{g['gap_k']:+.2f}")
    print("\nwrote site_tiers_june2024.csv, site_pixels_june2024.csv, site_gap_june2024.csv in", OUT_DIR)


if __name__ == "__main__":
    main()
