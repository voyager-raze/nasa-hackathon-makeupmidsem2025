"""Embed the land-cell table in web/index.html and build the judge-facing map.

Reads data/processed/features.csv, notes/weights.json, notes/targets.md,
notes/features.md, and results/sites.json. Uses the same distance rules as
src/score.py. Writes web/index.html only. Does not rank by editing
results/top5.csv, and does not fill a blank measurement.

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

import folium
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import score as scorer  # noqa: E402

SITES_JSON = ROOT / "results" / "sites.json"
OUT_HTML = ROOT / "web" / "index.html"

NULL_I32 = np.int32(-2147483648)
RECORD_BYTES = 16
FEATURE_UNITS = {
    "slope_median_deg": "degrees",
    "ndvi_median": "NDVI (native index)",
    "precip_median_mm_hr": "mm/hr",
    "lst_night_median_k": "kelvin",
}
MEASURED_PACK = ("ndvi_median", "precip_median_mm_hr", "lst_night_median_k")


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


def build_map(holdout_name: str) -> tuple[str, str]:
    earth = folium.Map(
        location=[18, 10],
        zoom_start=2,
        tiles="OpenStreetMap",
        control_scale=True,
        min_zoom=2,
    )
    folium.Rectangle(
        bounds=[
            [scorer.HOLDOUT_LAT_MIN, scorer.HOLDOUT_LON_MIN],
            [scorer.HOLDOUT_LAT_MAX, scorer.HOLDOUT_LON_MAX],
        ],
        color="#e0a15a",
        weight=1.5,
        fill=True,
        fill_color="#e0a15a",
        fill_opacity=0.14,
        tooltip=(
            f"{holdout_name} hold-out. Cells in this box are the famous control. "
            "They are scored with the same function and do not enter the discovery list."
        ),
    ).add_to(earth)
    return earth.get_name(), earth.get_root().render()


def weight_controls(weights: dict[str, float], all_null: dict[str, bool]) -> str:
    blocks = []
    for name in scorer.FEATURE_ORDER:
        if name not in weights:
            continue
        unit = FEATURE_UNITS[name]
        value = weights[name]
        if all_null[name]:
            blocks.append(
                f"""<label class="pm-weight is-disabled">
                  <span class="pm-weight-name">{html.escape(name)}</span>
                  <span class="pm-weight-val">no data</span>
                  <span class="pm-unit">{html.escape(unit)} · blank on every land cell · not applied</span>
                  <input id="w-{html.escape(name)}" type="range" min="0" max="5" step="0.1" value="{value:g}" disabled>
                </label>"""
            )
            continue
        blocks.append(
            f"""<label class="pm-weight">
              <span class="pm-weight-name">{html.escape(name)}</span>
              <input class="pm-num" id="wn-{html.escape(name)}" type="number" min="0" max="5" step="0.1" value="{value:g}" inputmode="decimal">
              <span class="pm-unit">{html.escape(unit)}</span>
              <input id="w-{html.escape(name)}" type="range" min="0" max="5" step="0.1" value="{value:g}" data-default="{value:g}">
            </label>"""
        )
    return "\n".join(blocks)


def page_chrome(
    map_name: str,
    bodies: dict[str, str],
    sites: dict,
    weights: dict[str, float],
    all_null: dict[str, bool],
    scales: dict[str, float],
    cold_target: float,
    slope_band: tuple[float, float],
    n_cells: int,
) -> str:
    low, high = slope_band
    site_a = sites["site_a"]
    site_b = sites["site_b"]
    a_slope = site_a["features_used"]["slope_median_deg"]
    b_slope = site_b["features_used"]["slope_median_deg"]
    return f"""
    <div class="pm-app">
      <header class="pm-banner">
        <div class="pm-brand">
          <h1>Partial Match</h1>
        </div>
        <p class="pm-sentence">The score is a partial match on measured features, not a probability of mission success.</p>
        <div class="pm-readout">
          <p id="pm-check">Reading the embedded table.</p>
          <button type="button" id="pm-guide" class="pm-btn">Guide</button>
        </div>
      </header>
      <div class="pm-map-cell">
        <div class="folium-map" id="{map_name}"></div>
        <p id="pm-cursor" class="pm-cursor">—</p>
        <div class="pm-hud">
          <button type="button" id="pm-go-world" class="pm-btn">World</button>
          <button type="button" id="pm-go-rank" class="pm-btn">Rank 1</button>
          <button type="button" id="pm-go-a" class="pm-btn">Site A</button>
          <button type="button" id="pm-go-b" class="pm-btn">Site B</button>
          <button type="button" id="pm-go-box" class="pm-btn">Hold-out</button>
          <button type="button" id="pm-basemap" class="pm-btn">Dark map</button>
        </div>
        <div class="pm-legend">
          <div><i class="swatch rank"></i> Discovery rank, top 5</div>
          <div><i class="swatch a"></i> Site A · {html.escape(site_a["name"])}</div>
          <div><i class="swatch b"></i> Site B · {html.escape(site_b["name"])}</div>
          <div><i class="swatch box"></i> Atacama hold-out</div>
        </div>
      </div>
      <aside class="pm-side">
        <section class="pm-stats" aria-label="Site scores">
          <button type="button" id="pm-jump-a" class="pm-stat">
            <span class="pm-kicker">Site A · {html.escape(site_a["country"])}</span>
            <strong>{html.escape(site_a["name"])}</strong>
            <span class="pm-coord">{html.escape(site_a["cell_id"])}</span>
            <span id="pm-site-a-score" class="pm-stat-score">—</span>
          </button>
          <button type="button" id="pm-jump-b" class="pm-stat">
            <span class="pm-kicker">Site B · control · {html.escape(site_b["country"])}</span>
            <strong>{html.escape(site_b["name"])}</strong>
            <span class="pm-coord">{html.escape(site_b["cell_id"])}</span>
            <span id="pm-site-b-score" class="pm-stat-score">—</span>
          </button>
        </section>
        <p class="pm-hint">Zoom slope {scorer.fmt(float(a_slope))}° at Site A and {scorer.fmt(float(b_slope))}° at Site B. Those are patch measurements, not the grid column, and the score leaves them out. <span id="pm-control-now"></span></p>
        <section id="pm-weights">
          <div class="pm-section-head">
            <h2>Weights</h2>
            <button type="button" id="pm-reset" class="pm-btn">Reset</button>
          </div>
          <p class="pm-hint">Defaults from <code>notes/weights.json</code>. A change recomputes the order here. It does not rebuild the file. Lower score is a closer partial match.</p>
          {weight_controls(weights, all_null)}
        </section>
        <section>
          <div class="pm-section-head">
            <h2>Discovery</h2>
            <label class="pm-show">Show
              <select id="pm-show">
                <option value="5">5</option>
                <option value="8" selected>8</option>
                <option value="12">12</option>
              </select>
            </label>
          </div>
          <p id="pm-status" class="pm-hint">Cells outside the Atacama box.</p>
          <ol id="pm-ranks" class="pm-ranks"></ol>
        </section>
        <section>
          <h2>Selected cell</h2>
          <div id="pm-detail"></div>
        </section>
      </aside>
      <section class="pm-bodies" aria-label="Moon, Mars, and the score">
        <article class="pm-body">
          <p class="pm-kicker">Moon · not on the Earth map</p>
          <h2>{html.escape(bodies["moon_name"])}</h2>
          <p class="pm-coord">{html.escape(bodies["moon_center"])}</p>
        </article>
        <article class="pm-body">
          <p class="pm-kicker">Mars · not on the Earth map</p>
          <h2>{html.escape(bodies["mars_name"])}</h2>
          <p class="pm-coord">{html.escape(bodies["mars_center"])}</p>
          <p class="pm-hint">Minerals, an ice-map raster, and a dust index are blank in the target notes.</p>
        </article>
        <article class="pm-body">
          <p class="pm-kicker">Score</p>
          <p>Mean of weight × distance / scale, using only measured features. Scales stay fixed while a weight moves.</p>
          <p class="pm-coord">NDVI {scorer.fmt(scales["ndvi_median"])} · precip {scorer.fmt(scales["precip_median_mm_hr"])} mm/hr · night LST {scorer.fmt(scales["lst_night_median_k"])} K above {scorer.fmt(cold_target)} K</p>
          <p class="pm-hint">Slope band {low:.1f}–{high:.1f}°. No grid slope, so that term is not applied. Gravity, vacuum, thin air, and radiation are not in this score. {n_cells} land cells are embedded.</p>
        </article>
      </section>
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
<title>Partial Match map</title>
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
  html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; background: var(--bg); color: var(--ink); }
  body, button, input, select { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 15px; line-height: 1.45; }
  button, input, select { color: inherit; }
  h1, h2, p { margin: 0; }
  code { font-family: "Cascadia Mono", Consolas, monospace; font-size: 0.9em; color: inherit; background: transparent; }
  .pm-app { height: 100%; display: grid; grid-template-columns: minmax(0, 1fr) 400px; grid-template-rows: auto minmax(0, 1fr) auto; background: var(--bg); }
  .pm-banner { grid-column: 1 / -1; display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; column-gap: 24px; height: 64px; padding: 0 20px; box-sizing: border-box; overflow: hidden; background: var(--card); border-bottom: 1px solid var(--line); }
  .pm-brand h1 { font-size: 22px; font-weight: 650; letter-spacing: -0.02em; white-space: nowrap; }
  .pm-kicker { font-size: 12px; color: var(--muted); }
  .pm-sentence { font-size: 15px; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pm-readout { display: flex; align-items: center; gap: 12px; }
  .pm-readout p { font-size: 12.5px; color: var(--muted); white-space: nowrap; }
  .pm-check.is-bad { color: var(--bad); }
  .pm-map-cell { position: relative; min-height: 0; background: #d7e2ea; }
  .pm-map-cell .folium-map { position: absolute !important; inset: 0; width: 100% !important; height: 100% !important; }
  .leaflet-container img, .leaflet-pane img { max-width: none !important; max-height: none !important; }
  .leaflet-bar { border: 0 !important; box-shadow: 0 4px 16px rgba(28, 36, 48, 0.12) !important; border-radius: 10px !important; overflow: hidden; }
  .leaflet-bar a, .leaflet-bar a:hover { background: #fff !important; color: var(--ink) !important; border-bottom-color: var(--line) !important; width: 32px; height: 32px; line-height: 32px; }
  .pm-map-cell.is-dark .leaflet-tile-pane { filter: invert(1) hue-rotate(180deg) saturate(0.25) brightness(0.92) contrast(1.05); }
  .leaflet-control-attribution, .leaflet-control-scale-line { background: rgba(255, 255, 255, 0.9); color: var(--muted); }
  .leaflet-control-attribution a { color: var(--blue); }
  .pm-hud, .pm-legend, .pm-cursor { position: absolute; z-index: 500; }
  .pm-cursor { top: 12px; left: 52px; width: 196px; height: 32px; margin: 0; box-sizing: border-box; display: flex; align-items: center; justify-content: center; padding: 0 12px; background: rgba(255, 255, 255, 0.96); border: 1px solid var(--line); border-radius: 999px; box-shadow: 0 4px 16px rgba(28, 36, 48, 0.08); font-family: "Cascadia Mono", Consolas, monospace; font-variant-numeric: tabular-nums; font-size: 13px; line-height: 1; color: var(--ink); pointer-events: none; }
  .pm-hud { top: 12px; right: 12px; display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; max-width: calc(100% - 260px); }
  .pm-legend { left: 12px; bottom: 46px; display: grid; gap: 6px; padding: 10px 12px; background: rgba(255, 255, 255, 0.96); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 8px 24px rgba(28, 36, 48, 0.08); font-size: 13px; }
  .pm-legend div { display: flex; align-items: center; gap: 8px; }
  .swatch { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
  .swatch.rank { background: var(--blue); }
  .swatch.a { background: var(--green); }
  .swatch.b { background: var(--amber); }
  .swatch.box { background: transparent; border: 1.5px solid var(--amber); border-radius: 2px; }
  .pm-btn { background: #fff; color: var(--ink); border: 1px solid var(--line); padding: 6px 12px; font-size: 13px; cursor: pointer; border-radius: 999px; white-space: nowrap; box-shadow: 0 2px 8px rgba(28, 36, 48, 0.06); }
  .pm-btn:hover { border-color: #b9d4f6; background: var(--blue-soft); color: var(--blue); }
  .pm-side { grid-column: 2; grid-row: 2 / span 2; overflow: auto; padding: 16px 16px 28px; background: var(--bg); }
  .pm-side h2 { font-size: 16px; font-weight: 650; letter-spacing: -0.01em; }
  .pm-section-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 18px 0 8px; }
  .pm-side section > h2 { margin: 18px 0 8px; }
  .pm-hint { color: var(--muted); font-size: 13px; margin: 0 0 10px; }
  .pm-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .pm-stat { text-align: left; background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 12px; cursor: pointer; display: grid; gap: 2px; box-shadow: 0 1px 2px rgba(28, 36, 48, 0.04); }
  .pm-stat:hover { border-color: #b9d4f6; }
  .pm-stat strong { font-size: 15px; font-weight: 650; }
  .pm-stat-score { font-variant-numeric: tabular-nums; font-size: 18px; font-weight: 650; color: var(--blue); margin-top: 4px; }
  .pm-weight { display: grid; grid-template-columns: 1fr auto; grid-template-areas: "name val" "unit unit" "slider slider"; gap: 2px 8px; margin: 12px 0; padding: 10px 12px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; }
  .pm-weight-name { grid-area: name; font-size: 13px; font-weight: 650; }
  .pm-unit { grid-area: unit; color: var(--muted); font-size: 12.5px; }
  .pm-weight input[type="range"] { grid-area: slider; width: 100%; margin: 4px 0 0; accent-color: var(--blue); }
  .pm-num, .pm-weight-val { grid-area: val; width: 4.4rem; text-align: right; font-variant-numeric: tabular-nums; font-size: 14px; background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 4px 8px; }
  .pm-weight.is-disabled { background: #f8f5ef; }
  .pm-weight.is-disabled .pm-weight-val { color: var(--amber); border-color: transparent; background: transparent; width: auto; font-weight: 650; }
  .pm-show { color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 6px; }
  .pm-show select { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 4px 8px; }
  .pm-ranks { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  .pm-ranks button { width: 100%; display: grid; grid-template-columns: 1.6rem 1fr auto; gap: 8px; align-items: center; text-align: left; background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 8px 10px; cursor: pointer; }
  .pm-ranks button:hover { border-color: #b9d4f6; }
  .pm-ranks button.is-selected { background: var(--blue-soft); border-color: #b9d4f6; }
  .pm-rankn { color: var(--muted); font-variant-numeric: tabular-nums; }
  .pm-id, .pm-coord { font-family: "Cascadia Mono", Consolas, monospace; font-size: 13px; }
  .pm-score { font-variant-numeric: tabular-nums; font-weight: 650; color: var(--blue); }
  .pm-table { width: 100%; border-collapse: collapse; font-size: 13px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
  .pm-table th { color: var(--muted); font-weight: 600; font-size: 12px; }
  .pm-table th, .pm-table td { border-bottom: 1px solid var(--line); padding: 8px 8px 8px 0; text-align: left; vertical-align: top; }
  .pm-table th:first-child, .pm-table td:first-child { padding-left: 12px; }
  .pm-table td:nth-child(n+2) { font-variant-numeric: tabular-nums; }
  .pm-blank { min-height: 1.1em; }
  .pm-role { margin-bottom: 8px; }
  .pm-bodies { grid-column: 1; grid-row: 3; display: grid; grid-template-columns: 1fr 1fr 1.15fr; gap: 10px; padding: 10px 12px; background: var(--bg); }
  .pm-body { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; }
  .pm-body h2 { font-size: 15px; font-weight: 650; margin: 2px 0 4px; }
  .pm-body p { font-size: 13px; }
  .pm-pin { background: transparent; border: 0; }
  .pm-pin span { display: flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%; background: var(--blue); color: white; font-size: 12px; font-weight: 700; border: 2px solid white; box-shadow: 0 2px 8px rgba(28, 36, 48, 0.25); }
  .pm-pin.site-a span { background: var(--green); }
  .pm-pin.site-b span { background: var(--amber); }
  .pm-readout .pm-btn { margin-bottom: 6px; }
  .pm-btn-primary { background: var(--blue); color: #fff; border-color: var(--blue); box-shadow: none; }
  .pm-btn-primary:hover { background: #185fbe; color: #fff; border-color: #185fbe; }
  .pm-tour[hidden] { display: none; }
  .pm-tour-shade { position: fixed; background: rgba(22, 28, 36, 0.46); z-index: 2100; }
  .pm-tour-ring { position: fixed; z-index: 2101; border: 2px solid var(--blue); border-radius: 14px; box-shadow: 0 0 0 4px rgba(29, 111, 219, 0.18); pointer-events: none; }
  .pm-tour-card { position: fixed; z-index: 2102; width: min(380px, calc(100vw - 32px)); background: #fff; color: var(--ink); border-radius: 16px; padding: 18px 18px 14px; box-shadow: 0 18px 50px rgba(22, 28, 36, 0.22); }
  .pm-tour-card h2 { font-size: 18px; margin: 4px 0 8px; }
  .pm-tour-card p { font-size: 14.5px; }
  .pm-tour-actions { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 16px; }
  .pm-tour-nav { display: flex; gap: 8px; }
  @media (max-width: 980px) {
    html, body { height: auto; overflow: auto; }
    .pm-app { height: auto; grid-template-columns: 1fr; grid-template-rows: auto 68vh auto auto; }
    .pm-banner { grid-template-columns: 1fr; row-gap: 6px; }
    .pm-readout { text-align: left; }
    .pm-hud { left: 12px; right: auto; justify-content: flex-start; }
    .pm-side { grid-column: 1; grid-row: 4; }
    .pm-bodies { grid-column: 1; grid-row: 3; grid-template-columns: 1fr; }
    .pm-stats { grid-template-columns: 1fr; }
  }
</style>
"""

SCRIPT = r"""
<script>
const META = __META__;
const MAP_NAME = "__MAP_NAME__";
const B64 = "__B64__";
const NULL_I32 = -2147483648;

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
  if (name === "slope_median_deg") {
    return Math.max(SLOPE_LOW - value, 0) + Math.max(value - SLOPE_HIGH, 0);
  }
  return NaN;
}

let lats, lons, micros, norms, hold, n;
let scores, eligible;
let selected = -1;
let pins = null;
let map = null;
let lastLeader = -1;
let lastDiscovery = [];
let lastControl = -1;
let lastWeights = null;
let rankTimer = 0;
let darkMap = false;

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

function findCell(lat, lon) {
  const la = tenths(lat);
  const lo = tenths(lon);
  for (let i = 0; i < n; i += 1) {
    if (lats[i] === la && lons[i] === lo) return i;
  }
  return -1;
}

function activeFeatures(weights) {
  return META.features.filter((feature) => !feature.all_null && weights[feature.key] > 0);
}

function readWeights() {
  const weights = {};
  META.features.forEach((feature) => {
    const input = document.getElementById("w-" + feature.key);
    if (feature.all_null || !input || input.disabled) {
      weights[feature.key] = 0;
      return;
    }
    weights[feature.key] = Number(input.value);
  });
  return weights;
}

function updateReadouts() {
  META.features.forEach((feature) => {
    if (feature.all_null) return;
    const input = document.getElementById("w-" + feature.key);
    const num = document.getElementById("wn-" + feature.key);
    if (!input || !num || document.activeElement === num) return;
    num.value = String(Number(input.value));
  });
}

function fmtRaw(value) {
  if (!Number.isFinite(value)) return "";
  const micro = Math.round(value * 1000000);
  return formatMeasured(micro);
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
  if (!use.length) {
    return { discovery: [], control: -1, weights };
  }
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
  return { discovery, control, weights };
}

function marker(lat, lon, options, text) {
  const point = L.circleMarker([lat, lon], options);
  point.bindTooltip(text, { sticky: true });
  return point;
}

function tagMarker(i, label, className, tip) {
  const icon = L.divIcon({
    className: "pm-pin " + className,
    html: "<span>" + label + "</span>",
    iconSize: [22, 22],
    iconAnchor: [11, 11]
  });
  const point = L.marker([lats[i] / 10, lons[i] / 10], { icon: icon, zIndexOffset: className ? 700 : 500 });
  point.bindTooltip(tip);
  point.on("click", () => select(i));
  point.addTo(pins);
}

function drawMarkers(discovery) {
  if (!map || typeof L === "undefined") return;
  if (!pins) pins = L.layerGroup().addTo(map);
  pins.clearLayers();
  discovery.slice(0, 5).forEach((i, rank) => {
    tagMarker(i, String(rank + 1), "", "Discovery " + (rank + 1) + " · " + cellId(i) + " · " + fmtScore(scores[i]));
  });
  const siteA = findCell(META.site_a.lat, META.site_a.lon);
  const siteB = findCell(META.site_b.lat, META.site_b.lon);
  if (siteA >= 0) tagMarker(siteA, "A", "site-a", "Site A · " + META.site_a.name);
  if (siteB >= 0) tagMarker(siteB, "B", "site-b", "Site B · " + META.site_b.name + " · control");
  if (discovery.length) lastLeader = discovery[0];
  map.invalidateSize();
}

function renderList(discovery, control, weights) {
  const list = document.getElementById("pm-ranks");
  const status = document.getElementById("pm-status");
  const use = activeFeatures(weights);
  if (!use.length) {
    list.innerHTML = "";
    status.textContent = "No measured feature has a positive weight. Nothing is ranked.";
    document.getElementById("pm-control-now").textContent = "";
    return;
  }
  const limit = Number(document.getElementById("pm-show").value) || 8;
  const shown = discovery.slice(0, limit);
  const defaultIds = META.expected_top.map((row) => row.id).join(",");
  const nowIds = shown.slice(0, 5).map(cellId).join(",");
  const leaderWas = META.expected_top[0].id;
  const leaderNow = discovery.length ? cellId(discovery[0]) : "none";
  let orderNote = "Default weights. Rank 1 is " + leaderWas + ".";
  if (nowIds !== defaultIds) {
    orderNote = "The order changed. Rank 1 was " + leaderWas + ". It is now " + leaderNow + ".";
  }
  status.textContent = orderNote + " " + discovery.length + " discovery cells. The Atacama box is excluded.";
  list.innerHTML = shown.map((i, rank) => (
    "<li><button type=\"button\" data-i=\"" + i + "\" class=\"" + (i === selected ? "is-selected" : "") + "\">" +
    "<span class=\"pm-rankn\">" + (rank + 1) + "</span>" +
    "<span class=\"pm-id\">" + cellId(i) + "</span>" +
    "<span class=\"pm-score\">" + fmtScore(scores[i]) + "</span></button></li>"
  )).join("");
  list.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => select(Number(button.getAttribute("data-i"))));
  });
  const controlLine = document.getElementById("pm-control-now");
  if (control < 0) {
    controlLine.textContent = "No eligible control cell inside the Atacama box at these weights.";
  } else {
    const same = cellId(control) === META.site_b.cell_id;
    controlLine.textContent = same
      ? "Site B is the best cell inside the hold-out at these weights. It is not on the discovery list."
      : "Best cell inside the hold-out at these weights: " + cellId(control) + ", score " + fmtScore(scores[control]) + ". Site B remains the named control and is scored with the same function. Neither is on the discovery list.";
  }
  const siteA = findCell(META.site_a.lat, META.site_a.lon);
  const siteB = findCell(META.site_b.lat, META.site_b.lon);
  document.getElementById("pm-site-a-score").textContent = siteScoreText(siteA);
  document.getElementById("pm-site-b-score").textContent = siteScoreText(siteB);
}

function siteScoreText(i) {
  if (i < 0 || !eligible[i]) return "—";
  return fmtScore(scores[i]);
}

function renderDetail(i) {
  const root = document.getElementById("pm-detail");
  if (i < 0) {
    root.textContent = "Select a cell.";
    return;
  }
  const weights = readWeights();
  const nulls = [];
  const rows = META.features.map((feature) => {
    let micro = NULL_I32;
    if (!feature.all_null) micro = micros[feature.key][i];
    const blank = micro === NULL_I32;
    if (blank) nulls.push(feature.key);
    const shown = blank ? "" : formatMeasured(micro);
    let distance = "";
    let term = "";
    let state = "in the score";
    if (feature.all_null) state = "no data";
    else if (blank) state = "blank on this cell";
    else {
      const raw = rawDistance(feature.key, micro / 1000000);
      distance = fmtRaw(raw);
      if (weights[feature.key] <= 0) state = "weight is 0";
      else term = (weights[feature.key] * raw / SCALES[feature.key]).toFixed(4);
    }
    const cell = (value) => "<td class=\"" + (value === "" ? "pm-blank" : "") + "\"" + (value === "" ? " title=\"blank\"" : "") + ">" + esc(value) + "</td>";
    return "<tr><td><code>" + esc(feature.key) + "</code><div class=\"pm-hint\">" + esc(feature.unit) + "</div></td>" +
      cell(shown) + cell(distance) + cell(term) + "<td>" + state + "</td></tr>";
  }).join("");
  let role = "Discovery cell";
  if (hold[i]) role = "Inside the Atacama hold-out. Scored as a control cell, not a discovery winner.";
  if (cellId(i) === META.site_a.cell_id) role = "Site A · " + META.site_a.name;
  if (cellId(i) === META.site_b.cell_id) role = "Site B · " + META.site_b.name + ". Famous control.";
  const scoreLine = eligible[i]
    ? "Score " + fmtScore(scores[i]) + "."
    : "Not ranked. A feature with a positive weight is blank on this cell, so the cell is left out.";
  root.innerHTML =
    "<p><strong>" + esc(cellId(i)) + "</strong> · " + (lats[i] / 10).toFixed(1) + "°, " + (lons[i] / 10).toFixed(1) + "°</p>" +
    "<p>" + esc(role) + " " + esc(scoreLine) + "</p>" +
    "<table class=\"pm-table\"><thead><tr><th>Feature</th><th>Measurement</th><th>Distance</th><th>Term</th><th></th></tr></thead><tbody>" +
    rows + "</tbody></table>" +
    "<p class=\"pm-hint\">Null on this cell: " + (nulls.length ? nulls.map(esc).join(", ") : "none") + ". A blank measurement is left blank. A term is weight × distance / scale.</p>";
}

function select(i, zoom) {
  selected = i;
  renderDetail(i);
  document.querySelectorAll(".pm-ranks button").forEach((button) => {
    button.classList.toggle("is-selected", Number(button.getAttribute("data-i")) === i);
  });
  if (!map) return;
  const lat = lats[i] / 10;
  const lon = lons[i] / 10;
  if (zoom) map.flyTo([lat, lon], zoom, { duration: 0.45 });
  else map.panTo([lat, lon]);
}

function checkDefault(discovery, control) {
  const note = document.getElementById("pm-check");
  const problems = [];
  META.expected_top.forEach((row, index) => {
    if (!discovery[index] || cellId(discovery[index]) !== row.id || fmtScore(scores[discovery[index]]) !== row.score) {
      const got = discovery[index] ? cellId(discovery[index]) + " " + fmtScore(scores[discovery[index]]) : "missing";
      problems.push("rank " + (index + 1) + " computed " + got + ", batch " + row.id + " " + row.score);
    }
    if (discovery[index] && hold[discovery[index]]) problems.push(row.id + " is inside the hold-out");
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
  note.textContent = "Batch order · rank 1 " + META.expected_top[0].id;
}

function rerank() {
  const weights = readWeights();
  const ranked = rankCells(weights);
  if (selected < 0 && ranked.discovery.length) selected = ranked.discovery[0];
  lastDiscovery = ranked.discovery;
  lastControl = ranked.control;
  lastWeights = weights;
  renderList(ranked.discovery, ranked.control, weights);
  renderDetail(selected);
  drawMarkers(ranked.discovery);
  const defaults = META.features.every((feature) => {
    if (feature.all_null) return true;
    const input = document.getElementById("w-" + feature.key);
    return Number(input.value) === Number(input.getAttribute("data-default"));
  });
  if (defaults) checkDefault(ranked.discovery, ranked.control);
  else {
    const note = document.getElementById("pm-check");
    note.className = "pm-check";
    note.textContent = "Weights changed · order recomputed in the browser";
  }
}

function scheduleRank() {
  updateReadouts();
  clearTimeout(rankTimer);
  rankTimer = setTimeout(rerank, 80);
}

async function start() {
  const gzipBytes = b64ToBytes(B64);
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
  map = window[MAP_NAME];
  if (map) map.invalidateSize();
  META.features.forEach((feature) => {
    const input = document.getElementById("w-" + feature.key);
    if (!input || input.disabled) return;
    input.addEventListener("input", scheduleRank);
    const num = document.getElementById("wn-" + feature.key);
    if (!num) return;
    num.addEventListener("change", () => {
      let value = Number(num.value);
      if (!Number.isFinite(value)) value = Number(input.getAttribute("data-default"));
      value = Math.min(5, Math.max(0, Math.round(value * 10) / 10));
      num.value = String(value);
      input.value = String(value);
      scheduleRank();
    });
  });
  document.getElementById("pm-show").addEventListener("change", () => {
    if (lastWeights) renderList(lastDiscovery, lastControl, lastWeights);
  });
  document.getElementById("pm-reset").addEventListener("click", () => {
    META.features.forEach((feature) => {
      if (feature.all_null) return;
      const input = document.getElementById("w-" + feature.key);
      input.value = input.getAttribute("data-default");
      const num = document.getElementById("wn-" + feature.key);
      if (num) num.value = input.getAttribute("data-default");
    });
    if (map) map.setView([18, 10], 2);
    scheduleRank();
  });
  const siteA = () => findCell(META.site_a.lat, META.site_a.lon);
  const siteB = () => findCell(META.site_b.lat, META.site_b.lon);
  document.getElementById("pm-go-world").addEventListener("click", () => map && map.setView([18, 10], 2));
  document.getElementById("pm-go-rank").addEventListener("click", () => { if (lastLeader >= 0) select(lastLeader, 4); });
  document.getElementById("pm-go-a").addEventListener("click", () => { const i = siteA(); if (i >= 0) select(i, 5); });
  document.getElementById("pm-go-b").addEventListener("click", () => { const i = siteB(); if (i >= 0) select(i, 5); });
  document.getElementById("pm-jump-a").addEventListener("click", () => { const i = siteA(); if (i >= 0) select(i, 5); });
  document.getElementById("pm-jump-b").addEventListener("click", () => { const i = siteB(); if (i >= 0) select(i, 5); });
  document.getElementById("pm-go-box").addEventListener("click", () => {
    if (!map) return;
    const box = META.holdout;
    map.flyTo([(box.lat_min + box.lat_max) / 2, (box.lon_min + box.lon_max) / 2], 5, { duration: 0.45 });
  });
  document.getElementById("pm-basemap").addEventListener("click", () => {
    darkMap = !darkMap;
    document.querySelector(".pm-map-cell").classList.toggle("is-dark", darkMap);
    document.getElementById("pm-basemap").textContent = darkMap ? "Light map" : "Dark map";
  });
  if (map) {
    map.on("mousemove", (event) => {
      document.getElementById("pm-cursor").textContent =
        event.latlng.lat.toFixed(3) + "°, " + event.latlng.lng.toFixed(3) + "°";
    });
    map.on("mouseout", () => { document.getElementById("pm-cursor").textContent = "—"; });
  }
  rerank();
  setupTour();
}

function setupTour() {
  const steps = [
    {
      sel: ".pm-sentence",
      title: "The score",
      body: "This is a partial match on measured features. It is not a probability of mission success. A lower score is a closer match."
    },
    {
      sel: ".pm-legend",
      title: "What is on the map",
      body: "Blue numbers are the top discovery cells. Green A is Site A. Amber B is Site B, the control. The box is the Atacama hold-out. Those cells are scored the same way and do not become the discovery winner. The buttons above move the view."
    },
    {
      sel: "#pm-weights",
      title: "Change a weight",
      body: "Move a slider, or type a number from 0 to 5. The list updates in this page. You do not rebuild the file. Slope says no data, so that control stays off and is not used."
    },
    {
      sel: "#pm-ranks",
      title: "Open a cell",
      body: "Click a row. The table below shows the measurement, the distance, and the term. A blank stays blank. A measured zero stays zero."
    },
    {
      sel: ".pm-bodies",
      title: "Moon and Mars",
      body: "These cards are the locked targets. Their coordinates are not drawn on the Earth map. The score card lists the fixed scales."
    }
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
    if (top + 220 > window.innerHeight) top = Math.max(12, box.top - 230);
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
        "features": [
            {
                "key": name,
                "unit": FEATURE_UNITS[name],
                "all_null": bool(all_null[name]),
                "weight": weights[name],
            }
            for name in scorer.FEATURE_ORDER
            if name in weights
        ],
        "expected_top": expected_top,
        "expected_control": {
            "id": scorer.cell_id(float(control_row["lat_center_deg"]), float(control_row["lon_center_deg"])),
            "score": formatted_score(control_row["score"]),
        },
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

    map_name, folium_html = build_map(scorer.HOLDOUT_NAME)
    chrome = page_chrome(
        map_name,
        bodies,
        sites,
        weights,
        all_null,
        scales,
        float(cold_target),
        slope_band,
        len(frame),
    )
    map_div = f'<div class="folium-map" id="{map_name}" ></div>'
    if map_div not in folium_html:
        stop(["Folium did not emit the Earth map container. web/index.html was not written."])
    page = folium_html.replace("</head>", STYLE + "\n</head>", 1)
    page = page.replace(map_div, chrome, 1)
    script = (
        SCRIPT.replace("__META__", json.dumps(meta, ensure_ascii=False))
        .replace("__MAP_NAME__", map_name)
        .replace("__B64__", b64)
    )
    page = page.replace("</html>", script + "\n</html>", 1)
    OUT_HTML.parent.mkdir(exist_ok=True)
    OUT_HTML.write_text(page, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT_HTML}")
    print(f"Embedded cells: {len(frame)}")
    print(f"HTML bytes: {OUT_HTML.stat().st_size}")
    print("Default discovery:")
    for row in expected_top:
        print(f"  {row['id']} {row['score']}")
    print(f"Control: {meta['expected_control']['id']} {meta['expected_control']['score']}")
    print(f"Moon: {bodies['moon_name']} | {bodies['moon_center']}")
    print(f"Mars: {bodies['mars_name']} | {bodies['mars_center']}")


if __name__ == "__main__":
    main()
