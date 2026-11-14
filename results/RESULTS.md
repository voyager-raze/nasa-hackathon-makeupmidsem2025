# Partial Match

Team Mid-Sem Make Up, Delhi. Earth sites scored against the Shackleton–de Gerlache connecting ridge, with Arcadia Planitia (Badger) as the locked ground-ice case on Mars.

A similarity score is a partial match on the measured features, not a probability of mission success. A lower score is a closer partial match. The published scores used `ndvi_median`, `precip_median_mm_hr`, and `lst_night_median_k`. `slope_median_deg` was null in those scores. Gravity, vacuum or thin air, and radiation are stated below as limits. They are not rows in `results/sources.csv`.

The lunar slope rows are the locked Site01 tile: interquartile range 8.0-16.7 degrees, median 12.3 degrees, patch longitude -137.4771, patch latitude -89.4632, patch size 16 km (LOLA 5 m/pixel slope, Site01 connecting ridge).

## Site A — Kunlun Mountains

### Where it is

Kunlun Mountains, Rutog County, Ngari Prefecture, Tibet Autonomous Region, China. Less-famous site kept after the Worldview rejections. Patch center latitude 35.3, longitude 81.1. Patch size 0.2 deg x 0.2 deg. Cell `35.3_81.1`. Median elevation 6120.8 m (Copernicus DEM, GLO-30 Public, 2021 release).

On 2024-06-15, NASA Worldview Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD classed this patch as bare ground with ridgeline snow. The Kunlun Mountains label was read on 2024-09-20 in that layer. The row is a surface class.

The discovery cells in `results/sources.csv` classed as ice-sheet interior, and not kept, are latitude 73.5 longitude -40.5, latitude 73.5 longitude -40.7, latitude 73.9 longitude -40.1, latitude 73.5 longitude -40.9, and latitude 74.1 longitude -39.9. Each was classed on 2024-06-15 and confirmed on 2024-08-15.

Published score 0.186845. That is a worse partial match than the control score 0.167981.

### Matches

The score 0.186845 is the weighted distance of these three rows. No Moon or Mars value for these three quantities is in `results/sources.csv`. Each Earth number stands alone.

| Dimension | Earth value | Unit | Source |
| --- | --- | --- | --- |
| Vegetation | -0.01995 | NDVI | MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG, 061, 1-30 June 2024 |
| Dryness | 0.006 | mm/hr | GPM IMERG Final Precipitation L3 1 month 0.1 degree, 07 V07B, 1-30 June 2024 |
| Night temperature | 258.8 | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, 061, 1-30 June 2024 |
| Day temperature (descriptive; not scored) | 269.12 | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, 061, 1-30 June 2024 |
| Paired day–night range (descriptive; not scored) | 11.05 | kelvin | Same MOD11C3 file; median of paired valid-pixel `day - night` values |

Day temperature and paired range have no Moon or Mars referent in the source table.

### Breaks

Slope misses the lunar band. Median slope is 7.08 degrees (Copernicus DEM, GLO-30 Public, 2021 release). The locked lunar interquartile range is 8.0-16.7 degrees, and the lunar median is 12.3 degrees. The Earth median lies outside that band. This slope was measured after the score and was not part of 0.186845.

Gravity is a limit, not a value computed from a raster. Gravity on the Moon is about one-sixth of Earth. Gravity on Mars is about three-eighths of Earth. This patch is a full-Earth-gravity outdoor test.

Atmosphere is a limit, not a value computed from a raster. The Moon is a vacuum. Mars has thin carbon-dioxide air, roughly one percent of Earth’s surface pressure. This patch has Earth’s air.

Radiation is a limit, not a value computed from a raster. Air and the magnetic field block most of it at Earth’s surface. An outdoor test here does not qualify electronics or crews for the surface dose on the Moon or Mars.

Night temperature stands alone at 258.8 kelvin. A permanently shadowed lunar floor is not a thermal analog for any outdoor Earth site. No Diviner temperature is in `results/sources.csv`.

No ice or permafrost row is in `results/sources.csv`. Ridgeline snow in the Worldview class is a surface class. It is not a measured ice body, so this patch is not an operations analog for sampling lunar ice.

### How a mission would use it

The rehearsal is one rover drive on the measured median slope of 7.08 degrees, across the 0.2 deg x 0.2 deg patch whose median NDVI is -0.01995, logging wheel current. The drive uses the slope that was measured, outside the locked band of 8.0-16.7 degrees. Vacuum, radiation, and suit or landing-engine tests stay in a lab.

### Confidence

Low. The largest missing dataset is an ice or permafrost map. None was opened. That gap dominates. The published score also omitted slope, and the slope measured later falls outside the lunar band. Ice is unmeasured, so this site stays at low confidence.

The credibility pack is [notes/credibility.md](../notes/credibility.md), [notes/factor-coverage.md](../notes/factor-coverage.md), and [notes/sensitivity.md](../notes/sensitivity.md).

## Site B — Vinchina

### Where it is

Vinchina, Departamento Vinchina, La Rioja, Argentina. Famous control: the best cell inside the Atacama hold-out, scored with the same weights. The cell center is on the Argentine side of the Andean front. Patch center latitude -27.9, longitude -68.9. Patch size 0.2 deg x 0.2 deg. Cell `-27.9_-68.9`. Median elevation 5330.7 m (Copernicus DEM, GLO-30 Public, 2021 release).

On 2024-06-15 the same Worldview layer classed this patch as arid mountains. A closer look on 2024-11-15 in that layer showed bare mountains and small snow patches. The row is a surface class.

Published score 0.167981, from `ndvi_median`, `precip_median_mm_hr`, and `lst_night_median_k`. Slope was null in that score.

### Matches

Slope. Median slope is 9.48 degrees (Copernicus DEM, GLO-30 Public, 2021 release; the source row rounds 9.476 degrees to 9.48). The locked lunar interquartile range is 8.0-16.7 degrees, and the lunar median is 12.3 degrees (LOLA Site01, patch longitude -137.4771, patch latitude -89.4632). The Earth median is inside the band. The match is a mobility comparison on that slope range. The slope row was not part of the score 0.167981.

The score 0.167981 is the weighted distance of these three rows. No Moon or Mars value for these three quantities is in `results/sources.csv`. Each Earth number stands alone.

| Dimension | Earth value | Unit | Source |
| --- | --- | --- | --- |
| Vegetation | 0.00925 | NDVI | MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG, 061, 1-30 June 2024 |
| Dryness | 0.008 | mm/hr | GPM IMERG Final Precipitation L3 1 month 0.1 degree, 07 V07B, 1-30 June 2024 |
| Night temperature | 254.45 | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, 061, 1-30 June 2024 |
| Day temperature (descriptive; not scored) | 264.58 | kelvin | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, 061, 1-30 June 2024 |
| Paired day–night range (descriptive; not scored) | 10.44 | kelvin | Same MOD11C3 file; median of paired valid-pixel `day - night` values |

Day temperature and paired range have no Moon or Mars referent in the source table.

### Breaks

Gravity, atmosphere, and radiation are the same limits as at Site A. They were not computed from a raster. Gravity on the Moon is about one-sixth of Earth, and on Mars about three-eighths of Earth. The Moon is a vacuum, and Mars has thin carbon-dioxide air, roughly one percent of Earth’s surface pressure. Air and the magnetic field block most radiation here, so an outdoor test does not qualify electronics or crews for the surface dose.

Night temperature stands alone at 254.45 kelvin. A permanently shadowed lunar floor is not a thermal analog for this outdoor patch.

No ice or permafrost row is in `results/sources.csv`. Small snow patches in the Worldview check are a surface class, not a measured ice body.

Median elevation 5330.7 m has no lunar or Martian elevation in `results/sources.csv`. That Earth number stands alone.

### How a mission would use it

The control comparison supports one rover drive on the measured median slope of 9.48 degrees, inside the locked band of 8.0-16.7 degrees, on the patch whose median NDVI is 0.00925. That drive is the comparison for the Kunlun rehearsal. Vacuum, radiation, and suit or landing-engine tests stay in a lab.

### Confidence

Low. The largest missing dataset is an ice or permafrost map. None was opened. That gap dominates. The published score omitted slope. The slope measured later, 9.48 degrees, does fall inside 8.0-16.7 degrees, and that comparison is reported above as its own row. Ice is unmeasured, so this site stays at low confidence.

The credibility pack is [notes/credibility.md](../notes/credibility.md), [notes/factor-coverage.md](../notes/factor-coverage.md), and [notes/sensitivity.md](../notes/sensitivity.md).

## Mars

The case locked in `notes/targets.md` is ground ice. The region is Arcadia Planitia, the terraced crater Badger. No second Mars region was added.

Ground ice, in this dossier, uses cold and barren ground. The Earth rows that speak to that case are the night temperatures and the vegetation index already cited: 258.8 kelvin and NDVI -0.01995 at Kunlun, and 254.45 kelvin and NDVI 0.00925 at Vinchina. No Mars temperature and no Mars vegetation index are in `results/sources.csv`, so those Earth numbers stand alone. No ice or permafrost row exists in `results/sources.csv`. The ice link is untested.

## Source rows behind the scores

| Quantity | Value | Unit | Patch longitude | Patch latitude |
| --- | --- | --- | --- | --- |
| partial match score | 0.186845 | weighted distance | 81.1 | 35.3 |
| ndvi_median | -0.01995 | NDVI | 81.1 | 35.3 |
| precip_median_mm_hr | 0.006 | mm/hr | 81.1 | 35.3 |
| lst_night_median_k | 258.8 | kelvin | 81.1 | 35.3 |
| lst_day_median_k | 269.12 | kelvin | 81.1 | 35.3 |
| lst_day_night_range_median_k | 11.05 | kelvin | 81.1 | 35.3 |
| slope_median_deg | 7.08 | degrees | 81.1 | 35.3 |
| elevation_median | 6120.8 | m | 81.1 | 35.3 |
| partial match score | 0.167981 | weighted distance | -68.9 | -27.9 |
| ndvi_median | 0.00925 | NDVI | -68.9 | -27.9 |
| precip_median_mm_hr | 0.008 | mm/hr | -68.9 | -27.9 |
| lst_night_median_k | 254.45 | kelvin | -68.9 | -27.9 |
| lst_day_median_k | 264.58 | kelvin | -68.9 | -27.9 |
| lst_day_night_range_median_k | 10.44 | kelvin | -68.9 | -27.9 |
| slope_median_deg | 9.48 | degrees | -68.9 | -27.9 |
| elevation_median | 5330.7 | m | -68.9 | -27.9 |
| lunar slope interquartile range | 8.0-16.7 | degrees | -137.4771 | -89.4632 |
| lunar slope median | 12.3 | degrees | -137.4771 | -89.4632 |
