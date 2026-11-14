# Map

`web/index.html` is the judge-facing map. It is one file. Ranking does not call a server.

The score is a partial match on measured features, not a probability of mission success. A lower score is a closer partial match.

## Open it

Double-click `web/index.html`, or paste the file path into a browser. A local URL looks like `file:///D:/DTU/NasaHackathon/web/index.html`.

On GitHub Pages, with the repository root as the site, the page is `web/index.html`.

The feature table is embedded in the file. Leaflet and the OpenStreetMap basemap load from the network so the Earth map can draw. The ranking still runs if those tiles are slow. The Moon target and the Mars target are labeled panels under the Earth map. They are not drawn as Earth coordinates.

## Rebuild the embedded table

After `data/processed/features.csv` changes, or after a change to `notes/weights.json` or `notes/targets.md` that should become the new default:

```
python src/export_map_data.py
```

That command reads the measurement table, the default weights, and the locked Moon and Mars names, embeds the table, and writes `web/index.html`. It checks the default order against `results/top5.csv` and `results/control.csv` and stops if they disagree. It does not edit those files.

Moving a weight does not need that command. The page recomputes the order in the browser. The 95th-percentile scales and the cold-tail target stay the ones computed at build time, which is the same rule as `src/score.py`.

## What a judge should try

1. Open the page. The line under the title says the score is a partial match on measured features, not a probability of mission success. Rank 1 is `73.5_-40.5` with score 0.162265. That matches `results/top5.csv`.
2. Site A is Kunlun Mountains, cell `35.3_81.1`, the green A marker. Site B is Vinchina, cell `-27.9_-68.9`, the amber B marker inside the Atacama box. Site B is the control. It is not rank 1. The buttons World, Rank 1, Site A, Site B, and Hold-out move the Earth map. Dark map switches the basemap. The first open starts a short guide. The Guide button plays it again. The Moon panel is Shackleton–de Gerlache connecting ridge. The Mars panel is Arcadia Planitia, the terraced crater Badger.
3. Select a cell. `slope_median_deg` is blank. The slope control is disabled and labeled no data. A measured precipitation of 0 stays 0. The local zoom slopes on the site cards are patch measurements. They are not the grid column, and the score leaves them out.
4. Move the `ndvi_median` weight from 1 to 3. Rank 1 becomes `35.3_81.3` with score 0.112430. The Atacama box stays off the discovery list. Site B's score becomes 0.105244, and Site B stays the control. Reset weights. The batch order returns.
5. Move the `ndvi_median` weight to 0. Cells with a blank NDVI can enter the list, and that blank stays blank. It is not shown as zero.

The browser formula is the weighted mean in `results/score-notes.md`. At the default weights the page matched the batch top five and the control cell. Changing the slope weight does nothing while that column is empty, because the control is disabled and the column is not applied.
