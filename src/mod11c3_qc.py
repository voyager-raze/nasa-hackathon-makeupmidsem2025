"""MOD11C3 (Collection 6.1) nighttime-LST quality-control decoder and filter tiers.

Self-contained: it does not import or change any other project file.

Source of truth
---------------
LAADS DAAC file specification "Monthly 0.05Deg CMG LST product specifications",
MOD11C3, Version 61 (modified 09/20/2019), SDS QC_Night:
    https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD11C3

Background for beginners
------------------------
Each 0.05-degree pixel has two numbers:
  * LST_Night_CMG: the temperature, stored as an integer (kelvin = integer * 0.02).
                   The integer 0 means "no data" (fill value); valid is 7500..65535.
  * QC_Night:      one byte (8 on/off switches, "bits") of quality flags for that pixel.
Bits are counted from the right, so bit 0 is the rightmost. To read bits 0-1 we
compute  qc & 3  ("keep the two rightmost bits"). To read bits 6-7 we first shift
right by 6:  (qc >> 6) & 3.

Bit layout (verbatim meaning from the C6.1 specification)
---------------------------------------------------------
  bits 0-1  Mandatory QA flags
              0 = LST produced, good quality
              1 = LST produced, other quality (examine more detailed QA)
              2 = LST not produced (cloud effects)
              3 = LST not produced (reasons other than cloud)
  bit  2    Data Quality flag
              0 = good data quality of L1B in the 7 thermal-infrared bands
              1 = other quality data
  bit  3    Terra/Aqua combined-use flag   (0 = no, 1 = yes)
              A defined provenance flag. It is NOT a quality grade and NO filter
              tier uses it. The specification does not say more about its meaning.
  bits 4-5  "Emis Error flag" -- but see the warning below.
              0 = more days with emissivity within the 32-day average +/- 1.0 std
              1 = more days within average +/- 1.15 std
              2 = more days within average +/- 1.3 std
              3 = more days outside average +/- 1.3 std
              (applies to bands 22 and 29). This describes how CONSISTENT the
              emissivity was across days relative to a 32-day average. It is NOT
              an emissivity error in absolute units. (Older Collection 5 and 1 km
              products used 0.01 / 0.02 / 0.04 emissivity-error thresholds;
              that text does not apply to MOD11C3 C6.1.) The wording "more days"
              is not quantified in the specification, and it gives no pass/fail
              threshold, so we decode this field but use it in no primary tier.
  bits 6-7  LST Error flag: category of the estimated average LST error
              0 = <= 1 K, 1 = <= 2 K, 2 = <= 3 K, 3 = > 3 K
              These are algorithm-estimated categories, not probabilities and not
              validated accuracy.

IMPORTANT: QC has no fill value. Where LST is fill (0), the specification says QC
bits 0-1 are 2 or 3 and the other fields' zeros are undefined. QC = 0 on a "no
data" pixel therefore never means "good": every tier starts from "LST is valid".
"""
import numpy as np

LST_SCALE = 0.02                  # kelvin per stored integer (layer attribute)
DEFAULT_FILL_VALUE = 0            # LST_Night_CMG _FillValue
DEFAULT_VALID_RANGE = (7500, 65535)  # LST_Night_CMG valid_range (inclusive)

# Primary tier ladder. "T3" is intentionally absent (retired, see RETIRED_TIERS).
TIERS = {
    "T0": "valid LST only (the project's existing rule; QC not used)",
    "T1": "T0 + mandatory QA in {0, 1} (an LST was actually produced)",
    "T2": "T1 + estimated LST error category <= 1 (at most 2 K)",
    "T4": "T1 + estimated LST error category == 0 (at most 1 K)",
    "T5": "T1 + L1B data-quality bit 2 == 0 (good input data)",
}
# Not part of the primary ladder; reported only as a clearly labelled sensitivity.
EXPLORATORY_TIERS = {
    "X1": "T2 + emissivity-consistency category != 3 (drops only the 'out of +/-1.3 std' "
          "class; the specification gives no pass/fail threshold)",
}
RETIRED_TIERS = {
    "T3": "retired: it treated bits 4-5 as emissivity error <= 0.02, which the C6.1 "
          "MOD11C3 specification does not support",
}


def decode_qc(qc):
    """Split QC byte(s) into named fields. Works on one value or a whole array.

    Raises TypeError unless the input is uint8, so a wrongly-read array
    (e.g. signed or float) cannot be decoded silently.
    """
    qc = np.asarray(qc)
    if qc.dtype != np.uint8:
        raise TypeError(f"QC must be uint8, got {qc.dtype}")
    return {
        "mandatory_qa": qc & 3,
        "l1b_data_quality": (qc >> 2) & 1,
        "combined_use": (qc >> 3) & 1,        # reported only, never used for filtering
        "emis_consistency": (qc >> 4) & 3,    # NOT an emissivity error (see docstring)
        "lst_error_category": (qc >> 6) & 3,  # category index, not a kelvin value
    }


def lst_valid_mask(lst_raw, fill_value=DEFAULT_FILL_VALUE, valid_range=DEFAULT_VALID_RANGE):
    """True where the stored LST integer is usable.

    Same rule the project documents: not the fill value AND inside valid_range
    (both ends inclusive). Applied to the raw integers, before scaling.
    """
    lst = np.asarray(lst_raw)
    lo, hi = valid_range
    return (lst != fill_value) & (lst >= lo) & (lst <= hi)


def tier_mask(qc, lst_raw, tier, fill_value=DEFAULT_FILL_VALUE, valid_range=DEFAULT_VALID_RANGE):
    """Boolean array: True where the pixel is kept under `tier`."""
    if tier in RETIRED_TIERS:
        raise ValueError(f"tier {tier!r} is {RETIRED_TIERS[tier]}")
    if tier not in TIERS and tier not in EXPLORATORY_TIERS:
        raise ValueError(f"unknown tier {tier!r}; defined: {sorted(TIERS) + sorted(EXPLORATORY_TIERS)}")
    qc, lst = np.asarray(qc), np.asarray(lst_raw)
    if qc.shape != lst.shape:
        raise ValueError(f"QC shape {qc.shape} != LST shape {lst.shape}")
    keep = lst_valid_mask(lst, fill_value, valid_range)      # T0
    if tier == "T0":
        return keep
    f = decode_qc(qc)
    keep = keep & (f["mandatory_qa"] <= 1)                   # T1
    if tier == "T1":
        return keep
    if tier == "T2":
        return keep & (f["lst_error_category"] <= 1)
    if tier == "T4":
        return keep & (f["lst_error_category"] == 0)
    if tier == "T5":
        return keep & (f["l1b_data_quality"] == 0)
    # X1 (exploratory)
    return keep & (f["lst_error_category"] <= 1) & (f["emis_consistency"] != 3)


def to_kelvin(lst_raw, keep_mask, scale=LST_SCALE):
    """Scaled kelvin where kept; NaN elsewhere. Missing is never turned into 0."""
    lst = np.asarray(lst_raw).astype(np.float64) * scale
    return np.where(np.asarray(keep_mask), lst, np.nan)
