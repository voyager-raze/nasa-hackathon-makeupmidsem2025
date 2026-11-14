# Mission Analog Readiness

Team Mid-Sem Make Up. Local event: Delhi, NASA Space Apps 2026. Challenge: Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.

The score is a partial match on measured features, not a probability of mission success. A lower score is a closer partial match. The dashboard now shows a NASA Curiosity drive-completion reference rate with its Wilson interval, while making clear that this is not a candidate-site or whole-mission forecast. Candidate-specific success probability is not supported by the current one-month Earth proxy dataset.

This is a heuristic screening index: the three scored Earth features have no direct Moon or Mars referent in the cited source table. The target values are explicit proxies, not planetary measurements. June 2024 is one month, not a climate normal.

A separate multi-year path now supports monthly inputs, annualized 10-year features, seasonal extremes, and interannual variability. It does **not** replace the published June baseline. Only June 2024 is available locally, so no 10-year score or new ranking has been produced.

The page a judge opens is [`web/index.html`](web/index.html). It keeps the map and selection details in the existing no-page-scroll desktop layout. Double-click the file, or open it from the repository root on GitHub Pages.

| Place | Site |
| --- | --- |
| Moon | Shackleton–de Gerlache connecting ridge. Center 89.4632°S, 137.4771°W (222.5229°E). Locked slope band 8.0–16.7 degrees, median 12.3 degrees, on the 16 km LOLA Site01 tile. |
| Mars | Arcadia Planitia, the terraced crater Badger, 46.581°N, 194.85°E. [Bramson et al. (2015)](https://doi.org/10.1002/2015GL064844) infer a mostly excess-ice layer at a flat terrace 43 m deep; this project did not process a local ice map. |
| Site A | Kunlun Mountains, Rutog County, Ngari Prefecture, Tibet Autonomous Region, China. 35.3°N, 81.1°E. Cell `35.3_81.1`. Score **0.186845**. |
| Site B | Vinchina, Departamento Vinchina, La Rioja, Argentina. 27.9°S, 68.9°W. Cell `-27.9_-68.9`. Score **0.167981**. Hold-out comparator: the best eligible cell inside the defined Atacama-region box, scored with the same weights. |

Site B at 0.167981 is closer on the three June 2024 Earth proxies than Site A at 0.186845. Both scores used `ndvi_median`, `precip_median_mm_hr`, and `lst_night_median_k`; `slope_median_deg` was null in both. The later, separate slope check also places Vinchina (9.48°) inside the Moon's 8.0–16.7° band, while Kunlun (7.08°) is below it. Among these two, study Vinchina first for terrain-only mobility and keep Kunlun as a lower-slope comparison. Neither is a validated analog.

**What matches.** Only quantities with a row in [`results/sources.csv`](results/sources.csv).

Kunlun, June 2024, on a 0.2° by 0.2° cell: vegetation index −0.01995 NDVI, precipitation 0.006 mm/hr, night land-surface temperature 258.8 kelvin. Vinchina, same month and cell size: vegetation index 0.00925 NDVI, precipitation 0.008 mm/hr, night land-surface temperature 254.45 kelvin. Both vegetation indexes sit near zero, and both precipitation rates sit near the dry end of the logged unit. No Moon or Mars value for vegetation, precipitation, or night temperature is in the source table, so each Earth number stands alone.

Vinchina’s median slope is 9.48 degrees (the source row rounds 9.476 degrees to 9.48). That median sits inside the lunar band of 8.0–16.7 degrees, whose median is 12.3 degrees. The match is a mobility comparison on that slope range. The slope row was measured after the score and is outside the score 0.167981.

NASA Worldview Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD, classed Kunlun on 2024-06-15 as bare ground with ridgeline snow, and classed Vinchina on 2024-06-15 as arid mountains. A closer look at Vinchina on 2024-11-15 showed bare mountains and small snow patches. Those rows are surface classes.

**What breaks.** Gravity, vacuum or thin air, and radiation are limits. They are standard conditions Earth cannot copy outdoors. They are not rows in `results/sources.csv`.

Gravity on the Moon is about one-sixth of Earth. Gravity on Mars is about three-eighths of Earth. Both patches are full-Earth-gravity outdoor ground. The Moon is a vacuum. Mars has thin carbon-dioxide air, roughly one percent of Earth’s surface pressure. Both patches have Earth’s air. Air and the magnetic field block most radiation at Earth’s surface, so an outdoor test here does not qualify electronics or crews for the surface dose on the Moon or Mars.

The proposed comparison uses Kunlun as the lower-slope site and Vinchina as the in-band site. After route-scale terrain, surface-material, access, and safety checks, run matched-length traverses with the same rover setup, payload, and speed. Record local slope and material; measure wheel energy per distance, slip, and interruptions over repeated runs. Site differences would not isolate slope as the cause. The trial has not been run. Vacuum, radiation, and suit or landing-engine tests stay in a lab.

Night temperature stands alone at 258.8 kelvin at Kunlun and 254.45 kelvin at Vinchina. A permanently shadowed lunar floor is colder than any outdoor place on Earth. No Diviner temperature is in `results/sources.csv`. Bramson et al. (2015) provide published radar evidence for the Mars ground-ice target, but no Earth ice or permafrost layer was used; neither Earth patch is claimed as an ice-sampling analog. Ridgeline snow and small snow patches are surface classes. Median elevation is 6120.8 m at Kunlun (rounded from 6120.757 m) and 5330.7 m at Vinchina (rounded from 5330.746 m). No lunar or Martian elevation is in the source table.

Five discovery cells were classed ice-sheet interior on 2024-06-15 and confirmed on 2024-08-15, and were not kept: 73.5°N, 40.5°W; 73.5°N, 40.7°W; 73.9°N, 40.1°W; 73.5°N, 40.9°W; and 74.1°N, 39.9°W.

## How to rerun

On the original build machine, `python --version` reported **Python 3.13.9**. Install the packages named in [`requirements.txt`](requirements.txt): `pandas`, `numpy`, `h5py`, `pyhdf`, `rasterio`, and `folium`. That file does not pin versions.

The coarse rasters are not in git. `.gitignore` ignores `*.hdf`, `*.h5`, `*.hdf5`, `*.he5`, and `*.tif`. Filenames, versions, and URLs for the three June 2024 granules are in [`notes/data-log.md`](notes/data-log.md):

- `data/raw/MOD13C2.A2024153.061.2024198104950.hdf`
- `data/raw/MOD11C3.A2024153.061.2024187024328.hdf`
- `data/raw/3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5`

With those three files on disk, in this order:

```
python src/build_features.py
python src/score.py
python src/export_map_data.py
```

### Multi-year rerun

The monthly builder accepts a year and month, resolves the matching MOD13C2, MOD11C3, and IMERG granules in `data/raw/`, and writes a compressed table under `data/processed/monthly/YYYY-MM/`. For example:

```
python src/build_features.py --year 2024 --month 6
```

Preflight and build all 120 monthly tables for 2015–2024, then run:

```
python src/build_monthly_range.py --start-year 2015 --end-year 2024
python src/build_climatology.py --start-year 2015 --end-year 2024
python src/score_climatology.py --start-year 2015 --end-year 2024
```

The climatology builder requires at least 10 valid months per cell-year and at least 8 valid years per cell by default. A monthly cell value is accepted only with at least 8/16 valid MODIS pixels or 2/4 valid IMERG pixels. It checks every input table, its sidecar manifest and checksums, and coordinate grid, preserving missing values. Monthly manifests record SHA-256 hashes for the processed table and three source granules; the climatology manifest carries those hashes forward. Quality flags are explicitly recorded as unfiltered. The output contains day-weighted annual means, interannual standard deviations, seasonal monthly extremes, and spatial/time coverage counts. The separate climatology score uses the annual NDVI and precipitation rate plus the average coldest-month night temperature; it recomputes scales from that decade and remains a heuristic, not a success probability. Its outputs go under `results/climatology/` and cannot overwrite the published June results.

The 2015–2024 run currently stops before aggregation: 119 of 120 monthly feature tables are absent. The only local monthly granules are June 2024. See [`notes/data-log.md`](notes/data-log.md); no decade ranking is available yet.

`src/export_map_data.py` is the map rebuild named in [`notes/map.md`](notes/map.md). It rewrites `web/index.html`.

The two patch slopes and elevations come from Copernicus DEM GLO-30 Public tiles that are also outside git. Their URLs are on the `slope_median_deg` and `elevation_median` rows in `results/sources.csv`. The local files used were `data/raw/cop30_N35.3_E81.1.tif` and `data/raw/cop30_S27.9_W68.9.tif`. With those tiles present, `python src/local_slope.py` rewrites those rows. The LOLA Site01 slope tile is not in the repository. It was read on 14 November 2026 and the band was copied into `notes/targets.md` and `results/sources.csv`.

## Limits and nulls

Each Earth cell in the screen is 0.2° by 0.2°, the patch size on the Earth rows in `results/sources.csv`. [`notes/features.md`](notes/features.md) records that cell as 22.3 km north–south, and east–west as 22.3 km times the cosine of latitude: about 22.3 km at the equator and about 11.1 km at 60° latitude. The table holds 577134 land cells. June 2024 is one month. It is summer in the north and winter in the south. It is not a climate normal.

Earth cannot copy gravity, vacuum, thin carbon-dioxide air, or radiation. Those limits are stated above.

`slope_median_deg` and `slope_valid_count` are blank on every land cell in the feature grid, so the published scores left slope out. The 7.08 degree and 9.48 degree figures are later measurements of the two patches only. A blank vegetation, night-temperature, or precipitation value means the layer did not cover that cell. Every land cell south of 60°S has a blank NDVI in this June table. Minerals, an ice-map raster, and a dust index for Badger are blank in [`notes/targets.md`](notes/targets.md). No ice or permafrost map was opened. A null feature is part of the result.

## Credibility pack

The score is a partial match on measured features, not a probability of mission success. A lower score is a closer partial match.

- [`notes/credibility.md`](notes/credibility.md) — pedigree, verification, validation, and uncertainty
- [`notes/factor-coverage.md`](notes/factor-coverage.md) — which traits are measured, missing, or limits
- [`notes/sensitivity.md`](notes/sensitivity.md) — what the Site A and Site B order does when a weight is set to 0

The page is an analog screen for a rover rehearsal on measured ground. Vacuum, radiation, and suit or landing-engine tests stay in a lab.

## Read next

- [`results/RESULTS.md`](results/RESULTS.md) — the two dossiers
- [`results/sources.csv`](results/sources.csv) — every measured number
- [`notes/data-log.md`](notes/data-log.md) — granule names, versions, and URLs
