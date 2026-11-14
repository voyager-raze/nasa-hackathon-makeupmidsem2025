# Credibility

This note uses the ideas in NASA-STD-7009 as a checklist: pedigree of the inputs, verification that the code follows the written formula, validation against a Moon or Mars referent where one exists, and an explicit uncertainty. This file does not claim that standard is met. Partial Match is not certified for flight. The page is an analog screen for a rover rehearsal on measured ground. The score is a partial match on measured features, not a probability of mission success.

## Dashboard confidence and probability

The page reports **no candidate-specific mission success probability**. The available site features are a single June 2024 Earth snapshot; vegetation, precipitation, and surface temperature have no direct Moon/Mars referents; and there are no mission outcomes linked to these candidate cells. A weighted similarity value cannot be converted to mission probability without inventing a relationship between similarity and outcome.

To provide a useful numerical reference, the dashboard computes a historical Curiosity drive-completion rate from NASA's report: 622 of 738 attempted drives completed, or 84.3%. Its 95% Wilson interval is 81.5–86.7%, calculated from those counts. This is an observed **per-drive** rate over the first seven years of Curiosity, not a site-specific forecast or a whole-mission success probability. The interval treats attempts as binomial observations; drives from one rover over time are not fully independent, so this interval does not capture all operational or vehicle-specific uncertainty. Source: [NASA NTRS 20220000780](https://ntrs.nasa.gov/citations/20220000780).

The displayed **LOW** evidence grade is qualitative; it is not a confidence interval or probability. It reflects one month of proxy data and no candidate outcome calibration. The selected-cell panel shows measured values and valid-pixel support, but pixel coverage is not confidence that a mission will succeed.

A candidate-level model requires a specific rover, mission duration, task-success criterion, repeated seasonal and hazard-relevant site measurements, and representative rover-trial or mission outcome labels. Fit and calibrate on training cases, evaluate on held-out cases, publish calibration error and uncertainty intervals, and retain explicit gates for critical hazards such as mobility, power, thermal, communications, and crew safety.

## Pedigree

Every published number below is a row in `results/sources.csv`, or it is named as a quantity computed from those rows. June 2024 is one month, not a climate normal. It is summer in the north and winter in the south.

| Published number | Source row | Unit | Dataset | Date |
| --- | --- | --- | --- | --- |
| Site A score 0.186845, cell 35.3°N, 81.1°E | `partial match score` | weighted distance | `data/processed/features.csv` through `src/score.py` and `notes/weights.json` | 1–30 June 2024 |
| Site A NDVI −0.01995 | `ndvi_median` | NDVI | MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG, version 061 | 1–30 June 2024 |
| Site A rain 0.006 | `precip_median_mm_hr` | mm/hr | GPM IMERG Final Precipitation L3 1 month 0.1 degree, 07 V07B | 1–30 June 2024 |
| Site A night temperature 258.8 | `lst_night_median_k` | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, version 061 | 1–30 June 2024 |
| Site A day temperature 269.12 | `lst_day_median_k` | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, version 061 | 1–30 June 2024 |
| Site A paired day–night range 11.05 | `lst_day_night_range_median_k` | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, version 061 | 1–30 June 2024 |
| Site A slope 7.08, rounded from 7.078 | `slope_median_deg` | degrees | Copernicus DEM, GLO-30 Public | 2021 release |
| Site A elevation 6120.8, rounded from 6120.757 | `elevation_median` | m | Copernicus DEM, GLO-30 Public | 2021 release |
| Site B score 0.167981, cell 27.9°S, 68.9°W | `partial match score` | weighted distance | `data/processed/features.csv` through `src/score.py` and `notes/weights.json` | 1–30 June 2024 |
| Site B NDVI 0.00925 | `ndvi_median` | NDVI | MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG, version 061 | 1–30 June 2024 |
| Site B rain 0.008 | `precip_median_mm_hr` | mm/hr | GPM IMERG Final Precipitation L3 1 month 0.1 degree, 07 V07B | 1–30 June 2024 |
| Site B night temperature 254.45 | `lst_night_median_k` | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, version 061 | 1–30 June 2024 |
| Site B day temperature 264.58 | `lst_day_median_k` | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, version 061 | 1–30 June 2024 |
| Site B paired day–night range 10.44 | `lst_day_night_range_median_k` | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, version 061 | 1–30 June 2024 |
| Site B slope 9.48, rounded from 9.476 | `slope_median_deg` | degrees | Copernicus DEM, GLO-30 Public | 2021 release |
| Site B elevation 5330.7, rounded from 5330.746 | `elevation_median` | m | Copernicus DEM, GLO-30 Public | 2021 release |
| Lunar slope band 8.0–16.7 | `lunar slope interquartile range` | degrees | LOLA 5 m/pixel slope, Site01 connecting ridge | read 14 November 2026 |
| Lunar slope median 12.3 | `lunar slope median` | degrees | LOLA 5 m/pixel slope, Site01 connecting ridge | read 14 November 2026 |

The five Greenland cells classed `ice-sheet interior` stay rejected. Their Worldview rows are surface classes on 2024-06-15, confirmed on 2024-08-15. Kunlun is classed bare ground with ridgeline snow. Vinchina is classed arid mountains, with small snow patches noted on 2024-11-15. Snow in a Worldview class is not a measured ice body.

The score scales are computed from the June feature table and written in `results/score-notes.md`: NDVI 0.8304, rain 0.296 mm/hr, and 86.2 kelvin above a cold-tail target of 214.3 kelvin. A rerun in this chat recovered the same three scales and the same cold-tail target. Those four figures are not separate rows in `results/sources.csv`.

The same rerun, using `raw_distance` in `src/score.py` and the percentile scales on `data/processed/features.csv`, returned 0.186845379 for Kunlun and 0.167981166 for Vinchina. The differences from the published scores are 0.000000379 and 0.000000166. Both are inside 0.000001. The published scores were left unchanged. The MODIS day and paired-range source rows below document added descriptive values; they do not alter the published score rows.

The June daytime and paired day–night measurements were decoded from `LST_Day_CMG` and `LST_Night_CMG`, using each layer's `scale_factor` (0.02), `_FillValue`, and `valid_range`. The range is computed from paired valid pixels before taking the cell median. These columns are not score terms and have no Moon or Mars referent in the source table.

A second month was not opened. The preferred next file was the July 2024 MOD13C2 granule `MOD13C2.A2024183.061.2024228034735.hdf`. The download URL returned HTTP 401:

https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MOD13C2.061/MOD13C2.A2024183.061.2024228034735/MOD13C2.A2024183.061.2024228034735.hdf

That failed July attempt produced no measurement and no source row.

## Verification

`tests/test_score_formula.py` imports `raw_distance` from `src/score.py` and restates the same four distances. The test fails if the restated rule and the code disagree. It checks absolute NDVI departure from 0, rain above 0, kelvin above 214.3 (and 0 at or below that target), slope distance 0 inside 8.0–16.7 degrees and the degrees to the nearest edge outside that band, and the rank-1 worked example in `results/score-notes.md`: scaled gaps 0.038536, 0, and 0.448260 average to 0.162265. With equal weights and three used features, the score divides by 3.

Run it from the repository root:

```
python -m pytest tests/test_score_formula.py
```

## Validation

Formula verification, source validation, weight sensitivity, date/source sensitivity, and external validation are separate questions. The formula test verifies code against a restated rule; it is not independent validation. Earth measurements were opened and decoded for the June table, while July MOD13C2 access failed with HTTP 401 and the attempted coarse ETOPO2 archive timed out. No directly comparable Moon/Mars referents exist for the three scored quantities, and no valid independent Earth cases with direct planetary referents are available. External validation of candidate rankings is therefore not yet possible. The score is a heuristic screening index, not a direct cross-world similarity measurement.

The batch published ranking is the unfiltered June ranking (`results/top5.csv`), which includes the Greenland ice-sheet cells. The map discovery ranking excludes the Atacama hold-out box and the reviewed Greenland ice-sheet cluster; its purpose is to find non-control, non-ice-sheet cells for further inspection. It does not identify the best overall candidate: Site A/Kunlun's locked score 0.186845 is worse than Site B/Vinchina's control score 0.167981. The Atacama control ranking (`results/control.csv`) answers how the best eligible cell in that box scores under the same formula.

The slope band is the Moon comparison. Vinchina’s later patch median, 9.48 degrees, sits inside 8.0–16.7 degrees. Kunlun’s later patch median, 7.08 degrees, sits 0.92 degrees below the lower edge. Both patch slopes were measured after the published score. The global `slope_median_deg` column is still null, so those degrees are not inside 0.186845 or 0.167981.

The patch-slope comparison is a direct terrain check against the locked lunar band; it is not validation of the three-feature score or of rover performance. Vegetation, rain, and night temperature have no Moon or Mars value in `results/sources.csv`. Each of those Earth numbers stands alone. Median elevation at the two patches also stands alone: no lunar or Martian elevation is in the source table.

The locked Mars target, ground ice at Badger, has published target evidence: Bramson et al. (2015) interpreted CTX and SHARAD observations, with MOLA-based clutter simulations, as evidence for a decameters-thick layer that is mostly excess water ice at a flat terrace 43 m deep ([DOI](https://doi.org/10.1002/2015GL064844)). This team did not process that radar data or a local Mars ice map. No Earth ice/permafrost layer was used, so no Earth ice analog is identified. Minerals and a dust index remain blank. No Diviner temperature is in the source table. A permanently shadowed lunar floor is colder than any outdoor Earth site, so the June night temperatures are not a thermal analog for that floor.

## Uncertainty

`notes/sensitivity.md` is the rerun. Setting any one used weight to 0 leaves Vinchina closer than Kunlun. The order of these two sites does not swap. A rank can still move. Zeroing the night-temperature weight drops Kunlun from 0.186845 to 0.022147, and 1558 discovery cells that score worse than Kunlun on the published weights then score closer. One of them is the cell at 31.3°N, 33.9°E, where June NDVI is 0, rain is 0 mm/hr, and night temperature is 297.64 kelvin. That cell is an illustration of the weight, not a new site.

Weight draws measure only sensitivity to the named artificial weight distribution on fixed June inputs. They do not measure sensor error, seasonal variation, source bias, target uncertainty, or probability of truth, site suitability, or mission success.

Changing the slope weight does not change the published ranking, because `slope_median_deg` is null on all 577134 land cells. The patch slopes stay a separate comparison.

The largest gap for the Mars case is an Earth ice/permafrost layer. None was used. Worldview snow is not that measurement. Confidence stays low while the Earth-side ice comparison is absent.
