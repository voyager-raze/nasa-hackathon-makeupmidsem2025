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
| `lst_night_median_k` | 1.47% |
| `lst_night_valid_count` | 0.00% |
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
| `lst_night_median_k` | kelvin | `data/raw/MOD11C3.A2024153.061.2024187024328.hdf` layer `LST_Night_CMG` | stored integer * scale_factor (0.02), as the layer attribute states. Then the median of the finite pixels in the cell. This is the one temperature summary. `LST_Day_CMG` was not reduced into a second column. |
| `lst_night_valid_count` | count of 0.05° pixels | same night LST layer | pixels that are not `_FillValue` (0) and lie inside `valid_range` (7500 to 65535). |
| `precip_median_mm_hr` | mm/hr | `data/raw/3B-MO.MS.MRG.3IMERG.20240601-S000000-E235959.06.V07B.HDF5` dataset `Grid/precipitation` | median of finite pixels. The file unit is mm/hr. `BinMethod=ARITHMETIC_MEAN` and `TimeInterval=MONTH`, so the stored value is already the June mean rate. It was not converted to a monthly millimetre total. This is the dryness measurement, left in the product unit. A lower rate is drier. |
| `precip_valid_count` | count of 0.1° pixels | same precipitation dataset | pixels that are not the fill value (-9999.9). |
| `land_pixel_count` | count of 0.05° pixels | `data/raw/MOD11C3.A2024153.061.2024187024328.hdf` layer `Percent_land_in_grid` | pixels inside `valid_range` 1 to 100. This is the land test, not an analog feature. |
| `slope_median_deg` | degrees | no file | not computed. Entirely blank. |
| `slope_valid_count` | count | no file | not computed. Entirely blank. |

Of the land cells south of 60°S, 157497 of 157497 have a blank NDVI. That June gap, not a dropped column, is why `ndvi_median` is blank on a large share of the table.

When a valid count is even, the median is the arithmetic mean of the two central values (NumPy `nanmedian`). The same rule is used for every cell of a column.

`land_pixel_count` is a coverage count. It is not vegetation, temperature, dryness, or slope, and it is not a score.

## What this table is not

No column is a weight, a rank, or a site choice. Slope was not filled from the locked lunar band. Missing vegetation, night temperature, or precipitation was not copied from a neighboring cell.
