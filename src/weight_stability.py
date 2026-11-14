"""Measure ranking sensitivity to Dirichlet-distributed feature weights."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from export_map_data import rejected_center
from score import (
    FEATURES_CSV,
    FEATURE_ORDER,
    ROOT,
    TARGETS_MD,
    WEIGHTS_JSON,
    cell_id,
    holdout_mask,
    load_weights,
    raw_distance,
    read_slope_band,
)

SITES_JSON = ROOT / "results" / "sites.json"
OUTPUT_JSON = ROOT / "results" / "weight-stability.json"
DRAW_COUNT = 500
SEED = 20261115
RANK1_CELL = "35.3_81.1"
WEIGHT_PRIORS = {"Dirichlet(1,1,1)": 1.0, "Dirichlet(0.5,0.5,0.5)": 0.5}
METHOD_VERSION = "weight-sensitivity-v2"
EXCLUSION_SOURCE = ROOT / "notes" / "worldview-checks.md"


def method_fingerprint() -> str:
    paths = (ROOT / "src" / "score.py", ROOT / "src" / "export_map_data.py", Path(__file__))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    weights_payload = load_weights()
    weights: dict[str, float] = weights_payload["features"]
    frame = pd.read_csv(FEATURES_CSV)
    missing_columns = [
        name
        for name in ("lat_center_deg", "lon_center_deg", *FEATURE_ORDER)
        if name not in frame.columns
    ]
    if missing_columns:
        raise SystemExit(f"{FEATURES_CSV} is missing columns: {', '.join(missing_columns)}.")

    active = [
        name
        for name in FEATURE_ORDER
        if name in weights and weights[name] > 0 and not frame[name].isna().all()
    ]
    if not active:
        raise SystemExit("No measured, positively weighted features are available.")

    cold_target = None
    if "lst_night_median_k" in active:
        cold_target = float(
            frame["lst_night_median_k"].quantile(
                weights_payload["cold_tail_percentile"] / 100.0
            )
        )
    slope_band = read_slope_band(TARGETS_MD.read_text(encoding="utf-8"))
    normalized = []
    for name in active:
        distance = raw_distance(frame[name], name, cold_target, slope_band)
        scale = float(
            distance.quantile(weights_payload["distance_scale_percentile"] / 100.0)
        )
        if not np.isfinite(scale) or scale <= 0:
            raise SystemExit(f"Invalid distance scale for {name}: {scale}.")
        normalized.append((distance / scale).to_numpy(dtype=np.float64))
    normalized_matrix = np.column_stack(normalized)
    eligible = frame[active].notna().all(axis=1).to_numpy()
    sites = json.loads(SITES_JSON.read_text(encoding="utf-8"))

    def site_index(site_name: str) -> int:
        center = sites[site_name]["center"]
        match = np.flatnonzero(
            (frame["lat_center_deg"].to_numpy() == float(center["latitude"]))
            & (frame["lon_center_deg"].to_numpy() == float(center["longitude"]))
        )
        if len(match) != 1 or not eligible[match[0]]:
            raise SystemExit(f"{site_name} is not one eligible row in the June table.")
        return int(match[0])

    site_a = site_index("site_a")
    site_b = site_index("site_b")
    latitudes = frame["lat_center_deg"].to_numpy(dtype=np.float64)
    longitudes = frame["lon_center_deg"].to_numpy(dtype=np.float64)
    in_holdout = holdout_mask(frame).to_numpy()
    ids = [
        cell_id(float(lat), float(lon))
        for lat, lon in zip(latitudes, longitudes, strict=True)
    ]
    rejected = np.array(
        [
            rejected_center(float(lat), float(lon))
            for lat, lon in zip(latitudes, longitudes, strict=True)
        ]
    )
    discovery_mask = eligible & ~in_holdout & ~rejected
    discovery_indices = np.flatnonzero(discovery_mask)
    if len(discovery_indices) < 5:
        raise SystemExit("Fewer than five eligible discovery cells remain.")

    default_weights = np.array([weights[name] for name in active], dtype=np.float64)
    default_weights /= default_weights.sum()
    default_scores = normalized_matrix[discovery_indices] @ default_weights
    default_order = np.lexsort(
        (
            longitudes[discovery_indices],
            latitudes[discovery_indices],
            default_scores,
        )
    )
    observed_rank1 = ids[discovery_indices[default_order[0]]]
    if observed_rank1 != RANK1_CELL:
        raise SystemExit(
            f"Expected displayed rank 1 {RANK1_CELL}, found {observed_rank1}; "
            "stability results were not written."
        )

    rng = np.random.default_rng(SEED)
    site_a_values = normalized_matrix[site_a]
    site_b_values = normalized_matrix[site_b]
    discovery_values = normalized_matrix[discovery_indices]
    discovery_latitudes = latitudes[discovery_indices]
    discovery_longitudes = longitudes[discovery_indices]
    rank1_global = ids.index(RANK1_CELL)
    rank1_match = np.flatnonzero(discovery_indices == rank1_global)
    if len(rank1_match) != 1:
        raise SystemExit(f"{RANK1_CELL} is not in the displayed discovery set.")
    rank1_local = int(rank1_match[0])

    prior_results = []
    for prior_name, alpha in WEIGHT_PRIORS.items():
        draws = rng.dirichlet(
            np.full(len(active), alpha, dtype=np.float64), size=DRAW_COUNT
        )
        site_b_closer = 0
        rank1_in_top5 = 0
        for draw in draws:
            if float(site_b_values @ draw) < float(site_a_values @ draw):
                site_b_closer += 1
            scores = discovery_values @ draw
            cutoff = np.partition(scores, 4)[4]
            candidates = np.flatnonzero(scores <= cutoff)
            order = np.lexsort(
                (
                    discovery_longitudes[candidates],
                    discovery_latitudes[candidates],
                    scores[candidates],
                )
            )
            if rank1_local in candidates[order[:5]]:
                rank1_in_top5 += 1
        prior_results.append(
            {
                "prior": prior_name,
                "alpha": alpha,
                "draws": DRAW_COUNT,
                "vinchina_closer_count": site_b_closer,
                "vinchina_closer_fraction": site_b_closer / DRAW_COUNT,
                "rank1_top5_count": rank1_in_top5,
                "rank1_top5_fraction": rank1_in_top5 / DRAW_COUNT,
            }
        )

    primary = prior_results[0]

    result = {
        "method_version": METHOD_VERSION,
        "draws": DRAW_COUNT,
        "seed": SEED,
        "distribution": f"Dirichlet(1) over {len(active)} effective features",
        "features": active,
        "rank1_cell": RANK1_CELL,
        "vinchina_closer_count": primary["vinchina_closer_count"],
        "vinchina_closer_fraction": primary["vinchina_closer_fraction"],
        "rank1_top5_count": primary["rank1_top5_count"],
        "rank1_top5_fraction": primary["rank1_top5_fraction"],
        "prior_sensitivity": prior_results,
        "features_sha256": hashlib.sha256(FEATURES_CSV.read_bytes()).hexdigest(),
        "weights_sha256": hashlib.sha256(WEIGHTS_JSON.read_bytes()).hexdigest(),
        "targets_sha256": hashlib.sha256(TARGETS_MD.read_bytes()).hexdigest(),
        "exclusion_source_sha256": hashlib.sha256(EXCLUSION_SOURCE.read_bytes()).hexdigest(),
        "method_sha256": method_fingerprint(),
        "ranking_exclusions": {
            "atacama_holdout": {
                "lat_min": -30.0,
                "lat_max": -18.0,
                "lon_min": -71.5,
                "lon_max": -67.0,
            },
            "greenland_cluster_bounds": {
                "lat_min": 70.5,
                "lat_max": 78.9,
                "lon_min": -50.1,
                "lon_max": -28.9,
                "source": "notes/worldview-checks.md",
            },
        },
    }
    OUTPUT_JSON.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Features: {', '.join(active)}")
    for result in prior_results:
        print(
            f"{result['prior']}: Vinchina closer {result['vinchina_closer_count']}/{DRAW_COUNT}; "
            f"rank 1 stays top five {result['rank1_top5_count']}/{DRAW_COUNT}"
        )
    print(f"Wrote {OUTPUT_JSON.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
