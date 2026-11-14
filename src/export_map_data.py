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
        color="#8a5a2b",
        weight=2,
        fill=True,
        fill_color="#c4a574",
        fill_opacity=0.28,
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
                  <span class="pm-weight-name">{html.escape(name)} <span class="pm-unit">{html.escape(unit)}</span></span>
                  <input id="w-{html.escape(name)}" type="range" min="0" max="5" step="0.1" value="{value:g}" disabled>
                  <span class="pm-weight-val">no data</span>
                </label>
                <p class="pm-hint">No data. The column is blank on every land cell, so this weight is not applied.</p>"""
            )
            continue
        blocks.append(
            f"""<label class="pm-weight">
              <span class="pm-weight-name">{html.escape(name)} <span class="pm-unit">{html.escape(unit)}</span></span>
              <input id="w-{html.escape(name)}" type="range" min="0" max="5" step="0.1" value="{value:g}" data-default="{value:g}">
              <span class="pm-weight-val" id="wv-{html.escape(name)}">{value:g}</span>
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
    formula = f"""
        <ul>
          <li><code>ndvi_median</code>, {html.escape(FEATURE_UNITS["ndvi_median"])}: absolute departure from 0. Scale {scorer.fmt(scales["ndvi_median"])}.</li>
          <li><code>precip_median_mm_hr</code>, {html.escape(FEATURE_UNITS["precip_median_mm_hr"])}: rate above 0. Scale {scorer.fmt(scales["precip_median_mm_hr"])}.</li>
          <li><code>lst_night_median_k</code>, {html.escape(FEATURE_UNITS["lst_night_median_k"])}: kelvin above the cold-tail target {scorer.fmt(cold_target)}. Scale {scorer.fmt(scales["lst_night_median_k"])}.</li>
          <li><code>slope_median_deg</code>, degrees: degrees outside the locked band {low:.1f}–{high:.1f}, and 0 inside it. No data in the grid, so this term is not applied.</li>
        </ul>
    """
    return f"""
    <div class="pm-app">
      <header class="pm-banner">
        <div>
          <h1>Partial Match</h1>
          <p class="pm-sentence">The score is a partial match on measured features, not a probability of mission success.</p>
        </div>
        <p class="pm-meta">{n_cells} land cells embedded. A lower score is a closer partial match. Gravity, vacuum, thin air, and radiation are not in this score.</p>
      </header>
      <div class="pm-map-cell">
        <div class="folium-map" id="{map_name}"></div>
        <div class="pm-legend">
          <div><i class="swatch rank"></i> Discovery rank</div>
          <div><i class="swatch a"></i> Site A · {html.escape(site_a["name"])}</div>
          <div><i class="swatch b"></i> Site B · {html.escape(site_b["name"])}, the control</div>
          <div><i class="swatch box"></i> Atacama hold-out</div>
          <p>The score is a partial match on measured features, not a probability of mission success.</p>
        </div>
      </div>
      <aside class="pm-side">
        <p id="pm-check" class="pm-check">Reading the embedded table.</p>
        <section>
          <h2>Weights</h2>
          <p class="pm-hint">Defaults are the weights in <code>notes/weights.json</code>. Moving a weight recomputes the order in this browser. It does not rebuild the file.</p>
          {weight_controls(weights, all_null)}
          <button type="button" id="pm-reset" class="pm-btn">Reset weights</button>
        </section>
        <section>
          <h2>Discovery list</h2>
          <p id="pm-status" class="pm-hint">Cells outside the Atacama box. Site B stays on the control list.</p>
          <ol id="pm-ranks" class="pm-ranks"></ol>
        </section>
        <section>
          <h2>Selected cell</h2>
          <div id="pm-detail"></div>
        </section>
        <section>
          <h2>Sites</h2>
          <p><strong>Site A · {html.escape(site_a["name"])}</strong>, {html.escape(site_a["country"])}. Cell <code>{html.escape(site_a["cell_id"])}</code>, {site_a["center"]["latitude"]:.1f}°, {site_a["center"]["longitude"]:.1f}°. <span id="pm-site-a-score"></span></p>
          <p class="pm-hint">Local zoom slope {scorer.fmt(float(a_slope))} degrees is a patch measurement. It is not the grid column, and the score leaves it out.</p>
          <p><strong>Site B · {html.escape(site_b["name"])}</strong>, {html.escape(site_b["country"])}. Cell <code>{html.escape(site_b["cell_id"])}</code>, {site_b["center"]["latitude"]:.1f}°, {site_b["center"]["longitude"]:.1f}°. The famous control, scored with the same function. <span id="pm-site-b-score"></span></p>
          <p class="pm-hint">Local zoom slope {scorer.fmt(float(b_slope))} degrees is a patch measurement. It is not the grid column, and the score leaves it out. Cells in the Atacama box do not become the discovery winner.</p>
          <p id="pm-control-now" class="pm-hint"></p>
        </section>
        <section>
          <h2>How a score is made</h2>
          <p>score = sum(weight × raw distance / scale) / sum(weight). The scale is the 95th percentile of that raw distance on land cells where the feature is measured, including the hold-out. The cold-tail target is the 10th percentile of night land-surface temperature. Those divisors stay fixed while a weight moves.</p>
          {formula}
          <p>A cell is ranked only when every feature with a positive weight and a measured column is present. A blank stays blank. It is not filled with zero, and the cell is not ranked on the features that remain.</p>
        </section>
      </aside>
      <section class="pm-bodies" aria-label="Moon and Mars targets">
        <article class="pm-body">
          <p class="pm-kicker">Moon</p>
          <h2>{html.escape(bodies["moon_name"])}</h2>
          <p class="pm-coord">{html.escape(bodies["moon_center"])}</p>
          <p>These coordinates are on the Moon. They are not plotted on the Earth map.</p>
        </article>
        <article class="pm-body">
          <p class="pm-kicker">Mars</p>
          <h2>{html.escape(bodies["mars_name"])}</h2>
          <p class="pm-coord">{html.escape(bodies["mars_center"])}</p>
          <p>These coordinates are on Mars. They are not plotted on the Earth map. Minerals, an ice-map raster, and a dust index are blank in the target notes.</p>
        </article>
      </section>
    </div>
    """


STYLE = """
<title>Partial Match map</title>
<style>
  html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; background: #f4f1ea; color: #1c1915; }
  body { font-family: "Segoe UI", Helvetica, Arial, sans-serif; font-size: 15px; line-height: 1.4; }
  .pm-app { height: 100%; display: grid; grid-template-columns: minmax(0, 1fr) 390px; grid-template-rows: auto minmax(0, 1fr) auto; }
  .pm-banner { grid-column: 1 / -1; display: flex; justify-content: space-between; gap: 16px; align-items: end; padding: 10px 14px 8px; background: #1c1915; color: #f4f1ea; }
  .pm-banner h1 { margin: 0; font-size: 1.15rem; letter-spacing: 0.01em; }
  .pm-sentence { margin: 2px 0 0; font-size: 0.98rem; }
  .pm-meta { margin: 0; max-width: 34rem; font-size: 0.82rem; color: #d9d0c3; }
  .pm-map-cell { position: relative; min-height: 0; }
  .pm-map-cell .folium-map { position: absolute !important; inset: 0; width: 100% !important; height: 100% !important; }
  .leaflet-container img, .leaflet-pane img { max-width: none !important; max-height: none !important; }
  .pm-legend { position: absolute; z-index: 500; left: 10px; bottom: 18px; max-width: 280px; background: rgba(244, 241, 234, 0.94); border: 1px solid #cfc6b8; padding: 8px 10px; font-size: 0.82rem; }
  .pm-legend p { margin: 6px 0 0; }
  .pm-legend div { display: flex; gap: 6px; align-items: center; margin: 2px 0; }
  .swatch { width: 12px; height: 12px; border-radius: 50%; display: inline-block; flex: 0 0 auto; }
  .swatch.rank { background: #1d4e89; }
  .swatch.a { background: #0b6e4f; }
  .swatch.b { background: #b45309; }
  .swatch.box { background: #c4a574; border-radius: 2px; }
  .pm-side { grid-column: 2; grid-row: 2 / span 2; overflow: auto; padding: 12px 14px 24px; background: #f7f4ee; border-left: 1px solid #ddd4c6; }
  .pm-side h2 { margin: 16px 0 6px; font-size: 0.95rem; }
  .pm-side section:first-of-type h2 { margin-top: 8px; }
  .pm-hint, .pm-side p { margin: 0 0 8px; }
  .pm-hint { color: #5c564c; font-size: 0.84rem; }
  .pm-weight { display: grid; grid-template-columns: 1fr auto; grid-template-areas: "name val" "slider slider"; gap: 2px 8px; margin: 8px 0; }
  .pm-weight-name { grid-area: name; font-family: Consolas, "Courier New", monospace; font-size: 0.78rem; }
  .pm-unit { color: #5c564c; font-family: "Segoe UI", Helvetica, sans-serif; }
  .pm-weight input { grid-area: slider; width: 100%; margin: 0; }
  .pm-weight-val { grid-area: val; font-variant-numeric: tabular-nums; min-width: 3.2rem; text-align: right; }
  .pm-weight.is-disabled { opacity: 0.72; }
  .pm-btn { margin-top: 6px; background: #1c1915; color: #f4f1ea; border: 0; padding: 6px 10px; cursor: pointer; }
  .pm-ranks { list-style: none; margin: 0; padding: 0; }
  .pm-ranks button { width: 100%; text-align: left; background: white; border: 1px solid #e4dccf; border-bottom: 0; padding: 6px 8px; cursor: pointer; font: inherit; }
  .pm-ranks li:last-child button { border-bottom: 1px solid #e4dccf; }
  .pm-ranks button.is-selected { background: #e7f0e4; }
  .pm-ranks .pm-id { font-family: Consolas, "Courier New", monospace; font-size: 0.84rem; }
  .pm-score { float: right; font-variant-numeric: tabular-nums; }
  .pm-table { width: 100%; border-collapse: collapse; font-size: 0.84rem; }
  .pm-table th, .pm-table td { border-bottom: 1px solid #e4dccf; padding: 4px 4px 4px 0; vertical-align: top; text-align: left; }
  .pm-table td:nth-child(2) { min-width: 4.5rem; font-variant-numeric: tabular-nums; }
  .pm-blank { min-height: 1.1em; }
  .pm-check { font-size: 0.84rem; padding: 6px 8px; background: #ece7dc; }
  .pm-check.is-bad { background: #f3d6d0; }
  .pm-bodies { grid-column: 1; grid-row: 3; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 8px 10px; background: #ebe4d6; border-top: 1px solid #ddd4c6; }
  .pm-body { background: white; border: 1px solid #ddd4c6; padding: 8px 10px; }
  .pm-body h2 { margin: 0 0 4px; font-size: 1rem; }
  .pm-body p { margin: 0 0 4px; font-size: 0.84rem; }
  .pm-kicker { text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.72rem; color: #5c564c; }
  .pm-coord { font-family: Consolas, "Courier New", monospace; font-size: 0.92rem; }
  .pm-pin { background: transparent; border: 0; }
  .pm-pin span { display: block; width: 22px; height: 22px; line-height: 18px; text-align: center; border-radius: 50%; background: #1d4e89; color: white; font-size: 12px; font-weight: 700; border: 2px solid white; box-shadow: 0 0 0 1px #1d4e89; }
  code { font-size: 0.84em; color: inherit; background: transparent; }
  @media (max-width: 860px) {
    html, body { height: auto; overflow: auto; }
    .pm-app { height: auto; grid-template-columns: 1fr; grid-template-rows: auto 62vh auto auto; }
    .pm-side { grid-column: 1; grid-row: 4; border-left: 0; border-top: 1px solid #ddd4c6; }
    .pm-bodies { grid-column: 1; grid-row: 3; grid-template-columns: 1fr; }
    .pm-banner { flex-direction: column; align-items: start; }
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
let sawLeader = false;
let lastLeader = -1;
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
    const label = document.getElementById("wv-" + feature.key);
    if (input && label) label.textContent = String(Number(input.value));
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

function drawMarkers(discovery, control) {
  if (!map || typeof L === "undefined") return;
  if (!pins) pins = L.layerGroup().addTo(map);
  pins.clearLayers();
  const leader = discovery.length ? discovery[0] : -1;
  discovery.slice(0, 5).forEach((i, rank) => {
    const icon = L.divIcon({
      className: "pm-pin",
      html: "<span>" + (rank + 1) + "</span>",
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });
    const point = L.marker([lats[i] / 10, lons[i] / 10], { icon: icon, zIndexOffset: 500 });
    point.bindTooltip("Discovery " + (rank + 1) + " · " + cellId(i) + " · " + fmtScore(scores[i]));
    point.on("click", () => select(i));
    point.addTo(pins);
  });
  const siteA = findCell(META.site_a.lat, META.site_a.lon);
  const siteB = findCell(META.site_b.lat, META.site_b.lon);
  if (siteA >= 0) {
    marker(lats[siteA] / 10, lons[siteA] / 10, {
      radius: 9, color: "#083d2c", weight: 2, fillColor: "#0b6e4f", fillOpacity: 0.95
    }, "Site A · " + META.site_a.name).on("click", () => select(siteA)).addTo(pins);
  }
  if (siteB >= 0) {
    marker(lats[siteB] / 10, lons[siteB] / 10, {
      radius: 9, color: "#7c3b08", weight: 2, fillColor: "#b45309", fillOpacity: 0.95
    }, "Site B · " + META.site_b.name + " · control").on("click", () => select(siteB)).addTo(pins);
  }
  if (leader >= 0 && sawLeader && leader !== lastLeader) {
    map.flyTo([lats[leader] / 10, lons[leader] / 10], 4, { duration: 0.6 });
  }
  if (leader >= 0) {
    sawLeader = true;
    lastLeader = leader;
  }
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
  const shown = discovery.slice(0, 8);
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
    "<span class=\"pm-score\">" + fmtScore(scores[i]) + "</span>" +
    "<span class=\"pm-id\">" + (rank + 1) + " · " + cellId(i) + "</span></button></li>"
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
  if (i < 0) return "That cell is not in the embedded table.";
  if (!eligible[i]) return "Not ranked at these weights, because a weighted feature is blank on the cell.";
  return "Score at these weights: " + fmtScore(scores[i]) + ".";
}

function renderDetail(i) {
  const root = document.getElementById("pm-detail");
  if (i < 0) {
    root.textContent = "Select a cell.";
    return;
  }
  const nulls = [];
  const rows = META.features.map((feature) => {
    let micro = NULL_I32;
    if (!feature.all_null) micro = micros[feature.key][i];
    const blank = micro === NULL_I32;
    if (blank) nulls.push(feature.key);
    const shown = blank ? "" : formatMeasured(micro);
    let state = "in the score";
    if (feature.all_null) state = "no data";
    else if (blank) state = "blank on this cell";
    else if (readWeights()[feature.key] <= 0) state = "weight is 0";
    return "<tr><td><code>" + esc(feature.key) + "</code></td><td class=\"" + (blank ? "pm-blank" : "") + "\">" + esc(shown) + "</td><td>" + state + "</td></tr>";
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
    "<table class=\"pm-table\"><thead><tr><th>Feature</th><th>Measurement</th><th></th></tr></thead><tbody>" +
    rows + "</tbody></table>" +
    "<p class=\"pm-hint\">Null on this cell: " + (nulls.length ? nulls.map(esc).join(", ") : "none") + ". A blank measurement is left blank.</p>";
}

function select(i) {
  selected = i;
  renderDetail(i);
  document.querySelectorAll(".pm-ranks button").forEach((button) => {
    button.classList.toggle("is-selected", Number(button.getAttribute("data-i")) === i);
  });
  if (map) map.panTo([lats[i] / 10, lons[i] / 10]);
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
  note.textContent = "Default order matches the batch score. Rank 1 is " + META.expected_top[0].id + ". Moving a weight does not rebuild this file.";
}

function rerank() {
  const weights = readWeights();
  const ranked = rankCells(weights);
  if (selected < 0 && ranked.discovery.length) selected = ranked.discovery[0];
  renderList(ranked.discovery, ranked.control, weights);
  renderDetail(selected);
  drawMarkers(ranked.discovery, ranked.control);
  const defaults = META.features.every((feature) => {
    if (feature.all_null) return true;
    const input = document.getElementById("w-" + feature.key);
    return Number(input.value) === Number(input.getAttribute("data-default"));
  });
  if (defaults) checkDefault(ranked.discovery, ranked.control);
  else {
    const note = document.getElementById("pm-check");
    note.className = "pm-check";
    note.textContent = "Weights differ from notes/weights.json. The list was recomputed in the browser. Reset restores the batch order.";
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
  });
  document.getElementById("pm-reset").addEventListener("click", () => {
    META.features.forEach((feature) => {
      if (feature.all_null) return;
      const input = document.getElementById("w-" + feature.key);
      input.value = input.getAttribute("data-default");
    });
    sawLeader = false;
    lastLeader = -1;
    if (map) map.setView([18, 10], 2);
    scheduleRank();
  });
  rerank();
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
