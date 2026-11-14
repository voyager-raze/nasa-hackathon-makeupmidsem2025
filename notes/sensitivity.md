# Sensitivity

These figures are a rerun of the published formula on `data/processed/features.csv`. The rerun called `raw_distance` in `src/score.py`, read the weights from `notes/weights.json`, and used the 10th percentile of night temperature and the 95th percentile of each raw distance, which is the rule in `src/score.py`. It did not rewrite `results/top5.csv`, `results/control.csv`, `results/score-notes.md`, or `results/sources.csv`.

The published scores stay 0.186845 at Kunlun and 0.167981 at Vinchina. The rerun returned 0.186845379 and 0.167981166. The differences are 0.000000379 and 0.000000166, both inside 0.000001. A lower score is a closer partial match. The score is a partial match on measured features, not a probability of mission success.

Scales recovered on this rerun: NDVI 0.8304, rain 0.296 mm/hr, night temperature 86.2 kelvin above 214.3 kelvin. `slope_median_deg` is null on 577134 of 577134 land cells, so the slope weight is unused. The effective weights are 1, 1, and 1 on NDVI, rain, and night temperature. Each site score is the average of those three scaled gaps.

## Weight drops

Each row sets one used weight to 0 and leaves the other two at 1. The scales of the features that remain are the scales above. The score is the average of the two remaining scaled gaps.

| Weight set to 0 | Kunlun score | Vinchina score | Order |
| --- | --- | --- | --- |
| None (published weights) | 0.186845 | 0.167981 | Vinchina closer |
| `ndvi_median` | 0.268256 | 0.246402 | Vinchina closer |
| `precip_median_mm_hr` | 0.270133 | 0.238458 | Vinchina closer |
| `lst_night_median_k` | 0.022147 | 0.019083 | Vinchina closer |

The order of Site A and Site B does not change. Vinchina stays the closer partial match. The gap is smallest when the night-temperature weight is removed: 0.003064, against 0.018864 with the published weights.

A rank against other cells can move when that weight changes. With the night-temperature weight set to 0, 1558 discovery cells that score worse than Kunlun under the published weights score closer than Kunlun. One example is the cell at 31.3°N, 33.9°E. Its June values are NDVI 0, rain 0 mm/hr, and night temperature 297.64 kelvin. Its published score is about 0.322274, and the two-feature score with night temperature removed is 0. That cell is not a new site, and it was not added to the dossiers. It shows that the temperature term is what keeps a warm, barren, dry cell from looking like a close match.

Changing the slope weight does not change the published ranking. The global slope column is empty, so that weight never enters the denominator.

## Patch slopes, kept separate

No global slope raster was built. The later patch measurements stay outside the published scores.

| Patch | Median slope | Against 8.0–16.7 degrees |
| --- | --- | --- |
| Kunlun, cell 35.3_81.1 | 7.08 degrees, rounded from 7.078 | Outside the band, 0.92 degrees below 8.0 |
| Vinchina, cell -27.9_-68.9 | 9.48 degrees, rounded from 9.476 | Inside the band |

Those two degrees are the `slope_median_deg` rows in `results/sources.csv`. They are not part of 0.186845 or 0.167981.
