# MOD11C3 C6.1 QC_Night: bit definitions and filter tiers (QC robustness analysis)

Status: June 2024 only. Verified facts are labelled; assumptions are labelled.

## Source (verified)

LAADS DAAC file specification, MOD11C3, Version 61 (modified 09/20/2019), SDS `QC_Night`:
<https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD11C3>.
The specification confirms: `QC_Night` is uint8, has no `_FillValue`, and must be used
with `LST_Night_CMG`; where LST is fill (0), QC bits 0-1 are 2 or 3 and other zeros are
undefined. LST: uint16, fill 0, valid range 7500-65535, scale 0.02. Grid: 7200 x 3600,
upper-left (-180, 90), geographic (row 0 = 90N, column 0 = 180W).
`Clear_sky_nights` bit i is night i+1.

## Bits (verified against the specification)

| Bits | Field in code | Meaning |
|---|---|---|
| 0-1 | `mandatory_qa` | 0 LST good; 1 LST produced, other quality; 2 no LST (cloud); 3 no LST (other) |
| 2 | `l1b_data_quality` | 0 good L1B data in the 7 thermal-infrared bands; 1 other |
| 3 | `combined_use` | Terra/Aqua combined-use flag, 0 = no, 1 = yes. Defined provenance flag, not a quality grade |
| 4-5 | `emis_consistency` | Official label "Emis Error flag", but the keys describe emissivity consistency: 0 more days within the 32-day average ±1.0 std; 1 ±1.15 std; 2 ±1.3 std; 3 more days outside ±1.3 std (bands 22 and 29) |
| 6-7 | `lst_error_category` | Estimated average LST error category: 0 ≤1 K, 1 ≤2 K, 2 ≤3 K, 3 >3 K |

Corrections made to earlier versions of this analysis:
- Bits 4-5 are **not** emissivity-error thresholds of 0.01/0.02/0.04. Those thresholds are in
  the Collection 5 MOD11C3 text and in the User Guide tables for other products; they are not
  in the C6.1 MOD11C3 file specification. The earlier tier T3 was based on them and is retired.
- Bit 3 is **not** "TBD/undefined" for this product; it is the Terra/Aqua combined-use flag.
  The User Guide's cross-reference for MOD11C3 (Table 13) was misleading; the file specification governs.

## What the flags are not

The LST error categories are algorithm-estimated bins, not probabilities and not a measured
accuracy. A QC filter removes pixels the algorithm flagged; it does not make the remaining
temperature "more accurate" without further assumptions.

Not documented (assumption, unresolved): how the daily QC bits are combined into the
monthly QC of MOD11C3, what "more days" means quantitatively for bits 4-5, and what
the combined-use flag implies for a Terra (MOD) product. This is why bit 3 is never used
as a filter and bits 4-5 are used in no primary tier.

## Tiers

| Tier | Rule | Role |
|---|---|---|
| T0 | valid LST (not fill, inside valid range) | baseline, reproduces the published median |
| T1 | T0 + mandatory QA in {0, 1} | integrity check (an LST was produced) |
| T2 | T1 + LST error category ≤ 1 (≤ 2 K) | primary |
| T4 | T1 + LST error category = 0 (≤ 1 K) | strict |
| T5 | T1 + `l1b_data_quality` = 0 | strict, input data |
| X1 | T2 + `emis_consistency` ≠ 3 | exploratory only; no documented pass/fail threshold |
| T3 | retired | calling it raises an error |

Tier IDs were not renumbered so that earlier discussions stay unambiguous.

## Run

```
python -m unittest discover -s tests -p "test_mod11c3_qc.py" -v
python -m unittest discover -s tests -p "test_qc_site_tiers.py" -v
python src\inspect_mod11c3_qc.py     # needs the HDF file and pyhdf; rewrites hdf_inspection.json
python src\qc_site_tiers.py          # needs only hdf_inspection.json
```
