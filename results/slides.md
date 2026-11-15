## Slide 1 — Mission Analog Readiness

### Partial Match: a transparent shortlist for rover mobility rehearsals

Team Mid-Sem Make Up · Delhi · NASA Space Apps 2026

Challenge: Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.

## Slide 2 — The decision

Which Earth patch can rehearse which mission task?

A look-alike image is not evidence. We screened Earth data, checked terrain against a named lunar target, and separated what the measurements can and cannot support.

Use the result to plan a field study—not to claim a flight-ready analog.

## Slide 3 — Two targets, two evidence levels

**Moon:** Shackleton–de Gerlache connecting ridge, 89.4632°S, 137.4771°W. LOLA reports a 16 km tile slope IQR of **8.0–16.7°** (median **12.3°**).

**Mars:** terraced crater Badger, Arcadia Planitia, 46.581°N, 194.85°E. Bramson et al. (2015) interpret radar evidence as a decameters-thick, mostly excess-water-ice layer at a flat terrace 43 m deep. This is published target evidence, not a local ice map processed by our project.

The Earth-side ice comparison is still missing.

## Slide 4 — A screen, then a direct check

We screened 0.2° Earth cells with June 2024 MODIS NDVI, MODIS night land-surface temperature, and GPM monthly precipitation.

Equal-weight, normalized distance uses three **Earth-side proxies**: NDVI near zero, precipitation near zero, and night temperature above a 214.3 K cold-tail threshold. A lower score means closer to these proxies—not closer to the Moon or Mars overall.

Global slope was missing, so slope is **not in the score**. We later measured the two site slopes from Copernicus DEM and compared them directly with the LOLA band. Missing data stayed missing.

## Slide 5 — The result changes the recommendation

Site A: Kunlun Mountains, 35.3°N, 81.1°E. Site B: Vinchina, 27.9°S, 68.9°W—the best cell inside the Atacama-region hold-out, used as a comparator.

| Measurement | Kunlun (Site A) | Vinchina (Site B) |
| --- | --- | --- |
| Three-proxy score (lower is closer) | 0.186845 | **0.167981** |
| Median slope vs Moon IQR 8.0–16.7° | 7.08° — outside | **9.48° — inside** |

The proxy score and the independent slope check both favor Vinchina among these two. Study it first for a terrain-only mobility rehearsal; keep Kunlun as a lower-slope comparison. Positive-NDVI neighbors in Western Kunlun (`36.1_78.3`, 0.195322; `35.7_77.3`, 0.204707) and zero-rain hold-out cells in Sur Lípez, Bolivia (`-22.5_-67.7`, 0.211229; `-20.5_-67.5`, 0.227362) are also pinned on the map for comparison. Neither is a validated analog.

## Slide 6 — A testable next step

**Question:** how does rover mobility effort compare across these two candidate patches?

After route-scale terrain and access checks, run matched-length traverses with the same rover setup, payload, and speed. Record local slope and surface material; measure wheel energy per distance, slip, and interruptions over repeated runs. Site differences would not isolate slope as the cause.

NASA context, not a site forecast: Curiosity completed 622/738 attempted drives (84.3%; 95% Wilson interval 81.5–86.7%). The proposed site trial measures terrain-linked effort, not mission success.

This is a test plan, not a completed field trial. Access, safety, and logistics have not been assessed. Earth cannot reproduce lunar/Martian gravity, vacuum or thin air, radiation, or a permanently shadowed lunar thermal environment.

## Slide 7 — What is still unknown

Low confidence: the climate screen is one month; none of its three proxies has a direct planetary referent; no Earth ice/permafrost layer was used; and the 0.2° cells are too coarse for a route, boulder, or drill site. No Mars Earth analog is claimed.

Open the [90-second review guide](../web/index.html) on first dashboard visit. The [full dossier](RESULTS.html), [method](score-notes.html), [data log](../notes/data-log.html), and [validation](../notes/credibility.html) carry the evidence and caveats.

**Sources:** [MODIS NDVI](https://doi.org/10.5067/MODIS/MOD13C2.061) · [MODIS LST](https://doi.org/10.5067/MODIS/MOD11C3.061) · [GPM IMERG](https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07) · [LOLA slope](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slp.tif) · [Bramson et al. (2015)](https://doi.org/10.1002/2015GL064844) · [NASA Curiosity drive report](https://ntrs.nasa.gov/citations/20220000780)

Repository: [voyager-raze/nasa-hackathon-makeupmidsem2025](https://github.com/voyager-raze/nasa-hackathon-makeupmidsem2025)
