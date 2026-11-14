# Data log

Coarse Earth layers for Partial Match. The June feature build now includes MODIS daytime land-surface temperature and paired day-minus-night range as descriptive columns. Neither enters the published score, and the published scores and site choices are unchanged.

The locked Mars case stays **ground ice**, Arcadia Planitia, the terraced crater Badger. No second Mars search was opened. No Mars ice raster was opened. The June MOD10CM snow granule and the SWIM planetary applicability are documented below; no ice value was added.

The three June 2024 granules were obtained through an authorized NASA GESDISC DATA ARCHIVE session on 14 November 2026. No credential is recorded in this repository.

June 2024 is one month, not a climate normal. June is summer in the north and winter in the south. A later chat that needs a year should download the other months of the same short name and add them here. It must not treat this June granule as an annual value.

The July 2024 MOD13C2 attempt returned HTTP 401 at the protected Earthdata granule URL below. Per the data plan, the 2024 month-by-month run stopped there; no later month was requested and June remains a single-month measurement.

https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MOD13C2.061/MOD13C2.A2024183.061.2024228034735/MOD13C2.A2024183.061.2024228034735.hdf

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
| Quantity | Monthly NDVI. Science layer name in the HDF: `CMG 0.05 Deg Monthly NDVI`. The same file also holds EVI. Values are decoded using the layer's scale factor (10000), `_FillValue`, and `valid_range`. |
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
| Quantity | Monthly land-surface temperature. Science layers: `LST_Day_CMG` and `LST_Night_CMG`. Both decode as stored integer × `scale_factor` (0.02), with `_FillValue` and layer `valid_range` applied. `LST_Night_CMG` remains the only temperature score input. `LST_Day_CMG` is descriptive. The per-cell day–night range is the median of paired valid pixel differences (`day - night`), also descriptive and not scored. Quality layers `QC_Day` and `QC_Night` are present but were not used as additional filters. |
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

Global elevation was **not** downloaded. No global SRTM tile and no global Copernicus DEM was requested. The two shortlisted patch elevation and slope measurements come from a separate Copernicus DEM GLO-30 source documented in `results/sources.csv`.

On 15 November 2026, a coarse NOAA ETOPO2v2g 2-arc-minute grid was attempted instead of a global 30 m DEM. The archive endpoint returned HTTP 200 to a header request, but the full download timed out after 300 seconds (`curl` exit 28) at 51,751,487 of 83,092,100 bytes. The incomplete archive was removed. No slope was calculated, no slope values were written, and `slope_median_deg` remains blank on the global grid. This dataset attempt is stopped.

Download URL: https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2/ETOPO2v2-2006/ETOPO2v2g/raw_binary/ETOPO2v2g_i2_LSB.zip

## Snow, aerosol, and Mars ice

The June 2024 MOD10CM monthly snow-cover granule is listed in CMR, but its data URL returned HTTP 401 on download. No file was opened and no snow value was added.

- CMR collection: https://cmr.earthdata.nasa.gov/search/collections.json?short_name=MOD10CM
- Granule and failed download URL: https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/MODIS/MOD10CM/61/2024/06/01/MOD10CM.A2024153.061.2024187024104.hdf
- Dataset DOI: https://doi.org/10.5067/MODIS/MOD10CM.061
Status: **HTTP 401; stopped.**

The June 2024 MOD08_M3 aerosol granule is listed in CMR. Its HTTP header request redirected successfully, but the data download returned HTTP 401. No file was opened and no aerosol value was added.

- CMR granule search: https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MOD08_M3&version=6.1&temporal=2024-06-01T00%3A00%3A01Z%2C2024-07-01T00%3A00%3A00Z&page_size=1
- Granule and failed download URL: https://data.laadsdaac.earthdatacloud.nasa.gov/prod-lads/MOD08_M3/MOD08_M3.A2024153.061.2024187025131.hdf
- Dataset DOI: https://doi.org/10.5067/MODIS/MOD08_M3.061
Status: **HTTP 401; stopped.**

The USGS SWIM project is a lunar south-pole water-ice mapping product. It is not a Mars dataset and cannot supply an ice-consistency value for the Mars coordinates of Badger. The project page was not readable from this session because it returned an AWS WAF challenge; no SWIM file or value was opened. Badger's minerals, ice-map raster, and dust index remain blank.

SRTM GL1, short name `SRTMGL1`, is for shortlisted patches only, in a later chat. SRTM covers roughly 60°N to 56°S. It does not cover Antarctica or the far north. A site outside that band needs a different elevation model. Do not assume worldwide SRTM.

## Not downloaded

- EMIT, CRISM, and any global mineral map. A mineral sentence is optional and only for a finalist patch later.
- HLS Landsat (`HLSL30`) and Sentinel-2 (`HLSS30`). Those are the zoom lens, not this screen.
- MOD10CM snow cover was attempted, but the granule returned HTTP 401; no snow value was read. No static permafrost extent was opened. No SWIM raster was opened, and a lunar product is not a Mars ice measurement.
- Browse JPEGs. They are pictures, not measurements.
