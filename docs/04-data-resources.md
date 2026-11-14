# Data and resources

Use at least one dataset from the official Resources tab inside the solution. Extra datasets are welcome. A NASA photo or a sentence from a fact sheet does not, by itself, meet the data requirement.

The links in the first two sections are the ones on the Resources tab of the challenge page saved for this team. Cite these URLs in the submission. Tracking parameters that were attached in the saved file are left off.

## Official NASA resources

| Resource | What it is | Link |
| --- | --- | --- |
| NASA Earthdata Search | The main portal for finding and downloading NASA Earth observations | [search.earthdata.nasa.gov](https://search.earthdata.nasa.gov/) |
| NASA Worldview | A browser map for browsing satellite imagery and environmental layers | [worldview.earthdata.nasa.gov](https://worldview.earthdata.nasa.gov/) |
| NASA Planetary Data System (PDS) | The long-term archive for NASA planetary missions, including Moon and Mars imagery, geoscience, atmospheres, and maps | [pds.nasa.gov](https://pds.nasa.gov/) |
| Lunar Reconnaissance Orbiter (LRO) | LRO holdings in the PDS Geosciences Node: LROC, LOLA, Diviner, LEND, Mini-RF, and related products | [pds-geosciences.wustl.edu/missions/lro](https://pds-geosciences.wustl.edu/missions/lro/) |
| LRO Diviner | Diviner surface-temperature products, including polar temperature maps for very cold shadowed ground | [PDS Diviner page](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) |

## Official partner resources

NASA does not endorse these sites. Follow each site’s data-use rules.

| Agency | Resource | Why it is on the list | Link |
| --- | --- | --- | --- |
| CSA | RADARSAT Constellation Mission | Radar images of Earth, day or night, through cloud. Useful for ice, surface roughness, and terrain | [CSA RCM dataset](https://donnees-data.asc-csa.gc.ca/en/dataset/rcm) |
| CSA | RADARSAT-1 archive | Older radar archive, released under an open license | [CSA RADARSAT-1 dataset](https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1) |
| CSA | SAR Python tutorial | A practical path into radar imagery with Python and QGIS | [asc-csa/Synthetic_Aperture_Radar_Tutorial](https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial) |
| ESA | Copernicus Data Space Ecosystem | Sentinel data for land, ocean, and atmosphere, with a browser and processing tools | [dataspace.copernicus.eu](https://dataspace.copernicus.eu/) |
| ESA | ESA Open Science Catalog | Public geoscience datasets, products, and workflows | [opensciencedata.esa.int](https://opensciencedata.esa.int/) |
| JAXA | G-Portal | Earth-observation products searchable by variables such as precipitation, snow, and vegetation | [gportal.jaxa.jp/gpr](https://gportal.jaxa.jp/gpr/index/index) |

## Use these first

Open data in this order. Stop when the dossier has a source for every number. Do not try to download the world at 30 m resolution tonight.

| Order | Dataset | Planet | Use it for | Access |
| --- | --- | --- | --- | --- |
| 1 | NASA Worldview | Earth | Look at the candidate region in true color and in a temperature or vegetation layer. Save screenshots with the layer name and date visible | Browser, no login |
| 2 | Earthdata Search: MODIS land surface temperature and a vegetation index (NDVI) | Earth | Cold versus hot ground, and barren versus green ground, on a coarse global grid | [Earthdata Search](https://search.earthdata.nasa.gov/). A free Earthdata login is needed to download |
| 3 | SRTM GL1 (about 30 m) or Copernicus DEM (about 30 m or 90 m) for the shortlisted patches only | Earth | Elevation, then slope. SRTM covers roughly 60°N to 56°S, so Antarctica and far-northern sites need a different elevation model | Earthdata Search, short name `SRTMGL1` |
| 4 | LOLA elevation and one LROC view of the named rim, via the PDS LRO page or Moon Trek | Moon | The target slope and a picture of the ridge the Earth site is being compared with | [PDS LRO](https://pds-geosciences.wustl.edu/missions/lro/) and [Moon Trek](https://trek.nasa.gov/moon) |
| 5 | Diviner temperature for that lunar region | Moon | Show the Earth temperature analog breaking, especially if the lunar site is a cold trap | [PDS Diviner page](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) |
| 6 | Mars Trek: CTX mosaic and MOLA hillshade | Mars | Name and show the Mars target | [Mars Trek](https://trek.nasa.gov/mars) |
| 7 | Only if the case needs it: EMIT minerals on Earth, CRISM minerals on Mars | Both | A mineral sentence, such as clays or salts, for the patch you already chose | Earthdata short name `EMITL2BMIN`; CRISM through the PDS Geosciences Orbital Data Explorer |

Coarse global files are the right tool for the screen. Fine files are the right tool for the two or three patches you will actually describe. HLS Landsat and Sentinel-2 surface reflectance (Earthdata short names `HLSL30` and `HLSS30`) are the zoom lens for a final patch, not the first download.

## A screen that can finish in one night

Compute these on a coarse grid. A cell of about 10–50 km is enough to find regions. The dossier then zooms in.

**Moon-operations screen (Earth cells):**

- Median slope in a band that matches the chosen lunar rim (compute the lunar number first; do not invent the band).
- Vegetation index near zero.
- Low rainfall or a very dry climate class, from a published climate raster you can cite.
- A cold tail in land-surface temperature, or a high diurnal range.
- Prefer cells that are **not** inside the famous control region, then score that famous region separately with the same formula.

**Mars screen:** reuse the same grid. Change the weights to match the case.

- Ground-ice case: favor cold, barren, and near-surface ice or permafrost if a cited map exists. If you cannot cite an ice map, do not invent ice. Say the ice link is untested.
- Dust-and-salts case: favor low vegetation, a dust or aerosol signal, and flat-to-moderate slope. Add an EMIT mineral note only for the finalist patch.

Write the formula in the repo. A weighted distance is enough. For each feature, scale the Earth value and the target value to the same unit, then combine. Show the weights. If a feature is missing, leave it out of the score and lower the confidence. Do not fill it with a guess.

## What to record for every number

Judges trust a result they can replay. For each value in the dossier, keep one line:

- Quantity and unit
- Dataset name and version
- Date or date range
- Link or DOI
- The patch (longitude, latitude, and size)
- What you did (median slope, mean night temperature, and so on)

Store that table in the repo as `sources.csv` or a short `SOURCES.md`. Paste the same links into the NASA Data field and the References field on the project form.

## Accounts to create at the start of the work session

- An **Earthdata Login**, if downloads are needed. Searching Earthdata does not always require it. Downloading usually does.
- A **GitHub** repository that can be set to public before submission.
- A place to host the seven slides with a link that works without asking for permission (GitHub, Google Drive set to anyone with the link, or similar).

## Browser tools if code is late

The project can still be valid without a large pipeline.

- Worldview for the Earth images and environmental layers.
- Moon Trek and Mars Trek for the planetary images and terrain.
- Earthdata Search for the dataset citation, even if the “analysis” is a careful reading of a small downloaded tile.
- QGIS, if it is already installed, for slope on one tile.

If this fallback is used, say exactly which layers were read and what was compared by hand. A documented manual comparison beats a broken global model.

## Data we will not rely on

- A red-tinted photo as evidence of mineralogy.
- Uncited blog numbers for lunar or Martian temperature.
- A global 30 m stack of every layer. It will not finish, and the screen does not need it.
- Any claim about gravity, vacuum, or radiation “matching” an outdoor Earth site.
