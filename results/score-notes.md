# Score notes

The score is a partial match on the measured features, not a probability of mission success.

A lower score is a closer partial match. Gravity, vacuum, thin air, and radiation are not in this score.

## Formula

For each feature that is measured on the cell and was not skipped, the distance is the Earth value compared with the target in that feature's own unit. Each raw distance is then divided by a scale in that same unit: the 95th percentile of that raw distance on land cells where the feature is measured, including cells inside the hold-out. Those divisors are listed below. The score is the weighted mean of the quotients, using only features measured on that cell:

score = sum(weight × raw distance / scale) / sum(weight)

Weights, the cold-tail percentile, and the scale percentile are read from `notes/weights.json` on every run. They are not hard-coded in `src/score.py`. The lunar slope band is read from `notes/targets.md`.

Comparisons:

- `ndvi_median`: target is 0. Distance is the absolute departure from 0, in NDVI. A small negative index and a small positive index are both near the target. June NDVI near zero includes snow and ice as well as bare ground. This score does not separate those surfaces.
- `precip_median_mm_hr`: dryness uses the dry direction of the logged IMERG rate. The target is 0 mm/hr. Distance is the rate when the rate is positive, in mm/hr. June 2024 is one month, not an annual normal. A zero in this column is the dry end of this granule.
- `lst_night_median_k`: this is the only temperature column in the table. `LST_Day_CMG` was not reduced, so there is no day–night range to score. The cold-tail target is the 10th percentile of measured night land-surface temperature, **214.3 kelvin**. Distance is kelvin above that percentile. A cell at or below it has distance 0.
- `slope_median_deg`: nearness to the lunar band means 0 distance inside the band and, outside it, the degrees to the nearest edge. The band read from `notes/targets.md` is **8.0–16.7 degrees**.

A cell enters the discovery ranking or the control ranking only when every feature that has a positive weight and a column that is not entirely null is measured on that cell. A missing vegetation, precipitation, or night-temperature value stays out of the score. It is not filled, and the cell is not ranked on the features that remain, because dropping a missing test would make the cell look closer. `features_missing` on each ranked row still lists the skipped column. Nulls in `results/top5.csv` are written as `null`.

## Weights

File weights this delivery: `slope_median_deg` 1, `ndvi_median` 1, `precip_median_mm_hr` 1, `lst_night_median_k` 1.

Effective weights in the denominator this run: `ndvi_median` 1, `precip_median_mm_hr` 1, `lst_night_median_k` 1.

| Feature | Weight in `notes/weights.json` | Unit of the raw distance | This run |
| --- | --- | --- | --- |
| `slope_median_deg` | 1 | degrees | not used this run |
| `ndvi_median` | 1 | NDVI | used |
| `precip_median_mm_hr` | 1 | mm/hr | used |
| `lst_night_median_k` | 1 | kelvin | used |

Changing the slope weight does not change `results/top5.csv` while `slope_median_deg` is empty. Changing the weight of a feature in the effective list does. The delivered weights are the weights that produced the delivered ranking.

## Scales

The scale is the 95th percentile of the raw distance. Dividing by it puts a typical far value near 1 before the weights are applied. A cell farther out than that percentile can score above 1 on that feature.

| Feature | Scale | Raw distance |
| --- | --- | --- |
| `ndvi_median` | 0.8304 NDVI | absolute departure from 0 |
| `precip_median_mm_hr` | 0.296 mm/hr | mm/hr above 0, the dry end of the logged rate |
| `lst_night_median_k` | 86.2 kelvin | kelvin above the cold-tail percentile; 0 at or below it |

The cold-tail target, 214.3 kelvin, is the 10th percentile of `lst_night_median_k` on land cells where that column is measured. 56883 land cells are at or below it. The warmest latitude among those cells is -70.3 degrees. They are not a discovery result: June NDVI is blank on every land cell south of 60°S, so those cells fail the eligibility rule.

## Features skipped

- `slope_median_deg`: the column is null on every land cell, so this feature is left out of the score. The slope comparison is not yet measured.

Confidence is lower because the slope comparison is not yet measured. No slope raster was invented. Elevation was reserved for the zoom on the two chosen patches.

## Hold-out

The famous control is the Atacama Desert. Cells whose centers fall inside this bounding box do not compete for `results/top5.csv`.

| Edge | Degrees | Geographic edge |
| --- | --- | --- |
| South | -30.0 | 30°S |
| North | -18.0 | 18°S |
| West | -71.5 | 71.5°W |
| East | -67.0 | 67°W |

The box covers the Chilean Atacama from the northern desert to about 30°S and from the Pacific slope to the Andean front, including the Salar de Atacama. The Antarctic Dry Valleys are another famous control the science notes allow, and they were not used. June NDVI is blank south of 60°S, so vegetation cannot be scored there. Atacama has the three features this run actually scores.

Eligible cells inside the box: 1114. Eligible discovery cells outside it: 404930.

## Control score

The control score is the best eligible cell inside the box, from the same function as the discovery cells. It is not a discovery winner.

| Item | Value |
| --- | --- |
| cell_id | `-27.9_-68.9` |
| latitude | -27.9 |
| longitude | -68.9 |
| ndvi_median | 0.00925 |
| lst_night_median_k | 254.45 |
| precip_median_mm_hr | 0.008 |
| slope_median_deg | null |
| score | 0.167981 |
| features missing | slope_median_deg |

The median score of the 1114 eligible cells in the box is 0.273354. That median is a summary of the same cell scores. It is not a second formula. The row written to `results/control.csv` is the best cell.

## Discovery cells

`results/top5.csv` is written by `src/score.py` from the measurement table and the weights file. These five rows are that file.

| rank | cell_id | lat | lon | NDVI | night LST (K) | precip (mm/hr) | score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `73.5_-40.5` | 73.5 | -40.5 | -0.032 | 252.94 | 0 | 0.162265 |
| 2 | `73.5_-40.7` | 73.5 | -40.7 | -0.03205 | 253.02 | 0 | 0.162595 |
| 3 | `73.9_-40.1` | 73.9 | -40.1 | -0.0324 | 253.13 | 0 | 0.163160 |
| 4 | `73.5_-40.9` | 73.5 | -40.9 | -0.0318 | 253.21 | 0 | 0.163229 |
| 5 | `74.1_-39.9` | 74.1 | -39.9 | -0.0352 | 252.88 | 0 | 0.163318 |

The five centers span latitude 73.5 to 74.1 and longitude -40.9 to -39.9.

Each of these rows is missing `slope_median_deg`. The feature columns that were measured are filled from `data/processed/features.csv`. The script does not edit that table.

The best eligible discovery cell south of 60°N is `35.3_81.1` at latitude 35.3, longitude 81.1, score 0.186845. That score is a worse partial match than the Atacama control cell (0.167981). It is not one of the five discovery ranks.

## Worked example for rank 1

- `ndvi_median`: raw distance 0.032 NDVI, divided by 0.8304 NDVI = 0.038536, times weight 1.
- `precip_median_mm_hr`: raw distance 0 mm/hr, divided by 0.296 mm/hr = 0.000000, times weight 1.
- `lst_night_median_k`: raw distance 38.64 kelvin, divided by 86.2 kelvin = 0.448260, times weight 1.
- Score = weighted mean = 0.162265 (denominator 3).

## What this score is not

The score is a partial match on the measured features, not a probability of mission success. Gravity, vacuum, thin air, and radiation stay out of scope. Slope stays out of the score until that column is measured.

Rerun with `python src/score.py` after any edit to `notes/weights.json`.
