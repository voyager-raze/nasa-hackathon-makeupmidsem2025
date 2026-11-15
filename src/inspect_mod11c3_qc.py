"""Read-only inspection of a MOD11C3 (HDF4) file: metadata, QC_Night bits, candidate cells.

Nothing here filters or modifies data. Run from the repository root:
    python src/inspect_mod11c3_qc.py
Writes results/qc_robustness/hdf_inspection.json (small, safe to commit).

Change from the first version: LST validity now uses the file's own _FillValue and
valid_range (both checked, as the project does) via mod11c3_qc.lst_valid_mask, and
QC bits are decoded by mod11c3_qc.decode_qc instead of a duplicate function.
Field names follow the C6.1 file specification: bits 4-5 are reported as
`emis_consistency` (NOT an emissivity error) and bit 3 as `combined_use`.
Note: a JSON saved by the earlier version used the keys `mandatory`, `data_quality`,
`bit3`, `emis_error`, `lst_error`; `emis_error` there holds the bits 4-5 field.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from pyhdf.SD import SD, SDC

from mod11c3_qc import (DEFAULT_FILL_VALUE, DEFAULT_VALID_RANGE, LST_SCALE,
                        decode_qc, lst_valid_mask)

DEFAULT = "data/raw/MOD11C3.A2024153.061.2024187024328.hdf"
OUT = Path("results/qc_robustness/hdf_inspection.json")
# 0.2-degree cell = 4x4 block of the 0.05-degree grid; row 0 = 90N, col 0 = 180W.
# Verified: reproduces the published medians 258.8 K (Kunlun) and 254.45 K (Vinchina).
SITES = {"Kunlun": (35.3, 81.1), "Vinchina": (-27.9, -68.9)}


def jsonable(x):
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (list, tuple)):
        return [jsonable(i) for i in x]
    return x


def block(lat, lon):
    r0 = int(round((90.0 - (lat + 0.1)) / 0.05))
    c0 = int(round((lon - 0.1 + 180.0) / 0.05))
    return r0, c0


def counts(a):
    u, c = np.unique(a, return_counts=True)
    return {int(k): int(v) for k, v in zip(u, c)}


def popcount32(a):
    a = a.astype(np.uint32)
    n = np.zeros(a.shape, dtype=np.int64)
    for b in range(32):
        n += ((a >> np.uint32(b)) & np.uint32(1)).astype(np.int64)
    return n


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
    print("file:", path, "| bytes:", path.stat().st_size)
    hdf = SD(str(path), SDC.READ)
    rep = {"file": path.name, "bytes": path.stat().st_size, "global_attrs": {}, "datasets": {}}

    for k, v in hdf.attributes().items():
        rep["global_attrs"][k] = len(str(v))
        if k == "CoreMetadata.0":
            for key in ("SHORTNAME", "VERSIONID", "RANGEBEGINNINGDATE", "RANGEENDINGDATE"):
                m = re.search(key + r'.*?VALUE\s*=\s*"?([^"\n]+)"?', str(v), re.S | re.I)
                print(f"  CoreMetadata {key}:", m.group(1).strip() if m else "not found")

    arrays = {}
    for name in hdf.datasets():
        sds = hdf.select(name)
        a = np.asarray(sds.get())
        attrs = {k: jsonable(v) for k, v in sds.attributes().items()}
        rep["datasets"][name] = {"shape": list(a.shape), "dtype": str(a.dtype), "attrs": attrs}
        arrays[name] = a
        keep = {k: attrs[k] for k in ("_FillValue", "scale_factor", "add_offset", "valid_range", "units") if k in attrs}
        print(f"{name:18s} {str(a.dtype):7s} {a.shape} {keep}")

    lst, qc = arrays["LST_Night_CMG"], arrays["QC_Night"]
    la = rep["datasets"]["LST_Night_CMG"]["attrs"]
    # Fail loudly if the file lacks these attributes; never guess silently.
    fill, vrange = la["_FillValue"], tuple(la["valid_range"])
    scale = la["scale_factor"]
    print("\nLST_Night_CMG rule from file: fill =", fill, "| valid_range =", vrange, "| scale =", scale)
    if (fill, vrange) != (DEFAULT_FILL_VALUE, DEFAULT_VALID_RANGE) or abs(scale - LST_SCALE) > 1e-12:
        print("  WARNING: file attributes differ from mod11c3_qc defaults - investigate before analysis.")
    valid = lst_valid_mask(lst, fill, vrange)

    f = decode_qc(qc)  # raises TypeError if QC is not uint8
    mand = f["mandatory_qa"]
    q = {"qc_dtype": str(qc.dtype), "n_pixels": int(qc.size), "n_lst_valid": int(valid.sum()),
         "lst_rule": {"fill": fill, "valid_range": list(vrange), "scale": scale},
         "qc_all_values": counts(qc), "qc_where_lst_valid": counts(qc[valid]),
         "qc_where_lst_fill_or_invalid": counts(qc[~valid]),
         "lst_valid_but_qc0": int(((qc == 0) & valid).sum()),
         "lst_invalid_but_qc0": int(((qc == 0) & ~valid).sum()),
         # integrity checks: the C6.1 file spec says that where LST is fill, QC bits 0-1 are 2 or 3
         "lst_valid_with_mandatory_2_or_3": int((valid & (mand >= 2)).sum()),
         "lst_invalid_with_mandatory_0_or_1": int((~valid & (mand <= 1)).sum())}
    for label, mask in (("all", np.ones_like(valid)), ("lst_valid", valid)):
        q["bits_" + label] = {k: counts(v[mask]) for k, v in f.items()}
    rep["qc_night"] = q
    print("LST valid pixels:", q["n_lst_valid"], "of", q["n_pixels"])
    print("QC_Night values where LST valid:", q["qc_where_lst_valid"])
    print("QC_Night values where LST invalid:", q["qc_where_lst_fill_or_invalid"])
    print("Integrity: valid LST with mandatory 2/3 =", q["lst_valid_with_mandatory_2_or_3"],
          "| invalid LST with mandatory 0/1 =", q["lst_invalid_with_mandatory_0_or_1"])
    for k, v in q["bits_lst_valid"].items():
        print(" ", k, v)

    cs = arrays.get("Clear_sky_nights")
    rep["sites"] = {}
    for site, (lat, lon) in SITES.items():
        r0, c0 = block(lat, lon)
        sl = (slice(r0, r0 + 4), slice(c0, c0 + 4))
        s = {"row0": r0, "col0": c0, "lst_raw": lst[sl].tolist(), "qc_raw": qc[sl].tolist(),
             "lst_valid_in_block": int(valid[sl].sum())}
        if cs is not None:
            s["clear_nights_popcount"] = popcount32(cs[sl]).tolist()
        rep["sites"][site] = s
        print(f"\n{site}: rows {r0}-{r0+3}, cols {c0}-{c0+3}, valid LST pixels: {s['lst_valid_in_block']}/16")
        print(" LST raw:", s["lst_raw"])
        print(" QC raw :", s["qc_raw"])
        if cs is not None:
            print(" clear nights per pixel:", s["clear_nights_popcount"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1, default=str))
    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
