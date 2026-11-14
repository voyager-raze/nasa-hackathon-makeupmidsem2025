# Science check

Checked against `results/sources.csv` on 15 November 2026. The source table wins. Gravity, vacuum or thin air, and radiation are limits, not measurements.

`web/index.html` is the page linked from the root README. Its banner says: “The score is a partial match on measured features, not a probability of mission success.” The Moon panel is Shackleton–de Gerlache connecting ridge. The Mars panel is Arcadia Planitia, the terraced crater Badger. Weights were not changed.

## Claims checked

Each line names the `results/sources.csv` quantity, or states that the claim is a limit.

| Claim in the README or in `results/RESULTS.md` | Source |
| --- | --- |
| Site A score 0.186845, cell 35.3°N, 81.1°E, patch 0.2 deg x 0.2 deg | `partial match score` at longitude 81.1, latitude 35.3 |
| Site A NDVI −0.01995 | `ndvi_median` at 81.1, 35.3 |
| Site A precipitation 0.006 mm/hr | `precip_median_mm_hr` at 81.1, 35.3 |
| Site A night temperature 258.8 kelvin | `lst_night_median_k` at 81.1, 35.3 |
| Site A median slope 7.08 degrees, from 7.078 degrees | `slope_median_deg` at 81.1, 35.3. The value column is 7.08. The method text says rounded from 7.078 degrees. |
| Site A median elevation 6120.8 m, from 6120.757 m | `elevation_median` at 81.1, 35.3 |
| Site A surface class “bare ground with ridgeline snow”, 2024-06-15, Kunlun label read 2024-09-20 | `worldview surface` at 81.1, 35.3 |
| Site B score 0.167981, cell 27.9°S, 68.9°W | `partial match score` at longitude −68.9, latitude −27.9 |
| Site B NDVI 0.00925 | `ndvi_median` at −68.9, −27.9 |
| Site B precipitation 0.008 mm/hr | `precip_median_mm_hr` at −68.9, −27.9 |
| Site B night temperature 254.45 kelvin | `lst_night_median_k` at −68.9, −27.9 |
| Site B median slope 9.48 degrees, from 9.476 degrees, inside 8.0–16.7 | `slope_median_deg` at −68.9, −27.9, compared with `lunar slope interquartile range` |
| Site B median elevation 5330.7 m, from 5330.746 m | `elevation_median` at −68.9, −27.9 |
| Site B surface class “arid mountains”, 2024-06-15; closer look 2024-11-15 showed bare mountains and small snow patches | `worldview surface` at −68.9, −27.9 |
| Lunar slope band 8.0–16.7 degrees, median 12.3 degrees, patch longitude −137.4771, patch latitude −89.4632, patch size 16 km | `lunar slope interquartile range` and `lunar slope median` |
| Moon name Shackleton–de Gerlache connecting ridge, and the east-longitude form 222.5229°E | Same lunar patch coordinates. 222.5229°E is the east-longitude form written in `notes/targets.md` for longitude −137.4771. |
| Five cells classed ice-sheet interior and not kept: (73.5, −40.5), (73.5, −40.7), (73.9, −40.1), (73.5, −40.9), (74.1, −39.9), dates 2024-06-15 and 2024-08-15 | five `worldview surface` rows, value `ice-sheet interior` |
| Site A slope 7.08 degrees lies outside 8.0–16.7 degrees | comparison of the two source values above |
| Gravity about one-sixth of Earth on the Moon, and about three-eighths of Earth on Mars | gravity limit, not a measurement |
| The Moon is a vacuum. Mars has thin carbon-dioxide air, roughly one percent of Earth’s surface pressure | atmosphere limit, not a measurement |
| Outdoor Earth tests do not qualify electronics or crews for the Moon or Mars surface dose | radiation limit, not a measurement |
| A permanently shadowed lunar floor is colder than any outdoor Earth site, and no Diviner temperature is cited as a result | limit. No Diviner quantity exists in `results/sources.csv`. The cited night temperatures are the Earth `lst_night_median_k` rows only. |
| Earth cell size 0.2° by 0.2° | `patch size` on the Earth rows |
| Python 3.13.9 | `python --version` on this machine during this check. It is the interpreter named for a rerun. It is not a science measurement. |

## Claims removed

These phrases were in `results/RESULTS.md` and disagreed with `results/sources.csv`. The value column for Vinchina slope is 9.48. The method text says rounded from 9.476 degrees. 9.47 is a different rounding, so it was replaced with 9.48. `results/sources.csv` was not edited.

| Phrase removed | Why |
| --- | --- |
| “Median slope is 9.47 degrees” | Source value is 9.48 degrees at longitude −68.9, latitude −27.9. |
| “the measured median slope of 9.47 degrees” | Same row. |
| “The slope measured later, 9.47 degrees” | Same row. |
| Table cell `9.47` for `slope_median_deg` at longitude −68.9, latitude −27.9 | The source value is 9.48. |

No other number in `results/RESULTS.md` disagreed with the source table. The README was new in this chat, so it was written from the source values and does not carry a deleted numeric claim of its own.

Discovery-rank scores such as 0.162265 appear on the map page and in `results/score-notes.md`. They have no row in `results/sources.csv`, so they were left out of the README and out of `results/RESULTS.md`. The five cells stay in the prose only as the ice-sheet classes that do have source rows.

## Claims left with low confidence

| Claim | Largest missing dataset |
| --- | --- |
| Either Earth patch can rehearse sampling ice for the Moon ridge or for Badger’s ground ice. The dossiers call this confidence low. Snow in the Worldview class is a surface class. | An ice or permafrost map. None was opened. `notes/data-log.md` records that no ice file was logged. |
| The locked Mars case is ground ice at Badger, 46.581°N, 194.85°E. Those coordinates and the case name are the locked target in `notes/targets.md`. They are not a row in `results/sources.csv`. Minerals, an ice-map raster, and a dust index are blank there. | An ice or permafrost map, the same gap as above. No Mars temperature, vegetation, mineral, or dust quantity is in the source table. |
| The published scores describe the global screen. Slope was null on every land cell in that screen. The 7.08 and 9.48 degree figures cover only the two patches. | A global elevation model. `notes/data-log.md` records that global elevation was not downloaded. |
| June 2024 NDVI, night temperature, and precipitation stand in for the sites’ vegetation, cold, and dryness. | The other months of MOD13C2, MOD11C3, and GPM IMERG. This June granule is one month, not a climate normal. |
| Cell length 22.3 km north–south, about 11.1 km east–west at 60° latitude, and 577134 land cells. NDVI blank on every land cell south of 60°S. | These figures are the grid record in `notes/features.md`, not rows in `results/sources.csv`. The 0.2° patch size is the quantity the source table does record. |
