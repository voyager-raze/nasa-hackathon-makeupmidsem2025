## Slide 1 — Partial Match

Partial Match

Team Mid-Sem Make Up. Local event: Delhi, NASA Space Apps 2026.

Challenge: Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.

## Slide 2 — The problem

A base site is chosen for specific traits.

A look-alike photo is not a result.

Earth can rehearse some of those traits.

## Slide 3 — Our targets

Moon: Shackleton–de Gerlache connecting ridge. Center 89.4632°S, 137.4771°W (222.5229°E).

The Moon trait is the ridge or rim operations analog: slope, barren ground, cold, and the nearby cold-trap limit.

Locked slope band 8.0-16.7 degrees, median 12.3 degrees, on the 16 km LOLA Site01 tile.

Mars: Arcadia Planitia, the terraced crater Badger, 46.581°N, 194.85°E. Locked case: ground ice. Those coordinates are the locked target. No Badger ice, mineral, or dust measurement is in the source table.

No second planetary target.

## Slide 4 — Data and method

NASA Earthdata Search, https://search.earthdata.nasa.gov/, supplied the June 2024 layers: MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG, 061; MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG, 061; and GPM IMERG Final Precipitation L3 1 month 0.1 degree, 07 V07B.

NASA Worldview, https://worldview.earthdata.nasa.gov/, supplied the surface classes. Patch slopes used Copernicus DEM, GLO-30 Public, 2021 release. The lunar slope used LOLA 5 m/pixel slope, Site01 connecting ridge.

Default weights: slope, vegetation, precipitation, and night temperature each have weight 1.0. A larger weight pulls the weighted distance toward that feature. A lower score is a closer partial match. Slope was null in the published scores, so those scores used vegetation, precipitation, and night temperature.

Missing data was left blank.

## Slide 5 — What we found

Site A is the Kunlun Mountains, Rutog County, Ngari Prefecture, Tibet Autonomous Region, China. 35.3°N, 81.1°E.

Site B is Vinchina, Departamento Vinchina, La Rioja, Argentina. 27.9°S, 68.9°W. Famous control: the best cell inside the Atacama hold-out, scored with the same weights.

Site B at 0.167981 is a closer partial match than Site A at 0.186845. Both scores used June 2024 vegetation, precipitation, and night temperature. Slope was null in both scores.

| Measurement | Kunlun (Site A) | Vinchina (Site B) |
| --- | --- | --- |
| Vegetation | -0.01995 NDVI | 0.00925 NDVI |
| Precipitation | 0.006 mm/hr | 0.008 mm/hr |
| Night land-surface temperature | 258.8 kelvin | 254.45 kelvin |

## Slide 6 — Where the analogy breaks

Gravity, vacuum or thin carbon-dioxide air, and radiation are limits. They are not rows in the source table.

Gravity on the Moon is about one-sixth of Earth. Gravity on Mars is about three-eighths of Earth. Both patches are full-Earth-gravity outdoor ground.

The Moon is a vacuum. Mars has thin carbon-dioxide air, roughly one percent of Earth’s surface pressure. Both patches have Earth’s air.

Air and the magnetic field block most radiation at Earth’s surface, so an outdoor test here does not qualify electronics or crews for the surface dose on the Moon or Mars.

The largest gap is an ice or permafrost map. None was opened. No Diviner temperature is in the source table. Kunlun’s median slope is 7.08 degrees, outside the locked band of 8.0-16.7 degrees. Vinchina’s median slope is 9.48 degrees, inside that band. Both slope rows were measured after the score.

The rehearsal is one rover drive on the measured median slope of 7.08 degrees, across the patch whose median NDVI is -0.01995, logging wheel current.

Vacuum, radiation, and suit tests stay in a lab.

## Slide 7 — Limits and links

Confidence is low. The largest missing dataset is an ice or permafrost map. None was opened.

The grid cell is 0.2° by 0.2°: 22.3 km north-south, and east-west 22.3 km times the cosine of latitude, about 22.3 km at the equator and about 11.1 km at 60° latitude.

The grid cannot see a boulder, a narrow rim, or a single drill site inside a 10 to 50 km cell.

Repository: REPO_URL_HERE

Data: https://search.earthdata.nasa.gov/ and https://worldview.earthdata.nasa.gov/

https://doi.org/10.5067/MODIS/MOD13C2.061

https://doi.org/10.5067/MODIS/MOD11C3.061

https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07

https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slp.tif

https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/Copernicus_DSM_COG_10_N35_00_E081_00_DEM/Copernicus_DSM_COG_10_N35_00_E081_00_DEM.tif

https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/Copernicus_DSM_COG_10_S28_00_W069_00_DEM/Copernicus_DSM_COG_10_S28_00_W069_00_DEM.tif
