# Master plan: tonight through submission

**Deadline:** Sunday, 15 November 2026, 11:59 pm Delhi time.  
**Stop editing the form by 10:30 pm** so a broken link can still be fixed.  
**Team:** Mid-Sem Make Up, Delhi local event.  
**Project name:** Mission Analog Readiness. **Partial Match** names the screening method, not a claim that sites are mission-ready.

> **Current result:** This plan records the build workflow; the screening and seven-slide deck are complete. The published score uses three June 2024 Earth proxies. Slope was checked later on the two shortlisted patches and is not in the score. Vinchina is the in-band terrain candidate; Kunlun is the lower-slope comparison. The proposed field trial has not been run, and no Earth ice/permafrost analog is claimed.

This plan assumes the notes in [03-moon-mars-and-earth-limits.md](03-moon-mars-and-earth-limits.md) and the data order in [04-data-resources.md](04-data-resources.md). Do not reopen the concept unless the first data pass makes the default pair impossible.

## The project in one paragraph

Partial Match screens June 2024 NDVI, precipitation, and night land-surface temperature across coarse Earth cells, then compares a global-screen discovery candidate with the best eligible cell in a defined Atacama-region hold-out. The Moon target is the Shackleton–de Gerlache connecting ridge; the Mars target is Badger in Arcadia Planitia, with published radar evidence for ground ice. A separate Copernicus-to-LOLA slope check puts Vinchina inside the lunar slope band and Kunlun below it. The score is a proxy index, not a direct cross-world similarity measure or probability of mission success. The result supports a proposed, not-yet-run paired rover-mobility study; it does not identify an Earth ice analog.

## What “done” means

A judge can open three links and understand the result without a call.

1. A public repository with the screen, the source table, the two site dossiers, and the limits.
2. A simple map, or a static map page, with the Earth sites and the Moon and Mars targets labeled.
3. A seven-slide deck, link open to anyone.
4. The Space Apps project form submitted, in English, with the NASA data field filled from the Resources tab.

Anything beyond that is extra. A 30-second video is optional and only if the slides are already uploaded.

## Saturday night: lock the targets

Time box: about 2 hours. Sleep beats a third dataset.

1. Create or confirm an Earthdata login and a public-ready GitHub repo.
2. Open [Moon Trek](https://trek.nasa.gov/moon) or the [PDS LRO page](https://pds-geosciences.wustl.edu/missions/lro/). Choose **one** south-pole area from the public Artemis candidate list: Shackleton rim, the Shackleton–de Gerlache connecting ridge, Haworth, Shoemaker, Faustini, de Gerlache, or Nobile. Write the name, a center latitude and longitude, and why it is a base-relevant ridge rather than a crater floor.
3. Read one slope range for that patch from LOLA or a Trek elevation layer. Write the number, the unit, and the layer name. This number sets the Earth slope band. Do not copy a slope from memory.
4. Open the [PDS Diviner page](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) and note one temperature fact for that region, even if it is only “the illuminated rim is far warmer than the shadowed floor.” That fact is the slide where the Earth analog breaks.
5. Open [Mars Trek](https://trek.nasa.gov/mars). Choose the Mars case with the rule in the science notes: ground ice if the Earth story is cold and barren, dust and salts if the Earth story is wind and sediment. Name one region and save a CTX or MOLA view.
6. Write `notes/targets.md` with both names, coordinates, the slope number, the temperature note, and the links. This file is the contract for Sunday.

Stop when `notes/targets.md` exists. Do not start the global download on Saturday night if the targets are still unnamed.

## Sunday morning: screen Earth

Time box: until early afternoon. If the screen is not producing candidate cells by 2:00 pm, switch to the manual fallback at the bottom of this file.

1. Pick the coarse layers from [04-data-resources.md](04-data-resources.md): a vegetation index, land-surface temperature, a dryness or precipitation layer you can cite, and elevation only for shortlisted patches.
2. Build a grid of about 10–50 km. Score only the features measured across the global grid. If the slope column is null, leave slope out of the score and disclose that omission; compare local patch slopes with the lunar band separately. Write the weights in code or in a table. Missing data stays missing.
3. Drop cells inside the famous control you chose (start with the Atacama Desert unless another famous site is a fairer control). Rank what remains.
4. Take the top five named regions. Look at each in [NASA Worldview](https://worldview.earthdata.nasa.gov/). Reject any cell that is ocean, ice-sheet interior with no workable ground, a city, or a data error.
5. Choose:
   - **Site A:** the best remaining region a non-specialist has heard of less often than Atacama.
   - **Site B:** the famous control, scored with the same weights.
6. For A and B only, download a local elevation tile (SRTM or Copernicus DEM; SRTM does not cover Antarctica or the far north) and compute median slope. Report this as a separate patch check, not as part of the global score unless comparable slope data exist for the full grid. If a slope misses the lunar band, say so. Do not quietly change the band.

Save `sources.csv` as you go: quantity, unit, dataset, date, link, patch, method.

## Sunday afternoon: dossiers and the map

Time box: until about 6:30 pm.

For Site A and Site B, write one page each with the same headings:

- Where it is (name, country, center coordinates, patch size).
- Matches (only rows with a source).
- Breaks (include gravity, air, and radiation every time, plus any failed dimension such as temperature or minerals).
- How a mission would use it (one rehearsal: a drive, a sample, or a dust test).
- Confidence: high, medium, or low, and the reason (missing ice map, coarse grid, and so on).

Then make the map. A Folium HTML file, a Worldview screenshot pair, or a single web page is enough. The map must show:

- Site A and Site B on Earth.
- The named Moon target and the named Mars target, even if they sit on separate small maps.
- A legend that says the score is a partial match, not a probability of mission success.

Put the pages in the repo as `docs/site-a.md` and `docs/site-b.md`, or as sections of one `RESULTS.md`. Keep this planning folder (`docs/01` through `docs/06`) as background. The submission should point judges at the result, not at this plan.

## Sunday evening: slides, repo, form

Time box: 6:30 pm to 10:30 pm.

1. Freeze the code and the numbers. No new dataset after 7:30 pm.
2. Build the seven slides listed in [06-submission-checklist.md](06-submission-checklist.md). Export to PDF.
3. Push the public repo. Include a `README` with the result in the first screen, the run steps, the limits, and the data links.
4. Upload the PDF where a private browser can open it.
5. Fill the project form with the text blocks in the checklist. Paste from the repo so the numbers match.
6. Check both boxes, submit, and reload the team page to confirm the project shows as submitted.
7. Open every link in a private window. If one fails, fix the share setting and update the form if the site still allows edits.

If the local event has a live judging slot, keep a five-minute talk in the same order as the slides and leave the rest of the slot for questions. The website text still has to be English even if the room speaks another language.

## Cut line if the clock slips

Use the first row that is still true. Do not skip the row and keep building the full app.

| If this is still true | Do this instead | Still submit |
| --- | --- | --- |
| No global screen by 2:00 pm | Pick Site A from a Worldview search of cold, barren, sloped ground outside Atacama, using the same measurements by hand on two patches. Say the search was manual | Yes |
| No slope number by 5:00 pm | Report elevation and a qualitative slope from the imagery, and mark slope as unquantified | Yes |
| No web map by 8:00 pm | Three labeled screenshots in the repo and on the slides | Yes |
| No deck by 9:30 pm | A seven-section `SLIDES.md` exported or pasted into a public Google Slides file with seven slides, even if the design is plain | Yes |
| Nothing measured by 9:30 pm | Do not invent measurements. Submit a short report that states the targets, the data you opened, and the comparison you could not finish. A honest incomplete project is valid. A fabricated score is not | Yes, with the limits stated |

## What not to build

- A mobile app, an account system, or a trained neural network.
- A ranking of twenty famous analog sites. That project already exists in public this weekend, and it does not by itself find a less-studied place.
- A claim that Ladakh, the Thar Desert, Atacama, or any other home-country site wins before the screen says so. A local site is allowed, and local photos are allowed, only if the same numbers used everywhere else put it on the list.
- A single similarity percentage with no table under it. If you show a score, show the features, the weights, and the missing cells.

## What one more week should add

1. Process quality-controlled seasonal Earth observations; the June 2024 screen is a one-month snapshot.
2. Add a cited Earth ice/permafrost layer and test whether a candidate can support a ground-ice operations rehearsal. Until then, do not claim a Mars Earth analog.
3. Use finer terrain data to assess route-scale slope and roughness, not only a 0.2° cell median.
4. Check site access, permissions, seasonality, and safety before recommending fieldwork.
5. If feasible, run the paired rover-mobility trial and publish repeated-run measurements and uncertainty. Until then, the trial remains a proposal.

The checklist in the next file is the submission review, not evidence that these future validations have been completed.
