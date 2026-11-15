# June 2024 QC Score Sensitivity

## Purpose

This analysis tests how MOD11C3 nighttime-LST QC tiers affect the original partial-match scores for Kunlun and Vinchina.

It does not change the original feature table, weights, scoring code, or published rankings. Kunlun remains the discovery candidate and Vinchina the hold-out/control site; the QC tiers do not change those roles.

The analysis covers June 2024 only. June 2024 is a single monthly composite, not a climate normal.

## Headline result

For June 2024, filtering MOD11C3 nighttime LST with T1, T2 or X1 left both candidate-site medians unchanged, because no pixels were removed from either 16-pixel site block. Under T4, Vinchina retained 15/16 pixels (median +0.07 K), but Kunlun retained only 2/16 (12.5%) and its median rose by 3.88 K; with so little support, this Kunlun value is weakly supported. Under T5, Kunlun retained 10/16 pixels and Vinchina none, so no two-site comparison is possible. The site comparison therefore depends on both the QC criterion and the spatial support remaining after filtering. These findings describe QC sensitivity in a single monthly composite. They do not show which filter is more accurate or which site is more suitable for a mission.

## QC tier definitions

| Tier | Rule | Role |
|---|---|---|
| T0 | Valid LST only | Baseline (original aggregation) |
| T1 | T0 + mandatory QA in {0, 1} | Mandatory-QA filter |
| T2 | T1 + LST error category <= 1 (estimated <= 2 K) | Stricter than T1 |
| T4 | T1 + LST error category = 0 (estimated <= 1 K) | Alternative stricter filter |
| T5 | T1 + QC bit 2 = 0 (L1B input data quality good) | Alternative stricter filter |
| X1 | T2 + emissivity-consistency category != 3 | Exploratory only; not a primary filter |

T4 and T5 are alternative stricter filters, not one sequential ladder. T3 is retired and is not used. QC values are always interpreted together with LST validity. QC categories are algorithm estimates, not validated ground-truth accuracy.

## Fixed parameters

- Nighttime LST target: 214.3 K
- NDVI scale: 0.8304
- Precipitation scale: 0.296 mm/hr
- Nighttime LST scale: 86.2 K
- Effective weights: 1 for each of the three features
- Score denominator: 3

The global target and normalization scales are held fixed to isolate the effect of changing candidate-site LST. Only the nighttime-LST input is replaced; NDVI and precipitation keep their original values.

Because every LST median is above the target, the LST term rises linearly with temperature. With three equal weights, every score change in this report equals the LST median change divided by 258.6 (3 x 86.2), about 0.00387 score units per kelvin. The score changes are therefore linear rescalings of the LST changes under the fixed formula, not independent evidence beyond the temperature medians.

## Results

| Site | Tier | Kind | LST (K) | Pixels kept | Baseline | QC score | Delta | Status |
|---|---|---|---:|---:|---:|---:|---:|---|
| Kunlun | T0 | primary | 258.80 | 16/16 (100%) | 0.186845 | 0.186845 | +0.000000 | OK |
| Kunlun | T1 | primary | 258.80 | 16/16 (100%) | 0.186845 | 0.186845 | +0.000000 | OK |
| Kunlun | T2 | primary | 258.80 | 16/16 (100%) | 0.186845 | 0.186845 | +0.000000 | OK |
| Kunlun | T4 | primary | 262.68 | 2/16 (12.5%) | 0.186845 | 0.201849 | +0.015004 | LOW_SUPPORT |
| Kunlun | T5 | primary | 256.81 | 10/16 (62.5%) | 0.186845 | 0.179150 | -0.007695 | OK |
| Kunlun | X1 | exploratory | 258.80 | 16/16 (100%) | 0.186845 | 0.186845 | +0.000000 | OK |
| Vinchina | T0 | primary | 254.45 | 16/16 (100%) | 0.167981 | 0.167981 | +0.000000 | OK |
| Vinchina | T1 | primary | 254.45 | 16/16 (100%) | 0.167981 | 0.167981 | +0.000000 | OK |
| Vinchina | T2 | primary | 254.45 | 16/16 (100%) | 0.167981 | 0.167981 | +0.000000 | OK |
| Vinchina | T4 | primary | 254.52 | 15/16 (93.75%) | 0.167981 | 0.168252 | +0.000271 | OK |
| Vinchina | T5 | primary | N/A | 0/16 (0%) | 0.167981 | N/A | N/A | UNAVAILABLE |
| Vinchina | X1 | exploratory | 254.45 | 16/16 (100%) | 0.167981 | 0.167981 | +0.000000 | OK |

Status legend:

- OK: at least 8 pixels retained. This is a reporting precaution only. It is not an official MODIS threshold, not a statistically validated confidence threshold, and not a statement about data quality.
- LOW_SUPPORT: fewer than 8 pixels retained. The score is calculated but should be interpreted cautiously.
- UNAVAILABLE: no retained LST pixels. The score is not estimated.

A lower score means closer to the project's target conditions under the original normalized-distance definition. It does not mean a better site. A negative delta means the QC-adjusted score decreased (closer to the target); a positive delta means it increased (further from the target).

## Site-score gap

| Tier | Kunlun kept | Vinchina kept | Kunlun score | Vinchina score | Gap (Vinchina minus Kunlun) | Pair status |
|---|---:|---:|---:|---:|---:|---|
| T0 | 16/16 | 16/16 | 0.186845 | 0.167981 | -0.018864 | COMPARABLE |
| T1 | 16/16 | 16/16 | 0.186845 | 0.167981 | -0.018864 | COMPARABLE |
| T2 | 16/16 | 16/16 | 0.186845 | 0.167981 | -0.018864 | COMPARABLE |
| T4 | 2/16 | 15/16 | 0.201849 | 0.168252 | -0.033597 | LOW_SUPPORT |
| T5 | 10/16 | 0/16 | 0.179150 | N/A | N/A | UNAVAILABLE |
| X1 | 16/16 | 16/16 | 0.186845 | 0.167981 | -0.018864 | COMPARABLE |

The gap is computed from the six-decimal scores in `score_sensitivity_june2024.csv`, so it can be reproduced from that file. A negative gap means Vinchina's score is lower than Kunlun's.

Pair status: COMPARABLE means only that both sites retained enough pixels to pass the reporting precaution; it does not mean the comparison is reliable or that either site is more suitable. LOW_SUPPORT means at least one site is below the precaution. UNAVAILABLE means at least one site has no retained pixels, so no gap exists.

T1, T2 and X1 retained all pixels only for these two site blocks in June 2024, so their gaps equal the T0 gap. This says nothing about other grid cells or other months.

## T4: Kunlun low-support case

Under T4, 2 of the 16 MODIS pixels in Kunlun's project cell remain (12.5% retention); Vinchina retains 15 of 16 (93.75%). The Kunlun T4 median is therefore based on two pixels, and the median of two values is simply their mean. This is a major limitation of the Kunlun T4 result, not a minor footnote.

The Kunlun T4 score (0.201849) is calculated with the original formula, but it rests on two pixels and should be interpreted cautiously. The T4 pair status is LOW_SUPPORT, and the T4 gap should not be read as a reliable site comparison.

Unequal support: under T4 the two sites have very different support (2/16 versus 15/16), so the T4 changes are not like-for-like. The larger Kunlun shift (+3.88 K, against +0.07 K at Vinchina) should not be read as Kunlun being intrinsically more QC-sensitive: Kunlun lost 14 pixels and Vinchina lost 1.

Which pixels were excluded (derived from the tier counts only; this script reads no pixel-level data): T1 and T2 retained all 16 pixels at both sites, and T4 is a subset of T2. The 14 Kunlun pixels excluded by T4 were therefore not excluded for failing mandatory QA; they have LST error category 1 (estimated <= 2 K) rather than category 0 (estimated <= 1 K). At Vinchina, 1 pixel is excluded by T4 for the same reason.

Retained Kunlun T4 pixel values:

| Item | Value |
|---|---|
| Retained pixel values (T4) | 261.34 K, 264.02 K |
| Mean of the two (equals the T4 median) | 262.68 K |
| Original 16-pixel median (T0) | 258.80 K |

Provenance: these two pixel values were manually transcribed from the earlier June 2024 HDF pixel inspection. They are not computed or generated by this script and are not a reproducible output of it. As a consistency check only, the script confirms that their mean matches the T4 median in the QC CSV.

Both retained values lie above the original T0 median. This is a descriptive observation about two pixels. It does not show that they are outliers or unrepresentative, which has not been tested.

Pixels that pass a stricter filter are a selected subset of the block, not a random sample, so the T4 median describes that subset. It does not show that the original median was biased or that the T4 value is more accurate. Why particular pixels received a higher error category was not examined.

## T5: no two-site comparison

Under T5, Kunlun retains 10/16 pixels (62.5%; median 256.81 K) and Vinchina retains 0/16. T5 is T1 plus QC bit 2 = 0, and T1 retained all 16 Vinchina pixels, so all 16 Vinchina pixels have QC bit 2 (L1B input data quality) set to "other"; the same is true for 6 of 16 Kunlun pixels (derived from tier counts). Why this flag is set on every Vinchina pixel was not investigated.

Because no Vinchina pixels remain, no T5 Vinchina score or gap exists. T5 therefore cannot show which site has the lower score. Kunlun's T5 result is a Kunlun-only result. The T5 pair status is UNAVAILABLE.

## What these results do and do not show

They show how retained pixel support, nighttime-LST medians and the resulting scores for two site blocks depend on the chosen QC criterion in one monthly composite (June 2024).

They do not show which filter is more accurate, and stricter QC does not automatically mean more accurate data. They do not show which site is more suitable for a mission, and they support no statistical significance claim.

## Limitations

- Kunlun T4 retains 2/16 pixels (12.5%), so its median and score have very limited spatial support.
- Support is unequal between sites under T4, and the T5 comparison is impossible because Vinchina has no retained pixels.
- Filtered pixels are a selected subset, not a random sample. QC categories are algorithm estimates and do not establish ground-truth accuracy.
- June 2024 is a single monthly composite, not a climate normal and not independent daily observations.
- T1, T2 and X1 retained all pixels only for these two site blocks in June 2024.
- The LOW_SUPPORT limit of fewer than 8 pixels is a reporting precaution. It is not an official MODIS threshold or a statistically validated confidence threshold, and passing it does not make a median robust.
- Neighboring pixels are not independent, so no significance claims are made from them.
- The score is a partial-match heuristic, not a probability of mission success or a definitive site-suitability ranking. No rover field trial, site-access, safety or logistics assessment is included.

## Methodological note

- Tier rules follow `notes/qc-robustness-bit-definitions.md`. LST validity uses fill value 0, valid range 7500-65535 and scale factor 0.02.
- 0.05 degree MODIS pixels are aggregated into 0.2 degree project cells (16 pixels per cell) using the median.
- Monthly QC aggregation semantics are incompletely documented, so the exact meaning of a QC flag in a monthly composite is uncertain.
- Clear-sky sampling can bias temperature relative to all-sky conditions, and rugged terrain and mixed surfaces complicate interpretation.
- Baseline check: the script recomputes both original scores from the feature table and stops if either differs from the published score by more than 0.000002.
- T0 consistency check: the script stops if the T0 QC median differs from the original feature-table LST by more than 0.005 K.

## Reproducibility

Inputs:
- `data/processed/features.csv`
- `results/qc_robustness/site_tiers_june2024.csv`

Run from the repository root:

```
python src/analyze_qc_score_sensitivity.py
```

Outputs: `score_sensitivity_june2024.csv` and this report, both in `results/qc_robustness/`.

The two Kunlun T4 pixel values in this report are the one manually transcribed input; everything else is computed from the inputs above.

Original scoring parameters are held fixed. Original project outputs are not overwritten.
