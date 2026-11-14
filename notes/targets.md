# Locked targets

This file is the contract for later chats. Do not change the locked Moon name, the locked Mars name, or the locked slope band below.

A similarity score, when a later chat computes one, is a partial match on measured features. It is not a probability of mission success. Gravity, vacuum or thin air, and radiation are out of scope for any outdoor Earth analog. This chat did not score Earth.

## Moon

**Name:** Shackleton–de Gerlache connecting ridge

**Center:** 89.4632°S, 137.4771°W (222.5229°E)

This is the center of the LOLA Site01 slope tile, not an average of the lunar south pole and not a crater floor. Site01 is the connecting ridge between Shackleton and de Gerlache: sunlit, sloped ground between two craters, next to colder shadowed floors. The useful Artemis ground is that ridge, not the floor of either crater.

The same feature is named on the LROC NAC DTM product SHACKRDGE02, “Shackleton - de Gerlache Connecting Ridge,” center latitude −89.5, center longitude 224.81, bounds −89.63 to −89.37 and 209.81°E to 239.10°E:

https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_SHACKRDGE02

Moon Trek was opened on the South Pole map (south polar projection, LRO WAC mosaic). At a 200 km scale bar the view is the south polar crater field, with the pole near the middle of the disk. Shackleton is not resolved as a separate rim at that scale.

https://trek.nasa.gov/moon/

### Slope (locked)

**Locked band: 8.0–16.7 degrees. Median: 12.3 degrees.**

Later chats must not replace this band. It is the Earth slope band.

| Item | Value |
| --- | --- |
| Quantity | Slope, interquartile range of every finite pixel in the tile |
| Number | 8.0–16.7 degrees (25th–75th percentile). Median 12.3 degrees. |
| Unit | degrees |
| Layer | `Site01_final_adj_5mpp_slp.tif` |
| What the layer is | LOLA 5 m/pixel slope map, Site01, Connecting ridge. Pixel values are slope in degrees. South polar stereographic, sphere radius 1,737,400 m, MOON_ME / DE421. The tile is 3200 × 3200 pixels, 16 km on a side. |
| URL | https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slp.tif |
| Catalog | https://pgda.gsfc.nasa.gov/products/78 and https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/ |

Read from that GeoTIFF on 14 November 2026, then deleted from the temp folder. It was not committed. Rounded from 8.007, 12.290, and 16.722 degrees. The full pixel range in the tile is 0.0 to 64.6 degrees. About 36 percent of pixels are under 10 degrees, and about 12 percent are over 20 degrees, so the tile includes ridge-crest ground and steeper flanks. The locked band is the interquartile range of the whole tile.

A published high-illumination point on this ridge, Connecting Ridge C2 at 89.3157°S, 114.06°W, falls on the western edge of the same raster (column 10). A 500 m window there is clipped by that edge. Its median is about 5.8 degrees. That window is not the locked band.

### Temperature

Diviner fact, read from Williams et al., Lunar Surface Science Workshop 2020, abstract 5105:

https://www.hou.usra.edu/meetings/lunarsurface2020/pdf/5105.pdf

Those maps are Diviner bolometric temperatures (seven infrared channels, about ten years of nadir observations, 240 m/pixel polar stereographic grids). The archive index for the Diviner products, including the Polar Cumulative Products (5 July 2009–15 March 2020), is:

https://pds-geosciences.wustl.edu/missions/lro/diviner.htm

On Connecting Ridge C2 (89.3157°S, 114.06°W), summer temperatures are systematically high, about 200 K, with a shadowing dip near 20–22 hours local time. Winter at that ridge point alternates between illumination and shadow. The same abstract says surfaces cold enough to trap water, below about 110 K, become much more extensive in winter, and it gives the floor of Faustini as a permanently shadowed example whose temperature still swings by tens of kelvin.

The illuminated ridge is far warmer than a permanently shadowed floor. A permanently shadowed lunar floor can be colder than any outdoor place on Earth. No Earth site is a thermal analog for that floor. A nearby Earth ice body can still be an operations analog for “go sample the ice,” which is a different claim.

No Diviner raster was downloaded. The about 200 K figure is for Connecting Ridge C2, not a new measurement at the Site01 tile center.

## Mars

**Case:** ground ice.

**Why this case:** the Moon target is a cold south-polar ridge beside shadowed ground where ice can persist. The Earth story assumed for the pair is cold and barren. It is not wind and sediment. Earth was not scored in this chat, so this is an assumption from the Moon target, not from an Earth screen.

**Region:** Arcadia Planitia, the terraced crater Badger.

**Coordinates:** 46.581°N, 194.85°E

Bramson et al. (2015) mapped 187 terraced craters in Arcadia Planitia with 281 CTX images inside 180–225°E and 38–50°N, and checked SHARAD radargrams against clutter simulations built from MOLA. Badger is one of those craters, at 46.581°N, 194.85°E, with a flat terrace at 43 m depth. They infer a decameters-thick layer that is mostly excess water ice.

https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/2015GL064844

https://arxiv.org/pdf/1509.03210

### View opened in Mars Trek

https://trek.nasa.gov/mars/#v=0.1&x=194.85&y=46.58&z=6&p=urn%3Aogc%3Adef%3Acrs%3AEPSG%3A%3A104905&b=mars&e=190%2C42%2C200%2C51

On screen: the default basemap, **Viking VIS, Global Color Mosaic**, framed on about 190–200°E and 42–51°N. The scale bar read 160 km. The ground in view was cratered northern plains. That frame covers Badger and the CTX study box in Bramson et al.

**CTX HiRISE auto layer** is listed in Mars Trek and was not the image on screen at that scale. **MGS MOLA, Global Color Hillshade** and **MGS MOLA, Global DEM** are in the Trek layer list and were not the image on screen. The MOLA use cited above is the clutter simulation in Bramson et al., not a MOLA hillshade read in this chat.

### Left blank

| Item | Value |
| --- | --- |
| Minerals | no data |
| Ice map (a raster or index opened for this point) | no data |
| Dust index | no data |

## Out of scope

Gravity, vacuum, thin carbon-dioxide air, and radiation are out of scope for any outdoor Earth analog. Later chats must not claim an Earth site matches them.
