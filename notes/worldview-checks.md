# Worldview checks

The score is a partial match on measured features, not a probability of mission success.

Every look used NASA Worldview, https://worldview.earthdata.nasa.gov/. The layer on every look was **Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD**, with the Coastlines and Place Labels reference overlays on. A high score was rejected when the cell was ocean, a city, an ice-sheet interior with no workable ground, or an obvious data error.

`results/top5.csv` was not edited. The weights were not edited. The extra cells below were read from the same feature table with the same weighted distance in `src/score.py`, only to see what remained after the five discovery cells failed this check.

## Discovery cells

All five centers sit in one patch of the Greenland ice sheet. Two frames covered all five.

| Look | Date | Frame |
| --- | --- | --- |
| Feature month | 2024-06-15 | [lon −43.2 to −37.6, lat 72.6 to 75.0](https://worldview.earthdata.nasa.gov/?v=-43.2,72.6,-37.6,75.0&l=Reference_Labels_15m,Coastlines_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=true&t=2024-06-15-T00:00:00Z) |
| Confirmation | 2024-08-15 | [lon −42.2 to −38.2, lat 72.3 to 75.3](https://worldview.earthdata.nasa.gov/?v=-42.2,72.28529411764707,-38.2,75.31470588235295&l=Coastlines_15m,Reference_Labels_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=false&t=2024-08-15-T00:00:00Z) |
| Ice-sheet context | 2024-08-15 | [lon −65 to −15, lat 60 to 83](https://worldview.earthdata.nasa.gov/?v=-65,60,-15,83&l=Reference_Labels_15m,Coastlines_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=true&t=2024-08-15-T00:00:00Z) |

On 15 June 2024 the five centers were inside a continuous white surface. The place label in that frame read LAND. The coastline overlay drew no line inside the frame. The scale bar read 50 km. On 15 August 2024 the same centers were still white, and the wider frame showed the ice-sheet outline with the label GREENLAND, dark coastal water, and Iceland outside the ice. That is an ice-sheet interior with no workable ground.

| id | latitude | longitude | layer | date | decision | reason |
| --- | --- | --- | --- | --- | --- | --- |
| `73.5_-40.5` | 73.5 | −40.5 | Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD | 2024-06-15, confirmed 2024-08-15 | rejected | ice-sheet interior |
| `73.5_-40.7` | 73.5 | −40.7 | Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD | 2024-06-15, confirmed 2024-08-15 | rejected | ice-sheet interior |
| `73.9_-40.1` | 73.9 | −40.1 | Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD | 2024-06-15, confirmed 2024-08-15 | rejected | ice-sheet interior |
| `73.5_-40.9` | 73.5 | −40.9 | Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD | 2024-06-15, confirmed 2024-08-15 | rejected | ice-sheet interior |
| `74.1_-39.9` | 74.1 | −39.9 | Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD | 2024-06-15, confirmed 2024-08-15 | rejected | ice-sheet interior |

## Cells that outscored the Kunlun cell

The Kunlun cell at 35.3°N, 81.1°E scores 0.186845. 1485 eligible discovery cells score better than that. Their centers run from 70.5°N to 78.9°N and from 50.1°W to 28.9°W. The four edge cells of that set were opened on 15 August 2024 in the same true-color layer. Each frame was white ice, without a city or open ocean at the cell. A coastline appeared only at the corner of the southern frame, outside the cell.

| id | latitude | longitude | date | frame | decision | reason |
| --- | --- | --- | --- | --- | --- | --- |
| `75.9_-28.9` | 75.9 | −28.9 | 2024-08-15 | [east edge](https://worldview.earthdata.nasa.gov/?v=-32.5,73.24926470588235,-25.5,78.55073529411766&l=Coastlines_15m,Reference_Labels_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=false&t=2024-08-15-T00:00:00Z) | rejected | ice-sheet interior |
| `74.3_-50.1` | 74.3 | −50.1 | 2024-08-15 | [west edge](https://worldview.earthdata.nasa.gov/?v=-53.2,71.95220588235294,-47,76.64779411764705&l=Coastlines_15m,Reference_Labels_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=false&t=2024-08-15-T00:00:00Z) | rejected | ice-sheet interior |
| `70.5_-47.1` | 70.5 | −47.1 | 2024-08-15 | [south edge](https://worldview.earthdata.nasa.gov/?v=-50.2,68.25220588235294,-44,72.94779411764705&l=Coastlines_15m,Reference_Labels_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=false&t=2024-08-15-T00:00:00Z) | rejected | ice-sheet interior |
| `78.9_-42.3` | 78.9 | −42.3 | 2024-08-15 | [north edge](https://worldview.earthdata.nasa.gov/?v=-45.8,76.24926470588235,-38.8,81.55073529411766&l=Coastlines_15m,Reference_Labels_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=false&t=2024-08-15-T00:00:00Z) | rejected | ice-sheet interior |

Those four looks, plus the wide 15 August frame, are the basis for treating that whole score cluster as ice-sheet interior. The remaining 1,481 centers sit inside the same bounding box and were not given separate frames.

## Site A

Kept. Best eligible discovery cell outside that ice-sheet cluster. A non-specialist has heard of it less often than the Atacama. Its score, 0.186845, is a worse partial match than the control cell, 0.167981. That comparison is left as it is.

| id | latitude | longitude | layer | date | decision | reason |
| --- | --- | --- | --- | --- | --- | --- |
| `35.3_81.1` | 35.3 | 81.1 | Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD | 2024-06-15 | kept | bare ground, snow on the ridges, and lakes |

Frame: [lon 79.6 to 82.6, lat 34.2 to 36.4](https://worldview.earthdata.nasa.gov/?v=79.6,34.163970588235294,82.6,36.4360294117647&l=Reference_Labels_15m,Coastlines_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=true&t=2024-06-15-T00:00:00Z). The place label in that frame was Gozha Co, a lake south of the cell.

A second look on 2024-09-20, [same region](https://worldview.earthdata.nasa.gov/?v=79.79999999999998,34.315441176470586,82.4,36.28455882352941&l=Reference_Labels_15m,Coastlines_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=true&t=2024-09-20-T00:00:00Z), was clearer. The place label read Kunlun Mountains, with Gozha Co still to the south. Brown plateau and ridgeline snow were both visible. Kept for the same reason.

The coordinate was already fixed at the cell center. The OpenStreetMap label for that point is Rutog County, Ngari Prefecture, Tibet Autonomous Region, China: [Nominatim reverse geocode](https://nominatim.openstreetmap.org/reverse?lat=35.3&lon=81.1&format=jsonv2&zoom=10). The site name used here is the Worldview label, Kunlun Mountains.

## Site B

Kept. This is the control cell already scored in `results/control.csv` and `results/score-notes.md`, cell `-27.9_-68.9`, inside the Atacama hold-out box. The coordinate is that cell center.

| id | latitude | longitude | layer | date | decision | reason |
| --- | --- | --- | --- | --- | --- | --- |
| `-27.9_-68.9` | −27.9 | −68.9 | Corrected Reflectance (True Color), Terra / MODIS, v6.1 STD | 2024-06-15 | kept | arid mountains inside the hold-out box |

Frame: [lon −71.0 to −66.6, lat −29.6 to −26.2](https://worldview.earthdata.nasa.gov/?v=-71.04466019417475,-29.6,-66.55533980582524,-26.199999999999996&l=Reference_Labels_15m,Coastlines_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=true&t=2024-06-15-T00:00:00Z). June is winter here, so snow sat on the high ridges. The place label visible to the east of the cell was CATAMARCA. The ground in the frame was ridgeline and snow.

A closer look on 2024-11-15, [lon −69.6 to −68.2, lat −28.4 to −27.4](https://worldview.earthdata.nasa.gov/?v=-69.56019417475729,-28.4,-68.23980582524273,-27.4&l=Reference_Labels_15m,Coastlines_15m,MODIS_Terra_CorrectedReflectance_TrueColor&lg=true&t=2024-11-15-T00:00:00Z), showed bare brown mountains and small snow patches. Kept.

The OpenStreetMap label for the fixed coordinate is Departamento Vinchina, La Rioja, Argentina, on the Andean front inside the hold-out box: [Nominatim reverse geocode](https://nominatim.openstreetmap.org/reverse?lat=-27.9&lon=-68.9&format=jsonv2&zoom=10). The famous control remains the Atacama box scored in session 04. The winning cell of that box is this Argentine pin, not the Chilean Salar de Atacama.
