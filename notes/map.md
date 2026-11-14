# Map

`web/index.html` is the judge-facing map. It is one file. Ranking does not call a server.

The score is a partial match on measured features, not a probability of mission success. A lower score is a closer partial match.

## Open it

Double-click `web/index.html`, or paste the file path into a browser. A local URL looks like `file:///D:/DTU/NasaHackathon/web/index.html`.

On GitHub Pages, with the repository root as the site, the page is `web/index.html`.

The feature table is embedded in the file. Leaflet displays OpenFreeMap’s Positron style, and the dark control switches to its dark style. OpenFreeMap uses public vector tiles and does not require an API key. The ranking still runs if map tiles are slow. The right rail shows the selected Earth cell first, then Site A and Site B, the discovery list, and closed-by-default weight controls. The Moon and Mars targets stay fixed inside the selected-cell panel; only the Earth values change when another cell is selected. They are not drawn as Earth coordinates.

## Rebuild the embedded table

After `data/processed/features.csv` changes, or after a change to `notes/weights.json` or `notes/targets.md` that should become the new default:

```
python src/export_map_data.py
```

That command reads the measurement table, the default weights, and the locked Moon and Mars names, embeds the table, and writes `web/index.html`. It checks the default order against `results/top5.csv` and `results/control.csv` and stops if they disagree. It does not edit those files.

Moving a weight does not need that command. The page recomputes the order in the browser. The 95th-percentile scales and the cold-tail target stay the ones computed at build time, which is the same rule as `src/score.py`.

## What a judge should try

1. Open the page. The line under the title says the score is a partial match on measured features, not a probability of mission success. The page checks its embedded June ranking against `results/top5.csv` and the control in `results/control.csv`.
2. Use World, Rank 1, Site A, Site B, and Hold-out to move the map. Site A is Kunlun Mountains, cell `35.3_81.1`, with the green marker. Site B is Vinchina, cell `-27.9_-68.9`, with the amber marker inside the Atacama box; Site B is the control. Dark map switches to OpenFreeMap’s dark style. The first open starts a short guide; Guide plays it again.
3. Select a rank, pin, or site card. Each selects the same cell, highlights its row, updates the Earth side of the Moon and Mars comparison, and shows the current score. The target values stay fixed. Slope is no data for ordinary cells; the Kunlun and Vinchina patch measurements are shown separately and are not in the June score. A measured precipitation of 0 stays 0.
4. Open Adjust weights and move the `ndvi_median` weight from 1 to 3. Rank 1 becomes `35.3_81.3` at 0.112430, Site B becomes 0.105244, and the Atacama box stays off the discovery list. Reset weights to restore the values from `notes/weights.json`.
5. Set the `ndvi_median` weight to 0. Cells with a blank NDVI can enter the list only if all remaining used features are measured; a blank is never shown as zero.

The browser formula is the weighted mean in `results/score-notes.md`. At the default weights the page matches the batch top five and the control cell before the rejected Greenland ice-sheet cells are removed from the visible discovery list. Changing the slope weight is unavailable while that column is empty: the panel says no data, and there is no dead slider.
