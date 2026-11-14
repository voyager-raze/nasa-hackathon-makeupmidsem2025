# Partial Match

Team Mid-Sem Make Up. Local event: Delhi, NASA Space Apps 2026. Challenge: Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.

The score is a partial match on measured features, not a probability of mission success. A lower score is a closer partial match.

The page a judge opens is [`web/index.html`](web/index.html). That page states the same score sentence. Double-click the file, or open it from the repository root on GitHub Pages.

| Place | Site |
| --- | --- |
| Moon | Shackleton–de Gerlache connecting ridge. Center 89.4632°S, 137.4771°W (222.5229°E). Locked slope band 8.0–16.7 degrees, median 12.3 degrees, on the 16 km LOLA Site01 tile. |
| Mars | Arcadia Planitia, the terraced crater Badger, 46.581°N, 194.85°E. Locked case: ground ice. |
| Site A | Kunlun Mountains, Rutog County, Ngari Prefecture, Tibet Autonomous Region, China. 35.3°N, 81.1°E. Cell `35.3_81.1`. Score **0.186845**. |
| Site B | Vinchina, Departamento Vinchina, La Rioja, Argentina. 27.9°S, 68.9°W. Cell `-27.9_-68.9`. Score **0.167981**. Famous control: the best cell inside the Atacama hold-out, scored with the same weights. |

Site B at 0.167981 is a closer partial match than Site A at 0.186845. Both scores used June 2024 `ndvi_median`, `precip_median_mm_hr`, and `lst_night_median_k`. `slope_median_deg` was null in both scores.

**What matches.** Only quantities with a row in [`results/sources.csv`](results/sources.csv).

Kunlun, June 2024, on a 0.2° by 0.2° cell: vegetation index −0.01995 NDVI, precipitation 0.006 mm/hr, night land-surface temperature 258.8 kelvin. Vinchina, same month and cell size: vegetation index 0.00925 NDVI, precipitation 0.008 mm/hr, night land-surface temperature 254.45 kelvin. Both vegetation indexes sit near zero, and both precipitation rates sit near the dry end of the logged unit. No Moon or Mars value for vegetation, precipitation, or night temperature is in the source table, so each Earth number stands alone.

Vinchina’s median slope is 9.48 degrees (the source row rounds 9.476 degrees to 9.48). That median sits inside the lunar band of 8.0–16.7 degrees, whose median is 12.3 degrees. The match is a mobility comparison on that slope range. The slope row was measured after the score and is outside the score 0.167981.

NASA Worldview Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD, classed Kunlun on 2024-06-15 as bare ground with ridgeline snow, and classed Vinchina on 2024-06-15 as arid mountains. A closer look at Vinchina on 2024-11-15 showed bare mountains and small snow patches. Those rows are surface classes.

**What breaks.** Gravity, vacuum or thin air, and radiation are limits. They are standard conditions Earth cannot copy outdoors. They are not rows in `results/sources.csv`.

Gravity on the Moon is about one-sixth of Earth. Gravity on Mars is about three-eighths of Earth. Both patches are full-Earth-gravity outdoor ground. The Moon is a vacuum. Mars has thin carbon-dioxide air, roughly one percent of Earth’s surface pressure. Both patches have Earth’s air. Air and the magnetic field block most radiation at Earth’s surface, so an outdoor test here does not qualify electronics or crews for the surface dose on the Moon or Mars.

Kunlun’s median slope is 7.08 degrees (the source row rounds 7.078 degrees to 7.08). That median sits outside the locked band of 8.0–16.7 degrees. The Kunlun rehearsal is one rover drive on that measured 7.08 degree slope, across the cell whose median NDVI is −0.01995, logging wheel current. Vinchina’s comparison drive uses the measured 9.48 degree slope, inside 8.0–16.7 degrees, on the cell whose median NDVI is 0.00925. Vacuum, radiation, and suit or landing-engine tests stay in a lab.

Night temperature stands alone at 258.8 kelvin at Kunlun and 254.45 kelvin at Vinchina. A permanently shadowed lunar floor is colder than any outdoor place on Earth. No Diviner temperature is in `results/sources.csv`. No ice or permafrost row is in that table. Ridgeline snow and small snow patches are surface classes, so neither patch is an operations analog for sampling lunar ice. Median elevation is 6120.8 m at Kunlun (rounded from 6120.757 m) and 5330.7 m at Vinchina (rounded from 5330.746 m). No lunar or Martian elevation is in the source table.

Five discovery cells were classed ice-sheet interior on 2024-06-15 and confirmed on 2024-08-15, and were not kept: 73.5°N, 40.5°W; 73.5°N, 40.7°W; 73.9°N, 40.1°W; 73.5°N, 40.9°W; and 74.1°N, 39.9°W.

## How to rerun

On this machine, `python --version` reports **Python 3.13.9**. Install the packages named in [`requirements.txt`](requirements.txt): `pandas`, `numpy`, `rasterio`, and `folium`. That file does not pin versions.

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

`src/export_map_data.py` is the map rebuild named in [`notes/map.md`](notes/map.md). It rewrites `web/index.html`.

The two patch slopes and elevations come from Copernicus DEM GLO-30 Public tiles that are also outside git. Their URLs are on the `slope_median_deg` and `elevation_median` rows in `results/sources.csv`. The local files used were `data/raw/cop30_N35.3_E81.1.tif` and `data/raw/cop30_S27.9_W68.9.tif`. With those tiles present, `python src/local_slope.py` rewrites those rows. The LOLA Site01 slope tile is not in the repository. It was read on 14 November 2026 and the band was copied into `notes/targets.md` and `results/sources.csv`.

## Limits and nulls

Each Earth cell in the screen is 0.2° by 0.2°, the patch size on the Earth rows in `results/sources.csv`. [`notes/features.md`](notes/features.md) records that cell as 22.3 km north–south, and east–west as 22.3 km times the cosine of latitude: about 22.3 km at the equator and about 11.1 km at 60° latitude. The table holds 577134 land cells. June 2024 is one month. It is summer in the north and winter in the south. It is not a climate normal.

Earth cannot copy gravity, vacuum, thin carbon-dioxide air, or radiation. Those limits are stated above.

`slope_median_deg` and `slope_valid_count` are blank on every land cell in the feature grid, so the published scores left slope out. The 7.08 degree and 9.48 degree figures are later measurements of the two patches only. A blank vegetation, night-temperature, or precipitation value means the layer did not cover that cell. Every land cell south of 60°S has a blank NDVI in this June table. Minerals, an ice-map raster, and a dust index for Badger are blank in [`notes/targets.md`](notes/targets.md). No ice or permafrost map was opened. A null feature is part of the result.

## Read next

- [`results/RESULTS.md`](results/RESULTS.md) — the two dossiers
- [`results/sources.csv`](results/sources.csv) — every measured number
- [`notes/data-log.md`](notes/data-log.md) — granule names, versions, and URLs
