# Data log

Coarse Earth layers for Partial Match. This chat did not score cells, did not write `data/processed/features.csv`, and did not choose Site A or Site B.

The locked Mars case stays **ground ice**, Arcadia Planitia, the terraced crater Badger. No second Mars search was opened. No ice raster was opened. The ice link stays untested. Do not invent ice.

Checked again on 14 November 2026 with an Earthdata Login token supplied for this session. The token is not stored in this repository. After the account authorized NASA GESDISC DATA ARCHIVE, all three June 2024 granules downloaded.

June 2024 is one month, not a climate normal. June is summer in the north and winter in the south. A later chat that needs a year should download the other months of the same short name and add them here. It must not treat this June granule as an annual value.

`.gitignore` ignores `*.hdf`, `*.h5`, `*.hdf5`, and `*.he5`, so these files stay on this machine and are not committed. The filename in this log is the record.

## Resources-tab dataset this project will use

The project will actually use **NASA Earthdata Search**, https://search.earthdata.nasa.gov/, to obtain the three coarse layers below. That portal is on the challenge Resources tab. MODIS and GPM IMERG are the measurements inside that portal. They do not replace it.

Moon Trek and Mars Trek were used only to lock the targets in the previous chat. They are not the Earth-layer source.

## Vegetation

| Item | Value |
| --- | --- |
| Dataset | MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG |
| Short name | `MOD13C2` |
| Version | 061 |
| DOI | https://doi.org/10.5067/MODIS/MOD13C2.061 |
| Date range | 1–30 June 2024 (granule start day 2024153) |
| Quantity | Monthly NDVI. Science layer name in the HDF: `CMG 0.05 Deg Monthly NDVI`. The same file also holds EVI. `scale_factor`, `_FillValue`, and `valid_range` are attributes on that layer. This chat did not decode the numeric scale. |
| Resolution | 0.05° CMG, 7200 columns by 3600 rows, about 5.6 km at the equator. Coarse global grid. Not a 30 m world download. The next chat can aggregate it toward a 10–50 km cell. |
| Search URL | https://search.earthdata.nasa.gov/search/granules?p=C2565788914-LPCLOUD |
| Granule URL | https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MOD13C2.061/MOD13C2.A2024153.061.2024198104950/MOD13C2.A2024153.061.2024198104950.hdf |
| Filename | `data/raw/MOD13C2.A2024153.061.2024198104950.hdf` |
| Size | 105,705,498 bytes. HDF4 signature `0e031301`. |
| User guide | https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf |
| Status | **Download succeeded.** |

## Land-surface temperature

| Item | Value |
| --- | --- |
| Dataset | MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG |
| Short name | `MOD11C3` |
| Version | 061 |
| DOI | https://doi.org/10.5067/MODIS/MOD11C3.061 |
| Date range | 1–30 June 2024 (granule start day 2024153) |
| Quantity | Monthly land-surface temperature. Science layers: `LST_Day_CMG` and `LST_Night_CMG`. The file describes them as `LST data * scale_factor`, with quality layers `QC_Day` and `QC_Night`. The numeric scale was not decoded in this chat. Day and night together are the cold-tail and diurnal-range inputs. |
| Resolution | 0.05° CMG, 7200 columns by 3600 rows, about 5.6 km at the equator. Coarse global grid. Not a 30 m world download. |
| Search URL | https://search.earthdata.nasa.gov/search/granules?p=C2565788897-LPCLOUD |
| Granule URL | https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MOD11C3.061/MOD11C3.A2024153.061.2024187024328/MOD11C3.A2024153.061.2024187024328.hdf |
| Filename | `data/raw/MOD11C3.A2024153.061.2024187024328.hdf` |
| Size | 72,523,792 bytes. HDF4 signature `0e031301`. |
| User guide | https://lpdaac.usgs.gov/documents/715/MOD11_User_Guide_V61.pdf |
| Status | **Download succeeded.** |

## Precipitation

| Item | Value |
| --- | --- |
| Dataset | GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree |
| Short name | `GPM_3IMERGM` |
| Version | 07 (file is the current V07B run) |
| DOI | https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07 |
| Date range | 1–30 June 2024 |
| Quantity | Dataset `precipitation`. Long name in the file: “Merged microwave-infrared-gauge precipitation estimate.” Units attribute: `mm/hr`. Grid header: `TimeInterval=MONTH`, `BinMethod=ARITHMETIC_MEAN`, so this is the monthly mean rate, not a monthly millimetre total. Missing code on that field: `-9999.9`. |
| Resolution | 0.1° × 0.1° (`LatitudeResolution=0.1`, `LongitudeResolution=0.1`), about 10 km at the equator. This is the dryness layer. |
| Search URL | https://search.earthdata.nasa.gov/search/granules?p=C2723754851-GES_DISC |
| Granule URL | https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/GPM_3IMERGM.07/2024/3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5 |
| Filename | `data/raw/3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5` |
| Size | 19,149,547 bytes. HDF5 signature `894844460d0a1a0a`. Product version inside the file: V07B. |
| Documentation | https://arthurhou.pps.eosdis.nasa.gov/Documents/IMERG_TechnicalDocumentation_final.pdf |
| Status | **Download succeeded.** |

## Elevation

Global elevation was **not** downloaded. No SRTM tile and no Copernicus DEM was requested.

SRTM GL1, short name `SRTMGL1`, is for shortlisted patches only, in a later chat. SRTM covers roughly 60°N to 56°S. It does not cover Antarctica or the far north. A site outside that band needs a different elevation model. Do not assume worldwide SRTM.

## Not downloaded

- EMIT, CRISM, and any global mineral map. A mineral sentence is optional and only for a finalist patch later.
- HLS Landsat (`HLSL30`) and Sentinel-2 (`HLSS30`). Those are the zoom lens, not this screen.
- An ice or permafrost map. No file was found or logged, so ice stays untested.
- Browse JPEGs. They are pictures, not measurements.
