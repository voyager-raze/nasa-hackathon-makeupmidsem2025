# Feature grid

One row in `data/processed/features.csv` is one land cell. This file defines every column. It does not weight cells and it does not rank them.

June 2024 is one month. It is summer in the north and winter in the south. These columns are not a climate normal.

## Grid

| Item | Value |
| --- | --- |
| Cell size | 0.2° by 0.2° |
| North–south length | 22.3 km (0.2 × 111.32 km per degree) |
| East–west length | 22.3 km × cos(latitude). About 22.3 km at the equator and about 11.1 km at 60° latitude |
| MODIS pixels per cell | 4 × 4 pixels of the 0.05° CMG |
| IMERG pixels per cell | 2 × 2 pixels of the 0.1° grid |
| Land cells | 577134 |

The cell is an integer multiple of both logged grids, so no pixel is split and no gap is interpolated.

## Land rule

A cell is written only when at least one of its 16 MODIS `Percent_land_in_grid` pixels falls in that layer’s valid range (1 to 100). The fill value on that layer is 0, so open ocean is left out of the table. A coastal cell with any valid land pixel is kept. Ocean pixels inside that cell stay out of the vegetation and temperature medians because those layers are fill over water.

## Null rule

A blank measurement means the layer did not cover that cell: the valid-pixel count is 0. A blank is not a zero, not a neighbor’s value, and not an interpolated fill.

`slope_median_deg` and `slope_valid_count` are blank on every row. `notes/data-log.md` records that global elevation was not downloaded. This script does not estimate slope.

## Summary

Land cells: 577134

Percent null (blank values among land cells):

| Column | Percent null |
| --- | --- |
| `lat_center_deg` | 0.00% |
| `lon_center_deg` | 0.00% |
| `ndvi_median` | 29.11% |
| `ndvi_valid_count` | 0.00% |
| `lst_day_median_k` | 1.06% |
| `lst_day_valid_count` | 0.00% |
| `lst_night_median_k` | 1.47% |
| `lst_night_valid_count` | 0.00% |
| `lst_day_night_range_median_k` | 1.59% |
| `lst_day_night_range_valid_count` | 0.00% |
| `precip_median_mm_hr` | 1.03% |
| `precip_valid_count` | 0.00% |
| `land_pixel_count` | 0.00% |
| `slope_median_deg` | 100.00% |
| `slope_valid_count` | 100.00% |

## Columns

| Column | Unit | Source file | Method |
| --- | --- | --- | --- |
| `lat_center_deg` | degrees north | cell geometry of the logged CMG | center of the 0.2° cell. Row 0 of each MODIS grid is the north edge. |
| `lon_center_deg` | degrees east | cell geometry of the logged CMG | center of the 0.2° cell. Column 0 is the dateline at 180°W, increasing east. |
| `ndvi_median` | NDVI (native index) | `data/raw/MOD13C2.A2024153.061.2024198104950.hdf` layer `CMG 0.05 Deg Monthly NDVI` | stored integer / scale_factor (10000). Then the median of the finite pixels in the cell. |
| `ndvi_valid_count` | count of 0.05° pixels | same NDVI layer | pixels that are not `_FillValue` (−3000) and lie inside `valid_range` (−2000 to 10000). |
| `lst_day_median_k` | kelvin | `data/raw/MOD11C3.A2024153.061.2024187024328.hdf` layer `LST_Day_CMG` | stored integer * scale_factor (0.02), as the layer attribute states. Then the median of valid pixels in the cell. |
| `lst_day_valid_count` | count of 0.05° pixels | same day LST layer | pixels that are not `_FillValue` and lie inside that layer’s `valid_range`. |
| `lst_night_median_k` | kelvin | `data/raw/MOD11C3.A2024153.061.2024187024328.hdf` layer `LST_Night_CMG` | stored integer * scale_factor (0.02), as the layer attribute states. Then the median of valid pixels in the cell. This remains the only temperature feature in the score. |
| `lst_night_valid_count` | count of 0.05° pixels | same night LST layer | pixels that are not `_FillValue` and lie inside that layer’s `valid_range`. |
| `lst_day_night_range_median_k` | kelvin | same file, layers `LST_Day_CMG` and `LST_Night_CMG` | Median of paired valid-pixel differences `day - night` within the cell. This is a descriptive measure, not a score term. |
| `lst_day_night_range_valid_count` | count of paired 0.05° pixels | same day and night LST layers | Pixels valid in both layers; a missing day or night value stays missing. |
| `precip_median_mm_hr` | mm/hr | `data/raw/3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5` dataset `Grid/precipitation` | median of finite pixels. The file unit is mm/hr. `BinMethod=ARITHMETIC_MEAN` and `TimeInterval=MONTH`, so the stored value is already the June mean rate. It was not converted to a monthly millimetre total. This is the dryness measurement, left in the product unit. A lower rate is drier. |
| `precip_valid_count` | count of 0.1° pixels | same precipitation dataset | pixels that are not the fill value (-9999.9). |
| `land_pixel_count` | count of 0.05° pixels | `data/raw/MOD11C3.A2024153.061.2024187024328.hdf` layer `Percent_land_in_grid` | pixels inside `valid_range` 1 to 100. This is the land test, not an analog feature. |
| `slope_median_deg` | degrees | no file | not computed. Entirely blank. |
| `slope_valid_count` | count | no file | not computed. Entirely blank. |

Of the land cells south of 60°S, 157497 of 157497 have a blank NDVI. That June gap, not a dropped column, is why `ndvi_median` is blank on a large share of the table.

When a valid count is even, the median is the arithmetic mean of the two central values (NumPy `nanmedian`). The same rule is used for every cell of a column.

`land_pixel_count` is a coverage count. It is not vegetation, temperature, dryness, or slope, and it is not a score. The day and day–night columns are descriptive; they have no target referent or weight in this run.

## Score interpretation and feature rules

The score is a heuristic screening index on measured Earth features. No direct Moon or Mars referent is present for NDVI, precipitation, or night land-surface temperature; the current comparison targets are explicit proxies, not planetary measurements. Lower scores mean closer only under these rules and the June 2024 inputs.

| Feature | Physical quantity and unit | Earth source and handling | Planetary referent | Distance, scale, missing rule, and weight rationale |
| --- | --- | --- | --- | --- |
| `ndvi_median` | Dimensionless NDVI | MOD13C2.061, June 2024, 0.05° CMG aggregated to 0.2° cells; stored integer divided by 10000 after `_FillValue` and `valid_range` handling. | No referent. Zero is a barren-surface proxy, not a measured lunar or Martian NDVI. | Absolute departure from 0; normalized by the 95th percentile of measured June distances. Missing cells are ineligible. Default weight 1 is an unvalidated equal-weight choice. |
| `precip_median_mm_hr` | Monthly mean precipitation rate, mm/hr | GPM IMERG Final V07B, June 2024, 0.1° cells aggregated to 0.2°; `_FillValue` removed; `TimeInterval=MONTH` and `BinMethod=ARITHMETIC_MEAN` retained as a rate. | No referent. Zero is the dry end proxy, not a lunar or Martian measurement. | Positive rate above 0; normalized by the 95th percentile of measured June distances. Missing cells are ineligible. Default weight 1 is an unvalidated equal-weight choice. |
| `lst_night_median_k` | Night land-surface temperature, kelvin | MOD11C3.061, June 2024, 0.05° CMG aggregated to 0.2°; stored value multiplied by 0.02 after fill/range handling. QC layers were not additional filters. | No directly comparable Diviner or Mars referent in the source table. The 10th percentile of measured Earth June values (214.3 K) is an Earth-derived heuristic, not a planetary temperature. | Kelvin above 214.3 K, floored at zero; normalized by the 95th percentile of measured distances. Missing cells are ineligible. Default weight 1 is an unvalidated equal-weight choice. |
| `slope_median_deg` | Terrain slope, degrees | No global Earth raster was successfully opened; blank for all global cells. Later Copernicus GLO-30 patch values are limited to the two named sites and not part of the baseline. | Moon: locked LOLA Site01 band 8.0–16.7°; Mars: no referent. | Distance is zero inside the lunar band and degrees to its nearest edge outside; no global scale exists, so feature is inactive. Missing global values are not ranked. Weight 1 is configured but has no effect while all-null. |
| `lst_day_median_k`, `lst_day_night_range_median_k` | Day surface temperature and paired day-minus-night range, kelvin | MOD11C3.061, June 2024; same scale and fill handling; range uses pixels valid in both layers before cell median. | No referent. | Descriptive only, not scored. Missing values remain blank. |

Gravity, vacuum/thin air, and radiation are physical limits, not measured features. June 2024 is one month and is not a climate normal.

## What this table is not

No column is a weight, a rank, or a site choice. Slope was not filled from the locked lunar band. Missing vegetation, night temperature, or precipitation was not copied from a neighboring cell.
