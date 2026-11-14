# Factor coverage

One row per trait in [docs/03-moon-mars-and-earth-limits.md](../docs/03-moon-mars-and-earth-limits.md). Status is only `measured in the score`, `measured after the score`, `no data`, or `limit`. Gravity, atmosphere, and radiation stay limits. They are not score terms. Snow in a Worldview class is not an ice measurement.

| Trait | What the score does today | Status |
| --- | --- | --- |
| Slope | The published scores leave `slope_median_deg` out because that column is null on the global grid. The locked Moon band is 8.0–16.7 degrees. Kunlun 7.08 degrees and Vinchina 9.48 degrees were measured later, on the two patches only. | measured after the score |
| Vegetation | June 2024 `ndvi_median` enters the weighted mean as the absolute departure from 0. Kunlun is −0.01995 NDVI. Vinchina is 0.00925 NDVI. No Moon or Mars vegetation value is in the source table. | measured in the score |
| Dryness | June 2024 `precip_median_mm_hr` enters the weighted mean as the rate above 0. Kunlun is 0.006 mm/hr. Vinchina is 0.008 mm/hr. | measured in the score |
| Night temperature | June 2024 `lst_night_median_k` enters the weighted mean as kelvin above 214.3, and 0 at or below that cold tail. Kunlun is 258.8 kelvin. Vinchina is 254.45 kelvin. | measured in the score |
| Day temperature | June 2024 `lst_day_median_k` was decoded from the same MOD11C3 file. Kunlun is 269.12 kelvin and Vinchina is 264.58 kelvin. There is no Moon or Mars referent in the source table; it is not scored. | measured after the score |
| Day–night range | `lst_day_night_range_median_k` is the median of paired valid June day-minus-night pixels. Kunlun is 11.05 kelvin and Vinchina is 10.44 kelvin. There is no Moon or Mars referent in the source table; it is not scored. | measured after the score |
| Ice or permafrost | No ice or permafrost map is in the score or in `results/sources.csv`. The Greenland ice-sheet classes were rejected. Ridgeline snow and small snow patches are Worldview surface classes. | no data |
| Dust | No dust or aerosol value is in the score. The dust index for Badger is blank in `notes/targets.md`. | no data |
| Elevation | Median elevation is 6120.8 m at Kunlun and 5330.7 m at Vinchina, from the same Copernicus patches as the later slopes. Elevation is not a term in the weighted mean, and the global grid has no elevation column. | measured after the score |
| Gravity | About one-sixth of Earth on the Moon and about three-eighths of Earth on Mars. Both Earth patches are full outdoor gravity. The score does not include a gravity term. | limit |
| Atmosphere | The Moon is a vacuum. Mars has thin carbon-dioxide air, roughly one percent of Earth’s surface pressure. Both patches have Earth’s air. The score does not include an atmosphere term. | limit |
| Radiation | Air and the magnetic field block most of the surface dose at these patches. The score does not include a radiation term. Outdoor tests here do not qualify electronics or crews for the Moon or Mars surface dose. | limit |
