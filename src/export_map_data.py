"""Embed the land-cell table in web/index.html and build the judge-facing map.

Reads data/processed/features.csv, notes/weights.json, notes/targets.md,
notes/features.md, and results/sites.json. Uses the same distance rules as
src/score.py. Writes web/index.html only. Does not rank by editing
results/top5.csv, and does not fill a blank measurement.

The page is Leaflet plus the OpenFreeMap Positron and dark styles. It does not load Folium,
Bootstrap, jQuery, glyphicons, Font Awesome, or Leaflet.awesome-markers.

Weight changes are applied in the browser. Re-run this script only after the
measurement table, the default weights, or the locked targets change.
"""

from __future__ import annotations

import base64
import gzip
import html
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import score as scorer  # noqa: E402

SITES_JSON = ROOT / "results" / "sites.json"
OUT_HTML = ROOT / "web" / "index.html"

NULL_I32 = np.int32(-2147483648)
RECORD_BYTES = 16
MEASURED_PACK = ("ndvi_median", "precip_median_mm_hr", "lst_night_median_k")
PAGE_FEATURES = (
    {"key": "ndvi_median", "label": "Vegetation", "unit": "NDVI"},
    {"key": "precip_median_mm_hr", "label": "Dryness", "unit": "mm/hr"},
    {"key": "lst_night_median_k", "label": "Night cold", "unit": "K"},
    {"key": "slope_median_deg", "label": "Slope", "unit": "°"},
)
# The five cells classed ice-sheet interior. The box is the cluster of cells
# that outscored Kunlun and were classed the same way in notes/worldview-checks.md.
REJECTED_ICE = (
    "73.5_-40.5",
    "73.5_-40.7",
    "73.9_-40.1",
    "73.5_-40.9",
    "74.1_-39.9",
)
ICE_SHEET = {
    "lat_min": 70.5,
    "lat_max": 78.9,
    "lon_min": -50.1,
    "lon_max": -28.9,
}


def stop(messages: list[str]) -> None:
    print("Stopping. Required inputs are missing or a locked input was not measured.", file=sys.stderr)
    for message in messages:
        print(f"  {message}", file=sys.stderr)
    sys.exit(1)


def require_inputs() -> None:
    missing = []
    for path in (
        scorer.FEATURES_CSV,
        scorer.WEIGHTS_JSON,
        scorer.TARGETS_MD,
        scorer.FEATURES_MD,
        SITES_JSON,
        scorer.TOP5_CSV,
        scorer.CONTROL_CSV,
    ):
        if not path.is_file():
            missing.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    if missing:
        stop(missing)


def section(text: str, heading: str) -> str:
    for part in re.split(r"\n(?=## )", text):
        if part.startswith(f"## {heading}\n") or part.startswith(f"## {heading}\r"):
            return part
    stop([f"{scorer.TARGETS_MD.relative_to(ROOT)} has no '## {heading}' section."])
    raise AssertionError


def locked_phrase(block: str, label: str) -> str:
    match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", block)
    if match is None:
        stop(
            [
                f"{scorer.TARGETS_MD.relative_to(ROOT)} has no measured '{label}' "
                f"line in the expected section."
            ]
        )
    return match.group(1).strip()


def read_bodies(text: str) -> dict[str, str]:
    moon = section(text, "Moon")
    mars = section(text, "Mars")
    moon_name = locked_phrase(moon, "Name")
    moon_center = locked_phrase(moon, "Center")
    if not re.search(r"[0-9]", moon_center) or "°" not in moon_center:
        stop([f"{scorer.TARGETS_MD.relative_to(ROOT)} Moon center has no coordinate."])
    mars_name = locked_phrase(mars, "Region").rstrip(".")
    mars_center = locked_phrase(mars, "Coordinates").rstrip(".")
    if not re.search(r"[0-9]", mars_center) or "°" not in mars_center:
        stop([f"{scorer.TARGETS_MD.relative_to(ROOT)} Mars coordinates were not measured."])
    if not mars_name:
        stop([f"{scorer.TARGETS_MD.relative_to(ROOT)} Mars region name is blank."])
    return {
        "moon_name": moon_name,
        "moon_center": moon_center,
        "mars_name": mars_name,
        "mars_center": mars_center,
    }


def pack_micro(series: pd.Series) -> np.ndarray:
    out = np.full(len(series), NULL_I32, dtype="<i4")
    mask = series.notna().to_numpy()
    if not mask.any():
        return out
    scaled = np.rint(series.to_numpy(dtype=np.float64)[mask] * 1_000_000)
    if np.any(scaled <= np.iinfo(np.int32).min) or np.any(scaled > np.iinfo(np.int32).max):
        stop([f"A measured value in {series.name} does not fit the embedded table."])
    out[mask] = scaled.astype("<i4")
    back = out[mask].astype(np.float64) / 1_000_000
    if not np.array_equal(back, series.to_numpy(dtype=np.float64)[mask]):
        stop([f"Embedding {series.name} changed a measured value. The page was not written."])
    return out


def pack_tenths(series: pd.Series) -> np.ndarray:
    scaled = np.rint(series.to_numpy(dtype=np.float64) * 10.0)
    if np.any(scaled < -32768) or np.any(scaled > 32767):
        stop([f"{series.name} does not fit a tenth-degree coordinate."])
    out = scaled.astype("<i2")
    back = out.astype(np.float64) / 10.0
    if np.max(np.abs(back - series.to_numpy(dtype=np.float64))) > 1e-9:
        stop([f"Embedding {series.name} changed a coordinate. The page was not written."])
    return out


def score_frame(
    frame: pd.DataFrame,
    weights: dict[str, float],
    scales: dict[str, float],
    cold_target: float,
    slope_band: tuple[float, float],
    active: list[str],
) -> pd.DataFrame:
    """Same eligibility and weighted mean as src/score.py, for the build check."""
    scored = frame.copy()
    weight_sum = pd.Series(0.0, index=scored.index)
    weighted = pd.Series(0.0, index=scored.index)
    for name in active:
        distance = scorer.raw_distance(scored[name], name, cold_target, slope_band)
        present = scored[name].notna()
        weight_sum = weight_sum + weights[name] * present.astype(float)
        weighted = weighted + weights[name] * (distance / scales[name]) * present.astype(float)
    scored["score"] = weighted / weight_sum.where(weight_sum > 0)
    eligible = pd.Series(True, index=scored.index)
    for name in active:
        eligible = eligible & scored[name].notna()
    scored["eligible"] = eligible
    scored["in_holdout"] = scorer.holdout_mask(scored)
    return scored


def formatted_score(value: float) -> str:
    return f"{float(value):.6f}"


def check_against_batch(scored: pd.DataFrame, active: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    discovery = scored.loc[scored["eligible"] & ~scored["in_holdout"]].sort_values(
        ["score", "lat_center_deg", "lon_center_deg"],
        ascending=[True, True, True],
        kind="mergesort",
    )
    control = scored.loc[scored["eligible"] & scored["in_holdout"]].sort_values(
        ["score", "lat_center_deg", "lon_center_deg"],
        ascending=[True, True, True],
        kind="mergesort",
    )
    if discovery.empty or control.empty:
        stop(["The batch check produced an empty discovery list or an empty control list."])
    top = discovery.head(5)
    published = pd.read_csv(scorer.TOP5_CSV)
    published_control = pd.read_csv(scorer.CONTROL_CSV)
    problems = []
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        cell = scorer.cell_id(float(row["lat_center_deg"]), float(row["lon_center_deg"]))
        got = formatted_score(row["score"])
        pub_id = str(published.loc[rank - 1, "cell_id"])
        pub_score = f"{float(published.loc[rank - 1, 'score']):.6f}"
        if cell != pub_id or got != pub_score:
            problems.append(
                f"rank {rank}: page build computed {cell} {got}; results/top5.csv has {pub_id} {pub_score}."
            )
        if bool(row["in_holdout"]):
            problems.append(f"rank {rank} cell {cell} is inside the Atacama hold-out.")
    control_row = control.iloc[0]
    control_id = scorer.cell_id(float(control_row["lat_center_deg"]), float(control_row["lon_center_deg"]))
    control_score = formatted_score(control_row["score"])
    pub_control_id = str(published_control.loc[0, "cell_id"])
    pub_control_score = f"{float(published_control.loc[0, 'score']):.6f}"
    if control_id != pub_control_id or control_score != pub_control_score:
        problems.append(
            f"control: page build computed {control_id} {control_score}; "
            f"results/control.csv has {pub_control_id} {pub_control_score}."
        )
    if problems:
        stop(["The browser constants do not match the batch ranking.", *problems])
    if list(active) != ["ndvi_median", "precip_median_mm_hr", "lst_night_median_k"]:
        stop(
            [
                "The active features are not the three measured columns this delivery scores. "
                f"Found: {', '.join(active) or 'none'}."
            ]
        )
    return top, control_row

def rejected_center(lat: float, lon: float) -> bool:
    if scorer.cell_id(lat, lon) in REJECTED_ICE:
        return True
    return ICE_SHEET["lat_min"] <= lat <= ICE_SHEET["lat_max"] and ICE_SHEET["lon_min"] <= lon <= ICE_SHEET["lon_max"]


def check_site_scores(scored: pd.DataFrame, sites: dict) -> None:
    problems = []
    for key in ("site_a", "site_b"):
        lat = float(sites[key]["center"]["latitude"])
        lon = float(sites[key]["center"]["longitude"])
        hit = scored[(scored["lat_center_deg"] == lat) & (scored["lon_center_deg"] == lon)]
        if len(hit) != 1:
            problems.append(f"{key} is not one row of the measurement table.")
            continue
        got = float(hit.iloc[0]["score"])
        published = float(sites[key]["score"])
        if abs(got - published) >= 0.000001:
            problems.append(
                f"{key} computed {got:.9f}; published {published:.6f}. The published score was not edited."
            )
    if problems:
        stop(problems)


def weight_controls(weights: dict[str, float], all_null: dict[str, bool]) -> str:
    blocks = []
    for spec in PAGE_FEATURES:
        name = spec["key"]
        if name not in weights:
            continue
        label = html.escape(spec["label"])
        key = html.escape(name)
        if all_null[name]:
            blocks.append(
                f"""<div class="pm-weight">
              <span class="pm-label">{label}</span>
              <span class="pm-colname">{key}</span>
              <span class="pm-nodata">no data</span>
            </div>"""
            )
            continue
        value = weights[name]
        blocks.append(
            f"""<label class="pm-weight">
              <span class="pm-label">{label}</span>
              <span class="pm-colname">{key}</span>
              <input class="pm-num" id="wn-{key}" type="number" min="0" max="5" step="0.1" value="{value:g}" inputmode="decimal" aria-label="{label} weight">
              <input id="w-{key}" type="range" min="0" max="5" step="0.1" value="{value:g}" data-default="{value:g}" aria-label="{label} weight">
            </label>"""
        )
    return "\n".join(blocks)


def page_html(
    bodies: dict[str, str],
    sites: dict,
    weights: dict[str, float],
    all_null: dict[str, bool],
) -> str:
    site_a = sites["site_a"]
    site_b = sites["site_b"]
    a_score = f"{float(site_a['score']):.6f}"
    b_score = f"{float(site_b['score']):.6f}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Partial Match</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.1/dist/maplibre-gl.css">
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.1/dist/maplibre-gl.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js"></script>
{STYLE}
</head>
<body>
<div class="pm-app">
  <header class="pm-banner">
    <h1>Partial Match</h1>
    <div class="pm-lead">
      <p class="pm-sentence">The score is a partial match on measured features, not a probability of mission success.</p>
      <p class="pm-quiet">A lower score is a closer partial match.</p>
      <p id="pm-check">Reading the embedded table.</p>
    </div>
    <button type="button" id="pm-guide" class="pm-btn">Guide</button>
  </header>
  <div class="pm-map-cell">
    <div id="pm-map"></div>
    <div class="pm-hud">
      <button type="button" id="pm-go-world" class="pm-btn">World</button>
      <button type="button" id="pm-go-rank" class="pm-btn">Rank 1</button>
      <button type="button" id="pm-go-a" class="pm-btn">Site A</button>
      <button type="button" id="pm-go-b" class="pm-btn">Site B</button>
      <button type="button" id="pm-go-box" class="pm-btn">Hold-out</button>
      <button type="button" id="pm-basemap" class="pm-btn" aria-pressed="false">Dark map</button>
    </div>
  </div>
  <aside class="pm-side">
    <section id="pm-selected" class="pm-card">
      <h2>Selected cell</h2>
      <p id="pm-cell-id" class="pm-id">Reading the embedded table.</p>
      <p id="pm-cell-coord" class="pm-coord"></p>
      <p id="pm-cell-role"></p>
      <p class="pm-scoreline"><span id="pm-live-score" class="pm-score">—</span> <span id="pm-score-kind">June three-feature score</span></p>
      <p class="pm-quiet">June 2024 is one month, not a climate normal.</p>
      <div id="pm-earth"></div>
      <article class="pm-block">
        <h3>Moon</h3>
        <p class="pm-place">{html.escape(bodies["moon_name"])}</p>
        <p class="pm-coord">{html.escape(bodies["moon_center"])}</p>
        <p class="pm-quiet">Not a point on this Earth map.</p>
        <div id="pm-moon-rows"></div>
      </article>
      <article class="pm-block">
        <h3>Mars</h3>
        <p class="pm-place">{html.escape(bodies["mars_name"])}</p>
        <p class="pm-coord">{html.escape(bodies["mars_center"])}</p>
        <p class="pm-quiet">Not a point on this Earth map. Case: ground ice.</p>
        <div id="pm-mars-rows"></div>
        <p class="pm-minerals">Minerals, ice map, and dust index: no data.</p>
      </article>
      <p class="pm-limit">Gravity, vacuum or thin air, and radiation are limits. They are not score terms.</p>
    </section>
    <div class="pm-stats">
      <button type="button" id="pm-jump-a" class="pm-card pm-stat pm-site-a">
        <span class="pm-kicker">Site A · {html.escape(site_a["country"])}</span>
        <strong>{html.escape(site_a["name"])}</strong>
        <span class="pm-coord">{html.escape(site_a["cell_id"])}</span>
        <span id="pm-site-a-score" class="pm-stat-score">—</span>
        <span id="pm-site-a-kind" class="pm-kicker">June three-feature score</span>
        <span class="pm-kicker">Published {a_score}</span>
      </button>
      <button type="button" id="pm-jump-b" class="pm-card pm-stat pm-site-b">
        <span class="pm-kicker">Site B · control · {html.escape(site_b["country"])}</span>
        <strong>{html.escape(site_b["name"])}</strong>
        <span class="pm-coord">{html.escape(site_b["cell_id"])}</span>
        <span id="pm-site-b-score" class="pm-stat-score">—</span>
        <span id="pm-site-b-kind" class="pm-kicker">June three-feature score</span>
        <span class="pm-kicker">Published {b_score}</span>
      </button>
    </div>
    <section class="pm-card">
      <h2>Discovery</h2>
      <p id="pm-status" class="pm-hint">Reading the embedded table.</p>
      <ol id="pm-ranks" class="pm-ranks"></ol>
    </section>
    <details id="pm-weights" class="pm-card">
      <summary>Adjust weights</summary>
      <p class="pm-hint">Defaults from notes/weights.json. A change recomputes the order on this page. Scales stay fixed. A lower score is a closer partial match.</p>
      {weight_controls(weights, all_null)}
      <button type="button" id="pm-reset" class="pm-btn">Reset</button>
    </details>
  </aside>
</div>
<div id="pm-tour" class="pm-tour" hidden>
  <div id="pm-tour-top" class="pm-tour-shade"></div>
  <div id="pm-tour-left" class="pm-tour-shade"></div>
  <div id="pm-tour-right" class="pm-tour-shade"></div>
  <div id="pm-tour-bottom" class="pm-tour-shade"></div>
  <div id="pm-tour-ring" class="pm-tour-ring"></div>
  <div id="pm-tour-card" class="pm-tour-card" role="dialog" aria-modal="true" aria-labelledby="pm-tour-title">
    <p id="pm-tour-count" class="pm-kicker">1 of 5</p>
    <h2 id="pm-tour-title">The score</h2>
    <p id="pm-tour-body"></p>
    <div class="pm-tour-actions">
      <button type="button" id="pm-tour-skip" class="pm-btn">Skip</button>
      <span class="pm-tour-nav">
        <button type="button" id="pm-tour-back" class="pm-btn">Back</button>
        <button type="button" id="pm-tour-next" class="pm-btn pm-btn-primary">Next</button>
      </span>
    </div>
  </div>
</div>
"""


STYLE = """
<style>
  :root {
    --bg: #f4f6f8;
    --card: #ffffff;
    --line: #e4e8ee;
    --ink: #1c2430;
    --muted: #5e6a78;
    --blue: #1d6fdb;
    --blue-soft: #e8f1fc;
    --green: #0f8a62;
    --amber: #c47a12;
    --bad: #b42318;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; background: var(--bg); color: var(--ink); }
  body, button, input, summary { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 15px; line-height: 1.45; }
  button, input, summary { color: inherit; }
  h1, h2, h3, p { margin: 0; }
  h1 { font-size: 20px; font-weight: 600; letter-spacing: -0.02em; }
  h2 { font-size: 16px; font-weight: 600; }
  .pm-app { height: 100%; display: grid; grid-template-columns: minmax(0, 1fr) 400px; grid-template-rows: auto minmax(0, 1fr); }
  .pm-banner { grid-column: 1 / -1; display: flex; flex-wrap: wrap; align-items: flex-start; gap: 8px 16px; padding: 12px 16px; background: var(--card); border-bottom: 1px solid var(--line); }
  .pm-lead { flex: 1 1 280px; min-width: 0; }
  .pm-sentence { font-size: 15px; white-space: normal; overflow: visible; }
  .pm-quiet, .pm-hint, .pm-kicker { color: var(--muted); font-size: 13px; }
  .pm-quiet { margin-top: 4px; }
  #pm-check { margin-top: 4px; }
  #pm-check.is-bad { color: var(--bad); }
  .pm-map-cell { position: relative; min-width: 0; min-height: 0; background: #d7dde3; }
  #pm-map { position: absolute; inset: 0; }
  .leaflet-container { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; background: #d7dde3; }
  .leaflet-container img { max-width: none !important; }
  .leaflet-bar { border: 1px solid var(--line) !important; border-radius: 12px !important; box-shadow: none !important; overflow: hidden; }
  .leaflet-bar a, .leaflet-bar a:hover { background: var(--card); color: var(--ink); border-bottom-color: var(--line); width: 32px; height: 32px; line-height: 32px; }
  .pm-hud { position: absolute; z-index: 500; top: 8px; left: 8px; display: flex; flex-wrap: wrap; gap: 8px; max-width: calc(100% - 64px); }
  .pm-btn { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 8px 12px; font-size: 13px; cursor: pointer; }
  .pm-btn:hover { border-color: #b9d4f6; }
  .pm-btn-primary { background: var(--blue); color: #fff; border-color: var(--blue); }
  .pm-btn:focus-visible, .pm-stat:focus-visible, .pm-ranks button:focus-visible, summary:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
  .pm-side { min-width: 0; overflow: auto; padding: 8px; border-left: 1px solid var(--line); }
  .pm-card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px; margin-bottom: 8px; }
  .pm-scoreline { min-height: 32px; display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; margin-top: 8px; }
  .pm-score, .pm-stat-score, .pm-num, .pm-coord, .pm-id { font-family: "Cascadia Mono", ui-monospace, Consolas, monospace; font-variant-numeric: tabular-nums; }
  .pm-score, .pm-stat-score { color: var(--blue); font-weight: 600; font-size: 22px; }
  .pm-id { font-size: 14px; margin-top: 8px; overflow-wrap: anywhere; }
  .pm-coord { font-size: 13px; overflow-wrap: anywhere; }
  .pm-block { margin-top: 16px; }
  .pm-block h3 { font-size: 13px; font-weight: 600; color: var(--muted); }
  .pm-place { font-weight: 600; margin-top: 4px; overflow-wrap: break-word; }
  .pm-earth-line, .pm-row { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 0.85fr); gap: 8px; padding: 8px 0; border-top: 1px solid var(--line); font-size: 13px; }
  .pm-row > div { min-width: 0; overflow-wrap: anywhere; }
  .pm-earth-line { grid-template-columns: minmax(0, 1fr) auto; }
  .pm-label { font-weight: 600; }
  .pm-colname { display: block; color: var(--muted); font-family: "Cascadia Mono", ui-monospace, Consolas, monospace; font-size: 11px; font-weight: 400; }
  .pm-note, .pm-minerals, .pm-limit { color: var(--muted); font-size: 13px; margin-top: 8px; overflow-wrap: break-word; }
  .pm-num { font-size: 12px; overflow-wrap: anywhere; }
  .pm-note { grid-column: 1 / -1; margin-top: 0; }
  .pm-limit { color: var(--ink); }
  .pm-stats { display: grid; gap: 8px; }
  .pm-stat { display: grid; gap: 2px; width: 100%; text-align: left; cursor: pointer; }
  .pm-stat strong { overflow-wrap: break-word; }
  .pm-site-a { box-shadow: inset 3px 0 0 var(--green); }
  .pm-site-b { box-shadow: inset 3px 0 0 var(--amber); }
  .pm-stat.is-selected, .pm-ranks button.is-selected { background: var(--blue-soft); border-color: #b9d4f6; }
  .pm-ranks { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 8px; }
  .pm-ranks button { width: 100%; display: grid; grid-template-columns: 2rem minmax(0, 1fr) auto; gap: 8px; align-items: center; text-align: left; background: var(--bg); border: 1px solid var(--line); border-radius: 12px; padding: 8px; cursor: pointer; }
  .pm-rankn { color: var(--muted); font-variant-numeric: tabular-nums; }
  .pm-list-score { color: var(--blue); font-family: "Cascadia Mono", ui-monospace, Consolas, monospace; font-variant-numeric: tabular-nums; font-weight: 600; }
  details summary { cursor: pointer; font-weight: 600; }
  .pm-weight { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 8px; padding: 8px 0; border-top: 1px solid var(--line); }
  .pm-weight input[type="range"] { grid-column: 1 / -1; width: 100%; accent-color: var(--blue); }
  .pm-num { width: 4.6rem; text-align: right; background: var(--bg); border: 1px solid var(--line); border-radius: 10px; padding: 4px 8px; }
  .pm-nodata { color: var(--muted); }
  .pm-tour[hidden] { display: none; }
  .pm-tour-shade { position: fixed; background: rgba(22, 28, 36, 0.46); z-index: 2100; }
  .pm-tour-ring { position: fixed; z-index: 2101; border: 2px solid var(--blue); border-radius: 12px; pointer-events: none; }
  .pm-tour-card { position: fixed; z-index: 2102; width: min(380px, calc(100vw - 32px)); background: var(--card); color: var(--ink); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }
  .pm-tour-card h2 { font-size: 18px; margin: 4px 0 8px; }
  .pm-tour-actions { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 16px; }
  .pm-tour-nav { display: flex; gap: 8px; }
  @media (max-width: 980px) {
    html, body { height: auto; overflow: auto; }
    .pm-app { height: auto; display: block; }
    .pm-map-cell { height: 70vh; }
    .pm-side { border-left: 0; border-top: 1px solid var(--line); }
    .pm-row, .pm-earth-line { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
    .pm-note { grid-column: 1 / -1; }
  }
</style>
"""


SCRIPT = r"""
<script>
const META = __META__;
const B64 = "__B64__";
const NULL_I32 = -2147483648;
const LIGHT = "https://tiles.openfreemap.org/styles/positron";
const DARK = "https://tiles.openfreemap.org/styles/dark";
const ATTRIB = '<a href="https://openfreemap.org">OpenFreeMap</a> &copy; <a href="https://www.openmaptiles.org/">OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const TARGET = {
  ndvi_median: { moon: "none", mars: "none" },
  precip_median_mm_hr: { moon: "none", mars: "none" },
  lst_night_median_k: { moon: "none", mars: "none" },
  slope_median_deg: { moon: "band", mars: "none" }
};

function hexFloat(hex) {
  const bytes = new Uint8Array(8);
  for (let i = 0; i < 8; i += 1) bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  return new DataView(bytes.buffer).getFloat64(0, true);
}

function b64ToBytes(b64) {
  const clean = b64.replace(/\s+/g, "");
  const out = new Uint8Array(Math.floor(clean.length * 3 / 4));
  let at = 0;
  for (let i = 0; i < clean.length; i += 4096) {
    const bin = atob(clean.slice(i, i + 4096));
    for (let j = 0; j < bin.length; j += 1) out[at++] = bin.charCodeAt(j);
  }
  return out.subarray(0, at);
}

function esc(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

function formatMeasured(micro) {
  if (micro === NULL_I32) return "";
  const neg = micro < 0;
  const abs = Math.abs(micro);
  const whole = Math.floor(abs / 1000000);
  let frac = String(abs % 1000000).padStart(6, "0").replace(/0+$/, "");
  const body = frac ? whole + "." + frac : String(whole);
  return neg ? "-" + body : body;
}

function fmtScore(value) {
  return value.toFixed(6);
}

const SCALES = {
  ndvi_median: hexFloat(META.scales_hex.ndvi_median),
  precip_median_mm_hr: hexFloat(META.scales_hex.precip_median_mm_hr),
  lst_night_median_k: hexFloat(META.scales_hex.lst_night_median_k)
};
const COLD = hexFloat(META.cold_hex);
const SLOPE_LOW = META.slope_band[0];
const SLOPE_HIGH = META.slope_band[1];

function rawDistance(name, value) {
  if (name === "ndvi_median") return Math.abs(value - 0);
  if (name === "precip_median_mm_hr") return Math.max(value - 0, 0);
  if (name === "lst_night_median_k") return Math.max(value - COLD, 0);
  if (name === "slope_median_deg") return Math.max(SLOPE_LOW - value, 0) + Math.max(value - SLOPE_HIGH, 0);
  return NaN;
}

let lats, lons, micros, norms, hold, n;
let scores, eligible;
let selected = -1;
let pins = null;
let markerByIndex = new Map();
let map = null;
let positron = null;
let darkMatter = null;
let darkOn = false;
let visibleDiscovery = [];
let lastControl = -1;
let rankTimer = 0;

function tenths(value) {
  return Math.round(value * 10);
}

function inHoldout(i) {
  const box = META.holdout;
  return lats[i] >= tenths(box.lat_min) && lats[i] <= tenths(box.lat_max)
    && lons[i] >= tenths(box.lon_min) && lons[i] <= tenths(box.lon_max);
}

function cellId(i) {
  return (lats[i] / 10).toFixed(1) + "_" + (lons[i] / 10).toFixed(1);
}

function formatLat(value) {
  return Math.abs(value).toFixed(1) + "°" + (value >= 0 ? "N" : "S");
}

function formatLon(value) {
  return Math.abs(value).toFixed(1) + "°" + (value >= 0 ? "E" : "W");
}

function findCell(lat, lon) {
  const la = tenths(lat);
  const lo = tenths(lon);
  for (let i = 0; i < n; i += 1) {
    if (lats[i] === la && lons[i] === lo) return i;
  }
  return -1;
}

function isRejected(i) {
  const id = cellId(i);
  if (META.rejected.indexOf(id) !== -1) return true;
  const box = META.ice_sheet;
  const lat = lats[i] / 10;
  const lon = lons[i] / 10;
  return lat >= box.lat_min && lat <= box.lat_max && lon >= box.lon_min && lon <= box.lon_max;
}

function featureByKey(key) {
  return META.features.find((feature) => feature.key === key);
}

function activeFeatures(weights) {
  return META.features.filter((feature) => !feature.all_null && weights[feature.key] > 0);
}

function readWeights() {
  const weights = {};
  META.features.forEach((feature) => {
    const input = document.getElementById("w-" + feature.key);
    weights[feature.key] = feature.all_null || !input ? 0 : Number(input.value);
  });
  return weights;
}

function weightsAreDefault() {
  return META.features.every((feature) => {
    if (feature.all_null) return true;
    const input = document.getElementById("w-" + feature.key);
    return Number(input.value) === Number(input.getAttribute("data-default"));
  });
}

function better(i, j) {
  if (scores[i] < scores[j]) return true;
  if (scores[i] > scores[j]) return false;
  if (lats[i] !== lats[j]) return lats[i] < lats[j];
  return lons[i] < lons[j];
}

function rankCells(weights) {
  const use = activeFeatures(weights);
  scores.fill(NaN);
  eligible.fill(0);
  if (!use.length) return { discovery: [], control: -1 };
  let weightSum = 0;
  use.forEach((feature) => { weightSum += weights[feature.key]; });
  const discovery = [];
  let control = -1;
  for (let i = 0; i < n; i += 1) {
    let ok = true;
    let acc = 0;
    for (let k = 0; k < use.length; k += 1) {
      const key = use[k].key;
      const norm = norms[key][i];
      if (Number.isNaN(norm)) { ok = false; break; }
      acc += weights[key] * norm;
    }
    if (!ok) continue;
    scores[i] = acc / weightSum;
    eligible[i] = 1;
    if (hold[i]) {
      if (control < 0 || better(i, control)) control = i;
    } else {
      discovery.push(i);
    }
  }
  discovery.sort((a, b) => (better(a, b) ? -1 : better(b, a) ? 1 : 0));
  return { discovery, control };
}

function bandText() {
  return SLOPE_LOW.toFixed(1) + "\u2013" + SLOPE_HIGH.toFixed(1);
}

function earthValue(key, i) {
  if (i < 0) return null;
  const feature = featureByKey(key);
  if (!feature) return null;
  if (key === "slope_median_deg" && feature.all_null) {
    const patch = META.patch_slope[cellId(i)];
    if (patch == null) return null;
    return { value: Number(patch), text: String(patch), patch: true };
  }
  if (feature.all_null || !micros[key]) return null;
  const micro = micros[key][i];
  if (micro === NULL_I32) return null;
  return { value: micro / 1000000, text: formatMeasured(micro), patch: false };
}

function rowStatus(key, earth, which) {
  if (!earth) return "no data";
  const kind = TARGET[key][which];
  if (kind === "none") return "no referent";
  if (kind === "band") {
    const distance = rawDistance("slope_median_deg", earth.value);
    return distance === 0 ? "inside band" : "outside band";
  }
  return "no data";
}

function targetText(key, which) {
  const kind = TARGET[key][which];
  if (kind === "band") return bandText() + " degrees";
  if (kind === "none") return "no referent";
  return "no data";
}

function rowHtml(feature, earth, which) {
  const waiting = selected < 0;
  const status = waiting ? "\u2014" : rowStatus(feature.key, earth, which);
  const earthText = waiting ? "\u2014" : (earth ? earth.text + " " + feature.unit : "no data");
  let sentence = "";
  if (!waiting && which === "moon" && feature.key === "slope_median_deg" && earth && (status === "inside band" || status === "outside band")) {
    const where = status === "inside band" ? "inside" : "outside";
    sentence = "Median slope " + earth.text + "\u00b0 is " + where + " " + bandText() + "\u00b0 (LOLA Site01).";
    if (earth.patch) sentence += " Later patch, not in the June score.";
  }
  if (!waiting && which === "moon" && feature.key === "lst_night_median_k" && earth) {
    sentence = "Night temperature " + earth.text + " K has no Diviner value in the source table.";
  }
  return "<div class=\"pm-row\"><div><div class=\"pm-label\">" + esc(feature.label) + "</div><div class=\"pm-colname\">" + esc(feature.key) + "</div></div>" +
    "<div><div class=\"pm-kicker\">Earth</div><div class=\"pm-num\">" + esc(earthText) + "</div></div>" +
    "<div><div class=\"pm-kicker\">Target</div><div class=\"pm-num\">" + esc(targetText(feature.key, which)) + "</div></div>" +
    "<div><div class=\"pm-kicker\">Status</div><div>" + esc(status) + "</div></div>" +
    (sentence ? "<p class=\"pm-note\">" + esc(sentence) + "</p>" : "") + "</div>";
}

function renderRows() {
  ["moon", "mars"].forEach((which) => {
    const html = META.features.map((feature) => rowHtml(feature, earthValue(feature.key, selected), which)).join("");
    document.getElementById("pm-" + which + "-rows").innerHTML = html;
  });
  const earth = document.getElementById("pm-earth");
  if (selected < 0) {
    earth.textContent = "Select a cell to compare it with the Moon target and the Mars target.";
    return;
  }
  earth.innerHTML = META.features.map((feature) => {
    const value = earthValue(feature.key, selected);
    const shown = value ? value.text + " " + feature.unit : "no data";
    const note = value && value.patch ? " Later patch, not in the June score." : "";
    return "<div class=\"pm-earth-line\"><div><div class=\"pm-label\">" + esc(feature.label) + "</div><div class=\"pm-colname\">" + esc(feature.key) + "</div></div><div class=\"pm-num\">" + esc(shown + note) + "</div></div>";
  }).join("");
}

function renderDetail(i) {
  const idEl = document.getElementById("pm-cell-id");
  const coordEl = document.getElementById("pm-cell-coord");
  const roleEl = document.getElementById("pm-cell-role");
  const scoreEl = document.getElementById("pm-live-score");
  const kindEl = document.getElementById("pm-score-kind");
  if (i < 0) {
    idEl.textContent = "No cell selected.";
    coordEl.textContent = "";
    roleEl.textContent = "";
    scoreEl.textContent = "\u2014";
    kindEl.textContent = "June three-feature score";
    renderRows();
    return;
  }
  const id = cellId(i);
  idEl.textContent = id;
  coordEl.textContent = formatLat(lats[i] / 10) + ", " + formatLon(lons[i] / 10);
  let role = "Discovery cell.";
  if (hold[i]) role = "Inside the Atacama hold-out.";
  if (id === META.site_a.cell_id) role = "Site A. " + META.site_a.name + ".";
  if (id === META.site_b.cell_id) role = "Site B. " + META.site_b.name + ". Atacama hold-out control.";
  roleEl.textContent = role;
  if (!eligible[i]) {
    scoreEl.textContent = "Not ranked";
    kindEl.textContent = activeFeatures(readWeights()).length
      ? "A used feature is blank on this cell."
      : "No measured feature has a positive weight.";
  } else {
    scoreEl.textContent = fmtScore(scores[i]);
    kindEl.textContent = weightsAreDefault() ? "June three-feature score" : "Score at these weights";
  }
  renderRows();
}

function paintMarkers() {
  markerByIndex.forEach((marker, i) => {
    marker.setStyle({ radius: i === selected ? 9 : 6 });
  });
}

function addCircle(i, fill, tip) {
  const marker = L.circleMarker([lats[i] / 10, lons[i] / 10], {
    radius: i === selected ? 9 : 6,
    color: "#ffffff",
    weight: 2,
    fillColor: fill,
    fillOpacity: 1
  });
  marker.bindTooltip(tip, { direction: "top" });
  marker.on("click", () => select(i));
  marker.addTo(pins);
  markerByIndex.set(i, marker);
}

function drawMarkers() {
  if (!map || typeof L === "undefined") return;
  if (!pins) pins = L.layerGroup().addTo(map);
  pins.clearLayers();
  markerByIndex = new Map();
  const siteA = findCell(META.site_a.lat, META.site_a.lon);
  const siteB = findCell(META.site_b.lat, META.site_b.lon);
  const reserved = new Set([siteA, siteB]);
  visibleDiscovery.slice(0, 5).forEach((i) => {
    if (reserved.has(i)) return;
    const score = eligible[i] ? fmtScore(scores[i]) : "not ranked";
    addCircle(i, "#1d6fdb", cellId(i) + " \u00b7 " + score);
  });
  if (siteA >= 0) {
    const score = eligible[siteA] ? fmtScore(scores[siteA]) : "not ranked";
    addCircle(siteA, "#0f8a62", "Site A \u00b7 " + META.site_a.name + " \u00b7 " + score);
  }
  if (siteB >= 0) {
    const score = eligible[siteB] ? fmtScore(scores[siteB]) : "not ranked";
    addCircle(siteB, "#c47a12", "Site B \u00b7 " + META.site_b.name + " \u00b7 " + score);
  }
}

function renderList(weights) {
  const list = document.getElementById("pm-ranks");
  const status = document.getElementById("pm-status");
  const use = activeFeatures(weights);
  if (!use.length) {
    list.innerHTML = "";
    status.textContent = "No measured feature has a positive weight. Nothing is ranked.";
  } else {
    const shown = visibleDiscovery.slice(0, 5);
    if (shown.some((i) => hold[i])) {
      status.textContent = "A hold-out cell entered the discovery list.";
    } else if (shown.some((i) => isRejected(i))) {
      status.textContent = "A rejected ice-sheet cell entered the discovery list.";
    } else if (weightsAreDefault()) {
      status.textContent = "Closest cells outside the Atacama box and the Greenland ice-sheet cluster. " + visibleDiscovery.length + " cells remain.";
    } else {
      const leader = visibleDiscovery.length ? cellId(visibleDiscovery[0]) : "none";
      let text = "The order changed. Rank 1 on this list is " + leader + ". The Atacama box stays off the list.";
      if (lastControl >= 0 && cellId(lastControl) !== META.site_b.cell_id) {
        text += " Best cell inside the hold-out at these weights is " + cellId(lastControl) + ", score " + fmtScore(scores[lastControl]) + ". Site B stays the named control.";
      }
      status.textContent = text;
    }
    list.innerHTML = shown.map((i, rank) => (
      "<li><button type=\"button\" data-i=\"" + i + "\" class=\"" + (i === selected ? "is-selected" : "") + "\">" +
      "<span class=\"pm-rankn\">" + (rank + 1) + "</span>" +
      "<span class=\"pm-id\">" + cellId(i) + "</span>" +
      "<span class=\"pm-list-score\">" + fmtScore(scores[i]) + "</span></button></li>"
    )).join("");
    list.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => select(Number(button.getAttribute("data-i"))));
    });
  }
  const siteA = findCell(META.site_a.lat, META.site_a.lon);
  const siteB = findCell(META.site_b.lat, META.site_b.lon);
  const kind = weightsAreDefault() ? "June three-feature score" : "Score at these weights";
  document.getElementById("pm-site-a-score").textContent = siteA < 0 || !eligible[siteA] ? "Not ranked" : fmtScore(scores[siteA]);
  document.getElementById("pm-site-b-score").textContent = siteB < 0 || !eligible[siteB] ? "Not ranked" : fmtScore(scores[siteB]);
  document.getElementById("pm-site-a-kind").textContent = kind;
  document.getElementById("pm-site-b-kind").textContent = kind;
  document.getElementById("pm-jump-a").classList.toggle("is-selected", selected >= 0 && cellId(selected) === META.site_a.cell_id);
  document.getElementById("pm-jump-b").classList.toggle("is-selected", selected >= 0 && cellId(selected) === META.site_b.cell_id);
}

function reducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function flyTo(latlng, zoom) {
  if (!map) return;
  if (reducedMotion()) map.setView(latlng, zoom, { animate: false });
  else map.flyTo(latlng, zoom, { duration: 0.7 });
}

function flyBounds(bounds) {
  if (!map) return;
  if (reducedMotion()) map.fitBounds(bounds, { animate: false, padding: [24, 24] });
  else map.flyToBounds(bounds, { duration: 0.7, padding: [24, 24] });
}

function select(i) {
  if (i < 0) return;
  selected = i;
  renderDetail(i);
  renderList(readWeights());
  paintMarkers();
  const zoom = cellId(i) === META.site_a.cell_id || cellId(i) === META.site_b.cell_id ? 6 : 5;
  flyTo([lats[i] / 10, lons[i] / 10], zoom);
}

function auditBatch(discovery, control) {
  const note = document.getElementById("pm-check");
  if (!weightsAreDefault()) {
    note.className = "pm-check";
    note.textContent = "Weights changed. The order was recomputed on this page. Published June scores stay " + META.published.site_a + " and " + META.published.site_b + ".";
    return;
  }
  const problems = [];
  META.expected_top.forEach((row, index) => {
    if (!discovery[index] || cellId(discovery[index]) !== row.id || fmtScore(scores[discovery[index]]) !== row.score) {
      const got = discovery[index] ? cellId(discovery[index]) + " " + fmtScore(scores[discovery[index]]) : "missing";
      problems.push("rank " + (index + 1) + " computed " + got + ", batch " + row.id + " " + row.score);
    }
  });
  if (control < 0 || cellId(control) !== META.expected_control.id || fmtScore(scores[control]) !== META.expected_control.score) {
    const got = control < 0 ? "missing" : cellId(control) + " " + fmtScore(scores[control]);
    problems.push("control computed " + got + ", batch " + META.expected_control.id + " " + META.expected_control.score);
  }
  if (problems.length) {
    note.className = "pm-check is-bad";
    note.textContent = "Default order does not match the batch score. " + problems.join("; ") + ".";
    return;
  }
  note.className = "pm-check";
  note.textContent = "June three-feature scores. Site A " + META.published.site_a + ". Site B " + META.published.site_b + ". Site B is the closer partial match.";
}

function rerank() {
  const weights = readWeights();
  const ranked = rankCells(weights);
  visibleDiscovery = ranked.discovery.filter((i) => !isRejected(i));
  lastControl = ranked.control;
  renderList(weights);
  renderDetail(selected);
  drawMarkers();
  auditBatch(ranked.discovery, ranked.control);
}

function scheduleRank() {
  clearTimeout(rankTimer);
  rankTimer = setTimeout(rerank, 80);
}

function ensureMap() {
  if (map || typeof L === "undefined") return;
  if (typeof maplibregl === "undefined" || typeof MaplibreGLLeaflet === "undefined") {
    document.getElementById("pm-check").textContent = "The basemap libraries did not load. The scores below still use the embedded table.";
    return;
  }
  positron = MaplibreGLLeaflet.maplibreGL({ style: LIGHT, attribution: ATTRIB });
  darkMatter = MaplibreGLLeaflet.maplibreGL({ style: DARK, attribution: ATTRIB });
  map = L.map("pm-map", { minZoom: 2, zoomControl: false, worldCopyJump: true, scrollWheelZoom: true, touchZoom: true });
  L.control.zoom({ position: "topright" }).addTo(map);
  map.setView([18, 10], 2);
  positron.addTo(map);
  const box = META.holdout;
  const rect = L.rectangle([[box.lat_min, box.lon_min], [box.lat_max, box.lon_max]], {
    color: "#c47a12",
    weight: 1.5,
    fillColor: "#c47a12",
    fillOpacity: 0.14
  });
  rect.bindTooltip("Atacama hold-out. These cells stay off the discovery list.");
  rect.addTo(map);
  map.invalidateSize();
}

function bindChrome() {
  META.features.forEach((feature) => {
    const input = document.getElementById("w-" + feature.key);
    const num = document.getElementById("wn-" + feature.key);
    if (!input || !num) return;
    input.addEventListener("input", () => {
      num.value = String(Number(input.value));
      scheduleRank();
    });
    num.addEventListener("input", () => {
      const value = Number(num.value);
      if (!Number.isFinite(value)) return;
      input.value = String(Math.min(5, Math.max(0, value)));
      scheduleRank();
    });
    num.addEventListener("change", () => {
      let value = Number(num.value);
      if (!Number.isFinite(value)) value = Number(input.getAttribute("data-default"));
      value = Math.min(5, Math.max(0, Math.round(value * 10) / 10));
      num.value = String(value);
      input.value = String(value);
      scheduleRank();
    });
  });
  document.getElementById("pm-reset").addEventListener("click", () => {
    META.features.forEach((feature) => {
      if (feature.all_null) return;
      const input = document.getElementById("w-" + feature.key);
      const num = document.getElementById("wn-" + feature.key);
      input.value = input.getAttribute("data-default");
      num.value = input.getAttribute("data-default");
    });
    scheduleRank();
  });
  const siteA = () => findCell(META.site_a.lat, META.site_a.lon);
  const siteB = () => findCell(META.site_b.lat, META.site_b.lon);
  document.getElementById("pm-go-world").addEventListener("click", () => flyTo([18, 10], 2));
  document.getElementById("pm-go-rank").addEventListener("click", () => { if (visibleDiscovery.length) select(visibleDiscovery[0]); });
  document.getElementById("pm-go-a").addEventListener("click", () => select(siteA()));
  document.getElementById("pm-go-b").addEventListener("click", () => select(siteB()));
  document.getElementById("pm-jump-a").addEventListener("click", () => select(siteA()));
  document.getElementById("pm-jump-b").addEventListener("click", () => select(siteB()));
  document.getElementById("pm-go-box").addEventListener("click", () => {
    const box = META.holdout;
    flyBounds([[box.lat_min, box.lon_min], [box.lat_max, box.lon_max]]);
  });
  document.getElementById("pm-basemap").addEventListener("click", () => {
    if (!map || !positron || !darkMatter) return;
    darkOn = !darkOn;
    if (darkOn) {
      map.removeLayer(positron);
      darkMatter.addTo(map);
    } else {
      map.removeLayer(darkMatter);
      positron.addTo(map);
    }
    document.getElementById("pm-basemap").textContent = darkOn ? "Light map" : "Dark map";
    document.getElementById("pm-basemap").setAttribute("aria-pressed", darkOn ? "true" : "false");
  });
  window.addEventListener("resize", () => { if (map) map.invalidateSize(); });
}

function setupTour() {
  const steps = [
    { sel: ".pm-sentence", title: "The score", body: "The score is a partial match on measured features, not a probability of mission success." },
    { sel: ".pm-hud", title: "Move the map", body: "World, Rank 1, Site A, Site B, and Hold-out fly the map to that place." },
    { sel: "#pm-selected", title: "Compare a cell", body: "The Earth column changes with the cell, and the Moon and Mars targets stay fixed." },
    { sel: "#pm-ranks", title: "Discovery list", body: "These cells sit outside the Atacama box and outside the rejected Greenland ice sheet." },
    { sel: "#pm-weights", title: "Weights", body: "Open Adjust weights to recompute the order, and a lower score is a closer partial match." }
  ];
  const root = document.getElementById("pm-tour");
  const card = document.getElementById("pm-tour-card");
  const ring = document.getElementById("pm-tour-ring");
  let index = 0;

  function shade(id, left, top, width, height) {
    const el = document.getElementById(id);
    el.style.left = left + "px";
    el.style.top = top + "px";
    el.style.width = width + "px";
    el.style.height = height + "px";
  }

  function place(el) {
    el.scrollIntoView({ block: "nearest", inline: "nearest" });
    const rect = el.getBoundingClientRect();
    const pad = 8;
    const box = {
      left: Math.max(8, rect.left - pad),
      top: Math.max(8, rect.top - pad),
      right: Math.min(window.innerWidth - 8, rect.right + pad),
      bottom: Math.min(window.innerHeight - 8, rect.bottom + pad)
    };
    box.width = Math.max(24, box.right - box.left);
    box.height = Math.max(24, box.bottom - box.top);
    shade("pm-tour-top", 0, 0, window.innerWidth, box.top);
    shade("pm-tour-bottom", 0, box.bottom, window.innerWidth, Math.max(0, window.innerHeight - box.bottom));
    shade("pm-tour-left", 0, box.top, box.left, box.height);
    shade("pm-tour-right", box.right, box.top, Math.max(0, window.innerWidth - box.right), box.height);
    ring.style.left = box.left + "px";
    ring.style.top = box.top + "px";
    ring.style.width = box.width + "px";
    ring.style.height = box.height + "px";
    const cardWidth = Math.min(380, window.innerWidth - 32);
    let left = box.left;
    let top = box.bottom + 12;
    if (top + 180 > window.innerHeight) top = Math.max(12, box.top - 190);
    if (left + cardWidth > window.innerWidth - 12) left = window.innerWidth - cardWidth - 12;
    card.style.width = cardWidth + "px";
    card.style.left = Math.max(12, left) + "px";
    card.style.top = top + "px";
  }

  function show(next) {
    index = next;
    const step = steps[index];
    const el = document.querySelector(step.sel);
    document.getElementById("pm-tour-count").textContent = (index + 1) + " of " + steps.length;
    document.getElementById("pm-tour-title").textContent = step.title;
    document.getElementById("pm-tour-body").textContent = step.body;
    document.getElementById("pm-tour-back").hidden = index === 0;
    document.getElementById("pm-tour-next").textContent = index === steps.length - 1 ? "Done" : "Next";
    if (el) place(el);
    document.getElementById("pm-tour-next").focus();
  }

  function openTour() {
    root.hidden = false;
    show(0);
  }

  function closeTour() {
    root.hidden = true;
    try { localStorage.setItem("pm-tour-seen", "1"); } catch (error) { /* storage can be blocked */ }
  }

  document.getElementById("pm-tour-next").addEventListener("click", () => {
    if (index >= steps.length - 1) closeTour();
    else show(index + 1);
  });
  document.getElementById("pm-tour-back").addEventListener("click", () => { if (index > 0) show(index - 1); });
  document.getElementById("pm-tour-skip").addEventListener("click", closeTour);
  document.getElementById("pm-guide").addEventListener("click", openTour);
  window.addEventListener("resize", () => { if (!root.hidden) show(index); });
  document.addEventListener("keydown", (event) => {
    if (root.hidden) return;
    if (event.key === "Escape") closeTour();
    if (event.key === "ArrowRight") document.getElementById("pm-tour-next").click();
    if (event.key === "ArrowLeft" && index > 0) show(index - 1);
  });
  let seen = false;
  try { seen = localStorage.getItem("pm-tour-seen") === "1"; } catch (error) { seen = false; }
  if (!seen) openTour();
}

async function start() {
  ensureMap();
  if (typeof L === "undefined") {
    document.getElementById("pm-check").textContent = "The basemap library did not load. The scores below still use the embedded table.";
  }
  const gzipBytes = b64ToBytes(B64);
  if (typeof DecompressionStream === "undefined") {
    throw new Error("This browser cannot read the embedded table.");
  }
  const stream = new Blob([gzipBytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  const raw = new Uint8Array(await new Response(stream).arrayBuffer());
  if (raw.byteLength !== META.n * 16) {
    throw new Error("Embedded table length " + raw.byteLength + " does not match " + META.n + " cells.");
  }
  const view = new DataView(raw.buffer, raw.byteOffset, raw.byteLength);
  n = META.n;
  lats = new Int16Array(n);
  lons = new Int16Array(n);
  micros = {
    ndvi_median: new Int32Array(n),
    precip_median_mm_hr: new Int32Array(n),
    lst_night_median_k: new Int32Array(n)
  };
  norms = {
    ndvi_median: new Float64Array(n),
    precip_median_mm_hr: new Float64Array(n),
    lst_night_median_k: new Float64Array(n)
  };
  hold = new Uint8Array(n);
  for (let i = 0; i < n; i += 1) {
    const offset = i * 16;
    lats[i] = view.getInt16(offset, true);
    lons[i] = view.getInt16(offset + 2, true);
    micros.ndvi_median[i] = view.getInt32(offset + 4, true);
    micros.precip_median_mm_hr[i] = view.getInt32(offset + 8, true);
    micros.lst_night_median_k[i] = view.getInt32(offset + 12, true);
    ["ndvi_median", "precip_median_mm_hr", "lst_night_median_k"].forEach((key) => {
      const micro = micros[key][i];
      norms[key][i] = micro === NULL_I32 ? NaN : rawDistance(key, micro / 1000000) / SCALES[key];
    });
    hold[i] = inHoldout(i) ? 1 : 0;
  }
  scores = new Float64Array(n);
  eligible = new Uint8Array(n);
  bindChrome();
  rerank();
  setupTour();
  if (map) map.invalidateSize();
}

start().catch((error) => {
  const note = document.getElementById("pm-check");
  note.className = "pm-check is-bad";
  note.textContent = "The embedded table did not load. " + error.message;
});
</script>
"""


def float_hex(value: float) -> str:
    return np.float64(value).tobytes().hex()


def main() -> None:
    require_inputs()
    targets_text = scorer.TARGETS_MD.read_text(encoding="utf-8")
    bodies = read_bodies(targets_text)
    slope_band = scorer.read_slope_band(targets_text)
    weights_payload = scorer.load_weights()
    weights: dict[str, float] = weights_payload["features"]
    sites = json.loads(SITES_JSON.read_text(encoding="utf-8"))
    for key in ("site_a", "site_b"):
        block = sites.get(key)
        if not isinstance(block, dict) or "name" not in block or "center" not in block:
            stop([f"{SITES_JSON.relative_to(ROOT)} does not name {key}."])
        center = block["center"]
        if "latitude" not in center or "longitude" not in center:
            stop([f"{SITES_JSON.relative_to(ROOT)} {key} has no measured center."])
    frame = pd.read_csv(scorer.FEATURES_CSV)
    required = ["lat_center_deg", "lon_center_deg", *scorer.FEATURE_ORDER]
    missing_columns = [name for name in required if name not in frame.columns]
    if missing_columns:
        stop([f"{scorer.FEATURES_CSV.relative_to(ROOT)} is missing columns: {', '.join(missing_columns)}."])
    duplicate = frame.duplicated(["lat_center_deg", "lon_center_deg"]).any()
    if bool(duplicate):
        stop(["Two land cells share a center. The page was not written, because rank ties would be ambiguous."])

    all_null = {name: bool(frame[name].isna().all()) for name in scorer.FEATURE_ORDER if name in weights}
    active = [
        name
        for name in scorer.FEATURE_ORDER
        if name in weights and weights[name] > 0 and not all_null[name]
    ]
    if not active:
        stop(["No feature has both a positive weight and a measured value. The page was not written."])

    cold_target = None
    if "lst_night_median_k" in active:
        cold_target = float(frame["lst_night_median_k"].quantile(weights_payload["cold_tail_percentile"] / 100.0))
    scales: dict[str, float] = {}
    for name in active:
        distance = scorer.raw_distance(frame[name], name, cold_target, slope_band)
        scale = float(distance.quantile(weights_payload["distance_scale_percentile"] / 100.0))
        if scale <= 0:
            stop([f"The scale for {name} is {scale}. The page was not written."])
        scales[name] = scale

    scored = score_frame(frame, weights, scales, float(cold_target), slope_band, active)
    top, control_row = check_against_batch(scored, active)
    check_site_scores(scored, sites)

    lat_i = pack_tenths(frame["lat_center_deg"])
    lon_i = pack_tenths(frame["lon_center_deg"])
    packed_cols = [pack_micro(frame[name]) for name in MEASURED_PACK]
    record = np.empty(
        len(frame),
        dtype=np.dtype(
            [
                ("lat", "<i2"),
                ("lon", "<i2"),
                ("ndvi", "<i4"),
                ("precip", "<i4"),
                ("lst", "<i4"),
            ],
            align=False,
        ),
    )
    if record.dtype.itemsize != RECORD_BYTES:
        stop([f"Embedded record size is {record.dtype.itemsize}, not {RECORD_BYTES}."])
    record["lat"] = lat_i
    record["lon"] = lon_i
    record["ndvi"] = packed_cols[0]
    record["precip"] = packed_cols[1]
    record["lst"] = packed_cols[2]
    raw = record.tobytes()
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    if gzip.decompress(compressed) != raw:
        stop(["The embedded table did not round-trip through compression."])
    b64 = base64.b64encode(compressed).decode("ascii")

    expected_top = []
    for _, row in top.iterrows():
        expected_top.append(
            {
                "id": scorer.cell_id(float(row["lat_center_deg"]), float(row["lon_center_deg"])),
                "score": formatted_score(row["score"]),
            }
        )
    patch_slope = {}
    for key in ("site_a", "site_b"):
        slope = sites[key].get("features_used", {}).get("slope_median_deg")
        if slope is None:
            continue
        patch_slope[sites[key]["cell_id"]] = scorer.fmt(float(slope))
    meta = {
        "n": int(len(frame)),
        "cold_hex": float_hex(float(cold_target)),
        "scales_hex": {name: float_hex(scales[name]) for name in MEASURED_PACK},
        "slope_band": [slope_band[0], slope_band[1]],
        "holdout": {
            "lat_min": scorer.HOLDOUT_LAT_MIN,
            "lat_max": scorer.HOLDOUT_LAT_MAX,
            "lon_min": scorer.HOLDOUT_LON_MIN,
            "lon_max": scorer.HOLDOUT_LON_MAX,
        },
        "ice_sheet": ICE_SHEET,
        "rejected": list(REJECTED_ICE),
        "features": [
            {
                "key": spec["key"],
                "label": spec["label"],
                "unit": spec["unit"],
                "all_null": bool(all_null[spec["key"]]),
                "weight": weights[spec["key"]],
            }
            for spec in PAGE_FEATURES
            if spec["key"] in weights
        ],
        "expected_top": expected_top,
        "expected_control": {
            "id": scorer.cell_id(float(control_row["lat_center_deg"]), float(control_row["lon_center_deg"])),
            "score": formatted_score(control_row["score"]),
        },
        "published": {
            "site_a": f"{float(sites['site_a']['score']):.6f}",
            "site_b": f"{float(sites['site_b']['score']):.6f}",
        },
        "patch_slope": patch_slope,
        "site_a": {
            "name": sites["site_a"]["name"],
            "cell_id": sites["site_a"]["cell_id"],
            "lat": sites["site_a"]["center"]["latitude"],
            "lon": sites["site_a"]["center"]["longitude"],
        },
        "site_b": {
            "name": sites["site_b"]["name"],
            "cell_id": sites["site_b"]["cell_id"],
            "lat": sites["site_b"]["center"]["latitude"],
            "lon": sites["site_b"]["center"]["longitude"],
        },
    }
    for key in ("site_a", "site_b"):
        lat = meta[key]["lat"]
        lon = meta[key]["lon"]
        found = (lat_i == np.int16(np.rint(lat * 10))) & (lon_i == np.int16(np.rint(lon * 10)))
        if int(found.sum()) != 1:
            stop([f"{key} cell {meta[key]['cell_id']} is not one row of the measurement table."])

    page = page_html(bodies, sites, weights, all_null)
    script = SCRIPT.replace("__META__", json.dumps(meta, ensure_ascii=False)).replace("__B64__", b64)
    if "__B64__" in script or "__META__" in script:
        stop(["A page placeholder was left unfilled."])
    page = page + script + "\n</body>\n</html>\n"
    banned = ("bootstrap", "jquery", "font-awesome", "fontawesome", "glyphicon", "awesome-markers", "user-scalable")
    lowered = page.lower()
    found = [word for word in banned if word in lowered]
    if found:
        stop([f"Generated page still references {', '.join(found)}."])
    if "leaflet" not in lowered or "tiles.openfreemap.org" not in lowered:
        stop(["Generated page is missing Leaflet or the OpenFreeMap basemap."])
    if "filter: invert" in lowered or "hue-rotate" in lowered:
        stop(["Generated page still inverts the basemap."])

    OUT_HTML.parent.mkdir(exist_ok=True)
    OUT_HTML.write_text(page, encoding="utf-8", newline="\n")

    ice = scored["lat_center_deg"].between(ICE_SHEET["lat_min"], ICE_SHEET["lat_max"]) & scored[
        "lon_center_deg"
    ].between(ICE_SHEET["lon_min"], ICE_SHEET["lon_max"])
    kept = scored.loc[scored["eligible"] & ~scored["in_holdout"] & ~ice].sort_values(
        ["score", "lat_center_deg", "lon_center_deg"],
        ascending=[True, True, True],
        kind="mergesort",
    )
    print(f"Wrote {OUT_HTML}")
    print(f"Embedded cells: {len(frame)}")
    print(f"HTML bytes: {OUT_HTML.stat().st_size}")
    print("Batch discovery, including the rejected ice-sheet cells:")
    for row in expected_top:
        print(f"  {row['id']} {row['score']}")
    print("Page discovery list, ice-sheet cluster excluded:")
    for _, row in kept.head(5).iterrows():
        print(
            " ",
            scorer.cell_id(float(row["lat_center_deg"]), float(row["lon_center_deg"])),
            formatted_score(row["score"]),
        )
    print(f"Control: {meta['expected_control']['id']} {meta['expected_control']['score']}")
    print(f"Moon: {bodies['moon_name']} | {bodies['moon_center']}")
    print(f"Mars: {bodies['mars_name']} | {bodies['mars_center']}")


if __name__ == "__main__":
    main()
