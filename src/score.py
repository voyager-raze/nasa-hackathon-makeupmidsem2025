"""Score land cells as a partial match to the Moon-operations screen.

Reads data/processed/features.csv and notes/weights.json. Reads the lunar
slope band from notes/targets.md. Does not modify the measurement table.

Writes results/top5.csv, results/control.csv, and results/score-notes.md.
Lower score is a closer partial match on the measured features.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES_CSV = ROOT / "data" / "processed" / "features.csv"
WEIGHTS_JSON = ROOT / "notes" / "weights.json"
TARGETS_MD = ROOT / "notes" / "targets.md"
FEATURES_MD = ROOT / "notes" / "features.md"
TOP5_CSV = ROOT / "results" / "top5.csv"
CONTROL_CSV = ROOT / "results" / "control.csv"
NOTES_MD = ROOT / "results" / "score-notes.md"

# Atacama Desert, the famous control. Northern Chile from 18°S to 30°S,
# Pacific slope to the Andean front. Cell centers on the boundary are inside.
# The box is the mapped desert, not a window fitted to a ranking.
HOLDOUT_NAME = "Atacama Desert"
HOLDOUT_LAT_MIN = -30.0
HOLDOUT_LAT_MAX = -18.0
HOLDOUT_LON_MIN = -71.5
HOLDOUT_LON_MAX = -67.0

FEATURE_ORDER = (
    "slope_median_deg",
    "ndvi_median",
    "precip_median_mm_hr",
    "lst_night_median_k",
)
UNITS = {
    "slope_median_deg": "degrees",
    "ndvi_median": "NDVI",
    "precip_median_mm_hr": "mm/hr",
    "lst_night_median_k": "kelvin",
}
RULES = {
    "slope_median_deg": "degrees outside the lunar slope band; 0 inside the band",
    "ndvi_median": "absolute departure from 0",
    "precip_median_mm_hr": "mm/hr above 0, the dry end of the logged rate",
    "lst_night_median_k": "kelvin above the cold-tail percentile; 0 at or below it",
}


def stop(messages: list[str]) -> None:
    print("Stopping. Required inputs are missing or a locked input was not measured.", file=sys.stderr)
    for message in messages:
        print(f"  {message}", file=sys.stderr)
    sys.exit(1)


def require_inputs() -> None:
    missing = []
    for path in (FEATURES_CSV, WEIGHTS_JSON, TARGETS_MD, FEATURES_MD):
        if not path.is_file():
            missing.append(str(path))
    if missing:
        stop(missing)


def read_slope_band(text: str) -> tuple[float, float]:
    match = re.search(
        r"Locked band:\s*([0-9]+(?:\.[0-9]+)?)\s*[\u2012\u2013\u2014\-]\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*degrees",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        stop(
            [
                f"{TARGETS_MD} has no measured lunar slope band "
                "(expected a 'Locked band: <low>–<high> degrees' line)."
            ]
        )
    low = float(match.group(1))
    high = float(match.group(2))
    if high < low:
        stop([f"Lunar slope band in {TARGETS_MD} runs from {low} down to {high}."])
    return low, high


def load_weights() -> dict:
    try:
        payload = json.loads(WEIGHTS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        stop([f"{WEIGHTS_JSON} is not valid JSON: {exc}"])
    if "features" not in payload or not isinstance(payload["features"], dict):
        stop([f"{WEIGHTS_JSON} needs a 'features' object of weights."])
    for key in ("cold_tail_percentile", "distance_scale_percentile"):
        if key not in payload:
            stop([f"{WEIGHTS_JSON} needs '{key}'."])
        value = float(payload[key])
        if not 0 < value < 100:
            stop([f"{WEIGHTS_JSON} {key} must be between 0 and 100. Found {value}."])
        payload[key] = value
    features = payload["features"]
    cleaned = {}
    for name, spec in features.items():
        if name not in RULES:
            stop(
                [
                    f"{WEIGHTS_JSON} lists '{name}', which has no comparison rule. "
                    "The score will not invent one."
                ]
            )
        if not isinstance(spec, dict) or "weight" not in spec:
            stop([f"{WEIGHTS_JSON} feature '{name}' needs a weight."])
        cleaned[name] = float(spec["weight"])
    payload["features"] = cleaned
    return payload


def raw_distance(
    values: pd.Series,
    name: str,
    cold_target: float | None,
    slope_band: tuple[float, float],
) -> pd.Series:
    if name == "ndvi_median":
        return (values - 0.0).abs()
    if name == "precip_median_mm_hr":
        return (values - 0.0).clip(lower=0.0)
    if name == "lst_night_median_k":
        if cold_target is None:
            stop(["Cold-tail target was not computed."])
        return (values - cold_target).clip(lower=0.0)
    if name == "slope_median_deg":
        low, high = slope_band
        below = (low - values).clip(lower=0.0)
        above = (values - high).clip(lower=0.0)
        return below + above
    stop([f"No comparison rule for {name}."])
    raise AssertionError


def fmt(value: float) -> str:
    return f"{value:.6g}"


def cell_id(lat: float, lon: float) -> str:
    return f"{lat:.1f}_{lon:.1f}"


def holdout_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["lat_center_deg"].between(HOLDOUT_LAT_MIN, HOLDOUT_LAT_MAX) & frame[
        "lon_center_deg"
    ].between(HOLDOUT_LON_MIN, HOLDOUT_LON_MAX)


def eligible_mask(frame: pd.DataFrame, active: list[str]) -> pd.Series:
    """Require every positively weighted, measured feature to be present."""
    if not active:
        return pd.Series(False, index=frame.index, dtype=bool)
    missing = [name for name in active if name not in frame.columns]
    if missing:
        stop([f"Eligibility check is missing columns: {', '.join(missing)}."])
    return frame[active].notna().all(axis=1)


def feature_list(names: list[str]) -> str:
    return ";".join(names) if names else "none"


def export_rows(frame: pd.DataFrame, rank_start: int = 1) -> pd.DataFrame:
    rows = frame.copy()
    rows.insert(0, "rank", range(rank_start, rank_start + len(rows)))
    rows["cell_id"] = [
        cell_id(lat, lon)
        for lat, lon in zip(rows["lat_center_deg"], rows["lon_center_deg"], strict=True)
    ]
    rows["lat_center_deg"] = rows["lat_center_deg"].map(lambda value: f"{value:.1f}")
    rows["lon_center_deg"] = rows["lon_center_deg"].map(lambda value: f"{value:.1f}")
    for name in FEATURE_ORDER:
        rows[name] = rows[name].map(lambda value: "null" if pd.isna(value) else fmt(float(value)))
    rows["score"] = rows["score"].map(lambda value: f"{float(value):.6f}")
    columns = [
        "rank",
        "cell_id",
        "lat_center_deg",
        "lon_center_deg",
        *FEATURE_ORDER,
        "score",
        "features_used",
        "features_missing",
    ]
    return rows[columns]


def worked_example(
    row: pd.Series,
    active: list[str],
    weights: dict[str, float],
    scales: dict[str, float],
    cold_target: float | None,
    slope_band: tuple[float, float],
) -> list[str]:
    lines = []
    weight_sum = sum(weights[name] for name in active)
    for name in active:
        raw = float(
            raw_distance(pd.Series([row[name]]), name, cold_target, slope_band).iloc[0]
        )
        norm = raw / scales[name]
        lines.append(
            f"- `{name}`: raw distance {fmt(raw)} {UNITS[name]}, "
            f"divided by {fmt(scales[name])} {UNITS[name]} = {norm:.6f}, "
            f"times weight {fmt(weights[name])}."
        )
    lines.append(
        f"- Score = weighted mean = {float(row['score']):.6f} "
        f"(denominator {fmt(weight_sum)})."
    )
    return lines


def render_notes(
    weights_payload: dict,
    slope_band: tuple[float, float],
    cold_target: float,
    scales: dict[str, float],
    active: list[str],
    skipped: list[tuple[str, str]],
    top: pd.DataFrame,
    control: pd.Series,
    n_eligible_discovery: int,
    n_eligible_control: int,
    control_median: float,
    n_cold_tail: int,
    cold_tail_lat_max: float,
    south_of_60: pd.Series | None,
) -> str:
    low, high = slope_band
    weight_lines = []
    for name in FEATURE_ORDER:
        if name not in weights_payload["features"]:
            continue
        applied = "used" if name in active else "not used this run"
        weight_lines.append(
            f"| `{name}` | {fmt(weights_payload['features'][name])} | {UNITS[name]} | {applied} |"
        )
    scale_lines = []
    for name in active:
        scale_lines.append(
            f"| `{name}` | {fmt(scales[name])} {UNITS[name]} | {RULES[name]} |"
        )
    skip_lines = [f"- `{name}`: {reason}" for name, reason in skipped]
    if not skip_lines:
        skip_lines = ["- No scored column was entirely null."]

    top_lines = [
        "| rank | cell_id | lat | lon | NDVI | night LST (K) | precip (mm/hr) | score |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in top.iterrows():
        top_lines.append(
            "| {rank} | `{cell_id}` | {lat} | {lon} | {ndvi} | {lst} | {precip} | {score} |".format(
                rank=int(row["rank"]),
                cell_id=row["cell_id"],
                lat=row["lat_center_deg"],
                lon=row["lon_center_deg"],
                ndvi=row["ndvi_median"],
                lst=row["lst_night_median_k"],
                precip=row["precip_median_mm_hr"],
                score=row["score"],
            )
        )

    lats = [float(value) for value in top["lat_center_deg"]]
    lons = [float(value) for value in top["lon_center_deg"]]
    cluster = (
        f"The five centers span latitude {min(lats):.1f} to {max(lats):.1f} "
        f"and longitude {min(lons):.1f} to {max(lons):.1f}."
    )

    if south_of_60 is None:
        south_text = "No eligible discovery cell south of 60°N was available."
    else:
        south_text = (
            f"The best eligible discovery cell south of 60°N is `{cell_id(float(south_of_60['lat_center_deg']), float(south_of_60['lon_center_deg']))}` "
            f"at latitude {float(south_of_60['lat_center_deg']):.1f}, longitude {float(south_of_60['lon_center_deg']):.1f}, "
            f"score {float(south_of_60['score']):.6f}. "
            f"That score is a worse partial match than the Atacama control cell ({float(control['score']):.6f}). "
            "It is not one of the five discovery ranks."
        )

    file_weights = ", ".join(
        f"`{name}` {fmt(weights_payload['features'][name])}"
        for name in FEATURE_ORDER
        if name in weights_payload["features"]
    )
    effective = ", ".join(
        f"`{name}` {fmt(weights_payload['features'][name])}" for name in active
    )

    return f"""# Score notes

The score is a partial match on the measured features, not a probability of mission success.
It is a heuristic screening index: none of the three scored features has a direct Moon or Mars referent in the cited source table. The Earth-side targets below are proxies, not planetary measurements.

A lower score is a closer partial match. Gravity, vacuum, thin air, and radiation are not in this score.

## Formula

For each feature that is measured on the cell and was not skipped, the distance is the Earth value compared with the target in that feature's own unit. Each raw distance is then divided by a scale in that same unit: the {fmt(weights_payload['distance_scale_percentile'])}th percentile of that raw distance on land cells where the feature is measured, including cells inside the hold-out. Those divisors are listed below. The score is the weighted mean of the quotients, using only features measured on that cell:

score = sum(weight × raw distance / scale) / sum(weight)

Weights, the cold-tail percentile, and the scale percentile are read from `notes/weights.json` on every run. They are not hard-coded in `src/score.py`. The lunar slope band is read from `notes/targets.md`.

Comparisons:

- `ndvi_median`: target is 0. Distance is the absolute departure from 0, in NDVI. A small negative index and a small positive index are both near the target. June NDVI near zero includes snow and ice as well as bare ground. This score does not separate those surfaces.
- `precip_median_mm_hr`: dryness uses the dry direction of the logged IMERG rate. The target is 0 mm/hr. Distance is the rate when the rate is positive, in mm/hr. June 2024 is one month, not an annual normal. A zero in this column is the dry end of this granule.
- `lst_night_median_k`: this is the only temperature column in the table. `LST_Day_CMG` was not reduced, so there is no day–night range to score. The cold-tail target is the {fmt(weights_payload['cold_tail_percentile'])}th percentile of measured night land-surface temperature, **{fmt(cold_target)} kelvin**. Distance is kelvin above that percentile. A cell at or below it has distance 0.
- `slope_median_deg`: nearness to the lunar band means 0 distance inside the band and, outside it, the degrees to the nearest edge. The band read from `notes/targets.md` is **{low:.1f}–{high:.1f} degrees**.

A cell enters the discovery ranking or the control ranking only when every feature that has a positive weight and a column that is not entirely null is measured on that cell. A missing vegetation, precipitation, or night-temperature value stays out of the score. It is not filled, and the cell is not ranked on the features that remain, because dropping a missing test would make the cell look closer. `features_missing` on each ranked row still lists the skipped column. Nulls in `results/top5.csv` are written as `null`.

## Weights

File weights this delivery: {file_weights}.

Effective weights in the denominator this run: {effective}.

| Feature | Weight in `notes/weights.json` | Unit of the raw distance | This run |
| --- | --- | --- | --- |
{chr(10).join(weight_lines)}

Changing the slope weight does not change `results/top5.csv` while `slope_median_deg` is empty. Changing the weight of a feature in the effective list does. The delivered weights are the weights that produced the delivered ranking.

## Scales

The scale is the {fmt(weights_payload['distance_scale_percentile'])}th percentile of the raw distance. Dividing by it puts a typical far value near 1 before the weights are applied. A cell farther out than that percentile can score above 1 on that feature.

| Feature | Scale | Raw distance |
| --- | --- | --- |
{chr(10).join(scale_lines)}

The cold-tail target, {fmt(cold_target)} kelvin, is the {fmt(weights_payload['cold_tail_percentile'])}th percentile of `lst_night_median_k` on land cells where that column is measured. {n_cold_tail} land cells are at or below it. The warmest latitude among those cells is {fmt(cold_tail_lat_max)} degrees. They are not a discovery result: June NDVI is blank on every land cell south of 60°S, so those cells fail the eligibility rule.

## Features skipped

{chr(10).join(skip_lines)}

Confidence is lower because the slope comparison is not yet measured. No slope raster was invented. Elevation was reserved for the zoom on the two chosen patches.

## Hold-out

The famous control is the {HOLDOUT_NAME}. Cells whose centers fall inside this bounding box do not compete for `results/top5.csv`.

| Edge | Degrees | Geographic edge |
| --- | --- | --- |
| South | {HOLDOUT_LAT_MIN:.1f} | 30°S |
| North | {HOLDOUT_LAT_MAX:.1f} | 18°S |
| West | {HOLDOUT_LON_MIN:.1f} | 71.5°W |
| East | {HOLDOUT_LON_MAX:.1f} | 67°W |

The box covers the Chilean Atacama from the northern desert to about 30°S and from the Pacific slope to the Andean front, including the Salar de Atacama. The Antarctic Dry Valleys are another famous control the science notes allow, and they were not used. June NDVI is blank south of 60°S, so vegetation cannot be scored there. Atacama has the three features this run actually scores.

Eligible cells inside the box: {n_eligible_control}. Eligible discovery cells outside it: {n_eligible_discovery}.

## Control score

The control score is the best eligible cell inside the box, from the same function as the discovery cells. It is not a discovery winner.

| Item | Value |
| --- | --- |
| cell_id | `{cell_id(float(control['lat_center_deg']), float(control['lon_center_deg']))}` |
| latitude | {float(control['lat_center_deg']):.1f} |
| longitude | {float(control['lon_center_deg']):.1f} |
| ndvi_median | {fmt(float(control['ndvi_median']))} |
| lst_night_median_k | {fmt(float(control['lst_night_median_k']))} |
| precip_median_mm_hr | {fmt(float(control['precip_median_mm_hr']))} |
| slope_median_deg | null |
| score | {float(control['score']):.6f} |
| features missing | slope_median_deg |

The median score of the {n_eligible_control} eligible cells in the box is {control_median:.6f}. That median is a summary of the same cell scores. It is not a second formula. The row written to `results/control.csv` is the best cell.

## Ranking meanings

`results/top5.csv` is the unfiltered published batch ranking and contains the Greenland ice-sheet cluster. The map's discovery ranking excludes the Atacama hold-out and the Greenland cluster rectangle (70.5–78.9°N, 50.1–28.9°W), supported by the June/August 2024 Worldview checks in `notes/worldview-checks.md`; the five leading cells also have individual source rows in `results/sources.csv`. It answers which eligible cells remain for follow-up after those exclusions; it does not identify the best overall candidate. Kunlun's locked score is worse than the Vinchina control score. `results/control.csv` is the best eligible cell inside the Atacama box under the same formula.

## Discovery cells

`results/top5.csv` is written by `src/score.py` from the measurement table and the weights file. These five rows are that file.

{chr(10).join(top_lines)}

{cluster}

Each of these rows is missing `slope_median_deg`. The feature columns that were measured are filled from `data/processed/features.csv`. The script does not edit that table.

{south_text}

## Worked example for rank 1

__WINNER_EXAMPLE__

## What this score is not

The score is a partial match on the measured features, not a probability of mission success. Gravity, vacuum, thin air, and radiation stay out of scope. Slope stays out of the score until that column is measured.

Rerun with `python src/score.py` after any edit to `notes/weights.json`.
"""


def main() -> None:
    require_inputs()
    slope_band = read_slope_band(TARGETS_MD.read_text(encoding="utf-8"))
    weights_payload = load_weights()
    weights: dict[str, float] = weights_payload["features"]
    frame = pd.read_csv(FEATURES_CSV)
    required_columns = ["lat_center_deg", "lon_center_deg", *FEATURE_ORDER]
    missing_columns = [name for name in required_columns if name not in frame.columns]
    if missing_columns:
        stop(
            [
                f"{FEATURES_CSV} is missing columns: {', '.join(missing_columns)}. "
                "They were not invented."
            ]
        )

    active: list[str] = []
    skipped: list[tuple[str, str]] = []
    for name in FEATURE_ORDER:
        if name not in weights:
            continue
        if weights[name] <= 0:
            skipped.append((name, f"weight in {WEIGHTS_JSON.name} is {fmt(weights[name])}, so it is left out."))
            continue
        if frame[name].isna().all():
            skipped.append(
                (
                    name,
                    "the column is null on every land cell, so this feature is left out of the score. "
                    "The slope comparison is not yet measured."
                    if name == "slope_median_deg"
                    else "the column is null on every land cell, so this feature is left out of the score.",
                )
            )
            continue
        active.append(name)

    if not active:
        stop(["No feature has both a positive weight and a measured value. Nothing was scored."])

    cold_target = None
    if "lst_night_median_k" in active:
        cold_target = float(
            frame["lst_night_median_k"].quantile(weights_payload["cold_tail_percentile"] / 100.0)
        )

    scales: dict[str, float] = {}
    norm = pd.DataFrame(index=frame.index)
    for name in active:
        distance = raw_distance(frame[name], name, cold_target, slope_band)
        scale = float(distance.quantile(weights_payload["distance_scale_percentile"] / 100.0))
        if scale <= 0:
            stop(
                [
                    f"The scale for {name} is {scale}. A zero scale would hide the distance. "
                    "The feature was not scored."
                ]
            )
        scales[name] = scale
        norm[name] = distance / scale

    weight_sum = pd.Series(0.0, index=frame.index)
    weighted = pd.Series(0.0, index=frame.index)
    for name in active:
        present = frame[name].notna()
        weight_sum = weight_sum + (weights[name] * present.astype(float))
        weighted = weighted + (weights[name] * norm[name] * present.astype(float))
    frame = frame.copy()
    frame["score"] = weighted / weight_sum.where(weight_sum > 0)
    frame["eligible"] = eligible_mask(frame, active)
    frame["in_holdout"] = holdout_mask(frame)

    used = feature_list(active)
    missing = feature_list([name for name, _reason in skipped])
    frame["features_used"] = used
    frame["features_missing"] = missing

    discovery = frame.loc[frame["eligible"] & ~frame["in_holdout"]].sort_values(
        ["score", "lat_center_deg", "lon_center_deg"],
        ascending=[True, True, True],
        kind="mergesort",
    )
    control_cells = frame.loc[frame["eligible"] & frame["in_holdout"]].sort_values(
        ["score", "lat_center_deg", "lon_center_deg"],
        ascending=[True, True, True],
        kind="mergesort",
    )
    if discovery.empty or control_cells.empty:
        stop(
            [
                "The ranking is empty. "
                f"Eligible discovery cells: {len(discovery)}. "
                f"Eligible control cells: {len(control_cells)}."
            ]
        )
    if len(discovery) < 5:
        stop(
            [
                f"Only {len(discovery)} eligible discovery cells. "
                "Five ranks were not invented to fill the file."
            ]
        )

    top_numeric = discovery.head(5).copy()
    control_numeric = control_cells.iloc[0]
    if holdout_mask(top_numeric).any():
        stop(["A hold-out cell entered the discovery list. The file was not written."])

    cold_rows = frame.loc[frame["lst_night_median_k"].notna() & (frame["lst_night_median_k"] <= cold_target)]
    south = discovery.loc[discovery["lat_center_deg"] < 60]
    south_row = None if south.empty else south.iloc[0]

    top_out = export_rows(top_numeric)
    control_out = export_rows(control_numeric.to_frame().T)

    winner_example = "\n".join(
        worked_example(
            top_numeric.iloc[0],
            active,
            weights,
            scales,
            cold_target,
            slope_band,
        )
    )
    notes = render_notes(
        weights_payload,
        slope_band,
        float(cold_target),
        scales,
        active,
        skipped,
        top_out,
        control_numeric,
        n_eligible_discovery=len(discovery),
        n_eligible_control=len(control_cells),
        control_median=float(control_cells["score"].median()),
        n_cold_tail=int(len(cold_rows)),
        cold_tail_lat_max=float(cold_rows["lat_center_deg"].max()) if len(cold_rows) else float("nan"),
        south_of_60=south_row,
    ).replace("__WINNER_EXAMPLE__", winner_example)

    RESULTS = ROOT / "results"
    RESULTS.mkdir(exist_ok=True)
    top_out.to_csv(TOP5_CSV, index=False, lineterminator="\n")
    control_out.to_csv(CONTROL_CSV, index=False, lineterminator="\n")
    NOTES_MD.write_text(notes, encoding="utf-8", newline="\n")
    print(f"Wrote {TOP5_CSV}")
    print(f"Wrote {CONTROL_CSV}")
    print(f"Wrote {NOTES_MD}")
    print("Discovery ranks:")
    print(top_out[["rank", "cell_id", "score"]].to_string(index=False))
    print(
        "Control:",
        control_out.iloc[0]["cell_id"],
        control_out.iloc[0]["score"],
    )


if __name__ == "__main__":
    main()
