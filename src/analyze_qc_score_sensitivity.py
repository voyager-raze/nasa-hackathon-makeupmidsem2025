
"""Analyze how MOD11C3 nighttime-LST QC tiers affect the two site scores.

This is a separate sensitivity analysis. It does not modify the original
features, weights, scoring script, or published ranking outputs.

Fixed scoring parameters are taken from the original score notes:
- NDVI target: 0
- Precipitation target: 0 mm/hr
- Nighttime LST target: 214.3 K
- NDVI scale: 0.8304
- Precipitation scale: 0.296 mm/hr
- Nighttime LST scale: 86.2 K

The original three effective weights are all 1.
"""

import csv
import math
from pathlib import Path


# ---------------------------------------------------------
# 1. File locations
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

FEATURES_CSV = ROOT / "data" / "processed" / "features.csv"
QC_CSV = ROOT / "results" / "qc_robustness" / "site_tiers_june2024.csv"

OUT_DIR = ROOT / "results" / "qc_robustness"
OUT_CSV = OUT_DIR / "score_sensitivity_june2024.csv"
OUT_MD = OUT_DIR / "score_sensitivity_june2024.md"


# ---------------------------------------------------------
# 2. Fixed original scoring parameters
# ---------------------------------------------------------

COLD_TARGET_K = 214.3

SCALES = {
    "ndvi_median": 0.8304,
    "precip_median_mm_hr": 0.296,
    "lst_night_median_k": 86.2,
}

WEIGHTS = {
    "ndvi_median": 1.0,
    "precip_median_mm_hr": 1.0,
    "lst_night_median_k": 1.0,
}

SITES = {
    "Kunlun": {
        "lat": 35.3,
        "lon": 81.1,
        "published_score": 0.186845,
    },
    "Vinchina": {
        "lat": -27.9,
        "lon": -68.9,
        "published_score": 0.167981,
    },
}

# Reporting threshold only, not a statistical confidence threshold.
MIN_PIXELS_FOR_STANDARD_SUPPORT = 8

# Maximum allowed difference (K) used for two consistency checks:
# the T0 QC median versus the original feature-table LST, and the manually
# transcribed pixel values versus the computed T4 median. It covers rounding
# at two decimal places and is not a scientific uncertainty.
LST_MATCH_TOLERANCE_K = 0.005

# Kunlun T4 retained-pixel values (K), MANUALLY TRANSCRIBED from the earlier
# June 2024 HDF pixel inspection. They are NOT computed by this script and are
# NOT a reproducible output of it. They are used only to print a
# provenance-labelled table in the report, are cross-checked against the T4
# median read from the QC CSV, and never enter any score calculation.
MANUAL_KUNLUN_T4_PIXELS_K = (261.34, 264.02)

REPORT_TIER_ORDER = ("T0", "T1", "T2", "T4", "T5", "X1")


# ---------------------------------------------------------
# 3. Read the original feature measurements
# ---------------------------------------------------------

def read_original_features():
    """Find the original June feature row for each candidate site."""

    if not FEATURES_CSV.is_file():
        raise FileNotFoundError(f"Missing file: {FEATURES_CSV}")

    found = {}

    with FEATURES_CSV.open(
        "r", newline="", encoding="utf-8-sig"
    ) as fh:
        reader = csv.DictReader(fh)

        for row in reader:
            lat = float(row["lat_center_deg"])
            lon = float(row["lon_center_deg"])

            for site, info in SITES.items():
                if (
                    math.isclose(lat, info["lat"], abs_tol=0.0001)
                    and math.isclose(lon, info["lon"], abs_tol=0.0001)
                ):
                    found[site] = {
                        "ndvi": float(row["ndvi_median"]),
                        "precip": float(row["precip_median_mm_hr"]),
                        "original_lst": float(row["lst_night_median_k"]),
                    }

    missing = set(SITES) - set(found)

    if missing:
        raise ValueError(
            "Could not find original feature rows for: "
            + ", ".join(sorted(missing))
        )

    return found


# ---------------------------------------------------------
# 4. Read the existing QC tier summaries
# ---------------------------------------------------------

def read_qc_summaries():
    """Read the site-level medians already produced by qc_site_tiers.py."""

    if not QC_CSV.is_file():
        raise FileNotFoundError(f"Missing file: {QC_CSV}")

    summaries = {}

    with QC_CSV.open(
        "r", newline="", encoding="utf-8-sig"
    ) as fh:
        reader = csv.DictReader(fh)

        for row in reader:
            key = (row["site"], row["tier"])

            summaries[key] = {
                "kind": row["kind"],
                "n_pixels": int(row["n_pixels"]),
                "n_kept": int(row["n_kept"]),
                "median_k": (
                    float(row["median_k"])
                    if row["median_k"].strip()
                    else None
                ),
            }

    expected_tiers = {"T0", "T1", "T2", "T4", "T5", "X1"}

    for site in SITES:
        for tier in expected_tiers:
            if (site, tier) not in summaries:
                raise ValueError(
                    f"Missing QC summary for {site}, tier {tier}"
                )

    return summaries


# ---------------------------------------------------------
# 5. Reproduce the original scoring formula
# ---------------------------------------------------------

def calculate_score(ndvi, precip, lst):
    """Calculate the original three-feature weighted mean."""

    if ndvi is None or precip is None or lst is None:
        return None

    distances = {
        "ndvi_median": abs(ndvi) / SCALES["ndvi_median"],
        "precip_median_mm_hr": (
            max(0.0, precip) / SCALES["precip_median_mm_hr"]
        ),
        "lst_night_median_k": (
            max(0.0, lst - COLD_TARGET_K)
            / SCALES["lst_night_median_k"]
        ),
    }

    weighted_total = sum(
        WEIGHTS[name] * distances[name]
        for name in distances
    )

    weight_total = sum(WEIGHTS.values())

    return weighted_total / weight_total


# ---------------------------------------------------------
# 6. Generate the sensitivity results
# ---------------------------------------------------------

def build_results(original, qc):
    results = []

    for site, measurements in original.items():
        baseline = calculate_score(
            measurements["ndvi"],
            measurements["precip"],
            measurements["original_lst"],
        )

        expected = SITES[site]["published_score"]

        # Confirm that our reconstructed T0 formula matches
        # the score published by the original project.
        if abs(baseline - expected) > 0.000002:
            raise ValueError(
                f"{site} baseline mismatch: calculated "
                f"{baseline:.6f}, expected {expected:.6f}. "
                "Stop and investigate before using the results."
            )

        for tier in ("T0", "T1", "T2", "T4", "T5", "X1"):
            summary = qc[(site, tier)]
            lst = summary["median_k"]
            kept = summary["n_kept"]

            if lst is None or kept == 0:
                score = None
                delta = None
                status = "UNAVAILABLE"

            else:
                score = calculate_score(
                    measurements["ndvi"],
                    measurements["precip"],
                    lst,
                )

                delta = score - baseline

                if kept < MIN_PIXELS_FOR_STANDARD_SUPPORT:
                    status = "LOW_SUPPORT"
                else:
                    status = "OK"

            results.append({
                "site": site,
                "tier": tier,
                "kind": summary["kind"],
                "n_pixels": summary["n_pixels"],
                "n_kept": kept,
                "median_k": lst,
                "baseline_score": round(baseline, 6),
                "qc_score": (
                    round(score, 6) if score is not None else None
                ),
                "delta_score": (
                    round(delta, 6) if delta is not None else None
                ),
                "status": status,
            })

    return results


# ---------------------------------------------------------
# 7. Save the CSV and Markdown report
# ---------------------------------------------------------

def write_outputs(results):
    # Build the report text first so nothing is written if a check fails.
    report_text = build_report(results)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    columns = [
        "site",
        "tier",
        "kind",
        "n_pixels",
        "n_kept",
        "median_k",
        "baseline_score",
        "qc_score",
        "delta_score",
        "status",
    ]

    with OUT_CSV.open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    OUT_MD.write_text(report_text, encoding="utf-8")


# ---------------------------------------------------------
# 7b. Consistency check and report-building helpers
# ---------------------------------------------------------

def check_t0_matches_original(original, qc):
    """Stop if the T0 QC median differs from the original feature LST.

    T0 (valid LST only) should reproduce the original monthly aggregation.
    This check does not change any calculation or input.
    """

    for site, measurements in original.items():
        t0_median = qc[(site, "T0")]["median_k"]
        original_lst = measurements["original_lst"]

        if (
            t0_median is None
            or abs(t0_median - original_lst)
            > LST_MATCH_TOLERANCE_K + 1e-9
        ):
            raise ValueError(
                f"{site}: T0 QC median ({t0_median}) does not match the "
                f"original feature-table LST ({original_lst}). "
                "Stop and investigate before using the results."
            )


def check_report_assumptions(index):
    """Stop if the data no longer match what the report wording assumes.

    The narrative in this report was written for the June 2024 results.
    If the inputs change so that a sentence would become false, fail
    loudly instead of writing misleading text.
    """

    problems = []

    for tier in ("T1", "T2", "X1"):
        for site in SITES:
            row = index[(site, tier)]
            if row["n_kept"] != row["n_pixels"]:
                problems.append(f"{site} {tier} no longer retains all pixels")

    expected_status = [
        ("Kunlun", "T4", "LOW_SUPPORT"),
        ("Vinchina", "T4", "OK"),
        ("Kunlun", "T5", "OK"),
        ("Vinchina", "T5", "UNAVAILABLE"),
    ]
    for site, tier, status in expected_status:
        if index[(site, tier)]["status"] != status:
            problems.append(f"{site} {tier} status is not {status}")

    for site in SITES:
        if index[(site, "T4")]["n_kept"] > index[(site, "T2")]["n_kept"]:
            problems.append(f"{site} T4 kept more pixels than T2")
        if index[(site, "T5")]["n_kept"] > index[(site, "T1")]["n_kept"]:
            problems.append(f"{site} T5 kept more pixels than T1")

    for row in index.values():
        if row["median_k"] is not None and row["median_k"] <= COLD_TARGET_K:
            problems.append(
                f"{row['site']} {row['tier']} median is not above the "
                "LST target (linearity statement would not hold)"
            )

    if (
        index[("Kunlun", "T4")]["median_k"] is not None
        and index[("Kunlun", "T4")]["median_k"]
        <= index[("Kunlun", "T0")]["median_k"]
    ):
        problems.append("Kunlun T4 median did not rise relative to T0")

    if problems:
        raise ValueError(
            "The report wording assumes the June 2024 results. "
            "Revise build_report() before regenerating. Problems: "
            + "; ".join(problems)
        )


def pair_status(status_a, status_b):
    """Combine two per-site statuses into one pair-level status."""

    if "UNAVAILABLE" in (status_a, status_b):
        return "UNAVAILABLE"
    if "LOW_SUPPORT" in (status_a, status_b):
        return "LOW_SUPPORT"
    return "COMPARABLE"


def build_report(results):
    """Build the Markdown report text. Writes nothing to disk."""

    index = {(r["site"], r["tier"]): r for r in results}
    check_report_assumptions(index)

    def k(tier):
        return index[("Kunlun", tier)]

    def v(tier):
        return index[("Vinchina", tier)]

    def pct(row):
        return f'{100.0 * row["n_kept"] / row["n_pixels"]:g}%'

    def kept(row):
        return f'{row["n_kept"]}/{row["n_pixels"]}'

    def fmt_lst(value):
        return "N/A" if value is None else f"{value:.2f}"

    def fmt_score(value):
        return "N/A" if value is None else f"{value:.6f}"

    def fmt_delta(value):
        return "N/A" if value is None else f"{value:+.6f}"

    n = k("T0")["n_pixels"]

    # Slope of the score with respect to LST under the fixed formula.
    lst_slope = (
        WEIGHTS["lst_night_median_k"]
        / sum(WEIGHTS.values())
        / SCALES["lst_night_median_k"]
    )

    k4_shift = k("T4")["median_k"] - k("T0")["median_k"]
    v4_shift = v("T4")["median_k"] - v("T0")["median_k"]

    # Counts derived from tier counts only (T4 is a subset of T2 and
    # T5 is a subset of T1 by definition). No pixel-level data is read.
    k_error_cat1 = k("T2")["n_kept"] - k("T4")["n_kept"]
    v_error_cat1 = v("T2")["n_kept"] - v("T4")["n_kept"]
    k_bit2_set = k("T1")["n_kept"] - k("T5")["n_kept"]
    v_bit2_set = v("T1")["n_kept"] - v("T5")["n_kept"]

    # Cross-check the manually transcribed pixel values.
    pixels = MANUAL_KUNLUN_T4_PIXELS_K
    pixel_mean = sum(pixels) / len(pixels)
    if (
        len(pixels) != k("T4")["n_kept"]
        or abs(pixel_mean - k("T4")["median_k"])
        > LST_MATCH_TOLERANCE_K + 1e-9
    ):
        raise ValueError(
            "The manually transcribed Kunlun T4 pixel values do not match "
            "the T4 median/pixel count in the QC CSV. Stop and investigate."
        )

    t0_median = k("T0")["median_k"]
    both_above_t0 = all(p > t0_median for p in pixels)

    lines = [
        "# June 2024 QC Score Sensitivity",
        "",
        "## Purpose",
        "",
        "This analysis tests how MOD11C3 nighttime-LST QC tiers "
        "affect the original partial-match scores for Kunlun and "
        "Vinchina.",
        "",
        "It does not change the original feature table, weights, "
        "scoring code, or published rankings. Kunlun remains the "
        "discovery candidate and Vinchina the hold-out/control site; "
        "the QC tiers do not change those roles.",
        "",
        "The analysis covers June 2024 only. June 2024 is a single "
        "monthly composite, not a climate normal.",
        "",
        "## Headline result",
        "",
        "For June 2024, filtering MOD11C3 nighttime LST with T1, T2 "
        "or X1 left both candidate-site medians unchanged, because no "
        f"pixels were removed from either {n}-pixel site block. "
        f"Under T4, Vinchina retained {kept(v('T4'))} pixels "
        f"(median {v4_shift:+.2f} K), but Kunlun retained only "
        f"{kept(k('T4'))} ({pct(k('T4'))}) and its median rose by "
        f"{k4_shift:.2f} K; with so little support, this Kunlun value "
        f"is weakly supported. Under T5, Kunlun retained "
        f"{kept(k('T5'))} pixels and Vinchina none, so no two-site "
        "comparison is possible. The site comparison therefore "
        "depends on both the QC criterion and the spatial support "
        "remaining after filtering. These findings describe QC "
        "sensitivity in a single monthly composite. They do not show "
        "which filter is more accurate or which site is more suitable "
        "for a mission.",
        "",
        "## QC tier definitions",
        "",
        "| Tier | Rule | Role |",
        "|---|---|---|",
        "| T0 | Valid LST only | Baseline (original aggregation) |",
        "| T1 | T0 + mandatory QA in {0, 1} | Mandatory-QA filter |",
        "| T2 | T1 + LST error category <= 1 (estimated <= 2 K) | "
        "Stricter than T1 |",
        "| T4 | T1 + LST error category = 0 (estimated <= 1 K) | "
        "Alternative stricter filter |",
        "| T5 | T1 + QC bit 2 = 0 (L1B input data quality good) | "
        "Alternative stricter filter |",
        "| X1 | T2 + emissivity-consistency category != 3 | "
        "Exploratory only; not a primary filter |",
        "",
        "T4 and T5 are alternative stricter filters, not one "
        "sequential ladder. T3 is retired and is not used. QC values "
        "are always interpreted together with LST validity. QC "
        "categories are algorithm estimates, not validated "
        "ground-truth accuracy.",
        "",
        "## Fixed parameters",
        "",
        f"- Nighttime LST target: {COLD_TARGET_K} K",
        "- NDVI scale: 0.8304",
        "- Precipitation scale: 0.296 mm/hr",
        "- Nighttime LST scale: 86.2 K",
        "- Effective weights: 1 for each of the three features",
        "- Score denominator: 3",
        "",
        "The global target and normalization scales are held fixed "
        "to isolate the effect of changing candidate-site LST. Only "
        "the nighttime-LST input is replaced; NDVI and precipitation "
        "keep their original values.",
        "",
        "Because every LST median is above the target, the LST term "
        "rises linearly with temperature. With three equal weights, "
        "every score change in this report equals the LST median "
        f"change divided by {1.0 / lst_slope:.1f} (3 x 86.2), about "
        f"{lst_slope:.5f} score units per kelvin. The score changes "
        "are therefore linear rescalings of the LST changes under "
        "the fixed formula, not independent evidence beyond the "
        "temperature medians.",
        "",
        "## Results",
        "",
        "| Site | Tier | Kind | LST (K) | Pixels kept | Baseline | "
        "QC score | Delta | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]

    for row in results:
        lines.append(
            f'| {row["site"]} | {row["tier"]} | {row["kind"]} | '
            f'{fmt_lst(row["median_k"])} | '
            f'{kept(row)} ({pct(row)}) | '
            f'{row["baseline_score"]:.6f} | '
            f'{fmt_score(row["qc_score"])} | '
            f'{fmt_delta(row["delta_score"])} | {row["status"]} |'
        )

    lines.extend([
        "",
        "Status legend:",
        "",
        "- OK: at least "
        f"{MIN_PIXELS_FOR_STANDARD_SUPPORT} pixels retained. This is a "
        "reporting precaution only. It is not an official MODIS "
        "threshold, not a statistically validated confidence "
        "threshold, and not a statement about data quality.",
        "- LOW_SUPPORT: fewer than "
        f"{MIN_PIXELS_FOR_STANDARD_SUPPORT} pixels retained. The score "
        "is calculated but should be interpreted cautiously.",
        "- UNAVAILABLE: no retained LST pixels. The score is not "
        "estimated.",
        "",
        "A lower score means closer to the project's target conditions "
        "under the original normalized-distance definition. It does "
        "not mean a better site. A negative delta means the "
        "QC-adjusted score decreased (closer to the target); a "
        "positive delta means it increased (further from the target).",
        "",
        "## Site-score gap",
        "",
        "| Tier | Kunlun kept | Vinchina kept | Kunlun score | "
        "Vinchina score | Gap (Vinchina minus Kunlun) | Pair status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ])

    for tier in REPORT_TIER_ORDER:
        kr = k(tier)
        vr = v(tier)
        status = pair_status(kr["status"], vr["status"])

        if kr["qc_score"] is None or vr["qc_score"] is None:
            gap_text = "N/A"
        else:
            gap_text = f'{round(vr["qc_score"] - kr["qc_score"], 6):+.6f}'

        lines.append(
            f"| {tier} | {kept(kr)} | {kept(vr)} | "
            f'{fmt_score(kr["qc_score"])} | '
            f'{fmt_score(vr["qc_score"])} | {gap_text} | {status} |'
        )

    lines.extend([
        "",
        "The gap is computed from the six-decimal scores in "
        "`score_sensitivity_june2024.csv`, so it can be reproduced "
        "from that file. A negative gap means Vinchina's score is "
        "lower than Kunlun's.",
        "",
        "Pair status: COMPARABLE means only that both sites retained "
        "enough pixels to pass the reporting precaution; it does not "
        "mean the comparison is reliable or that either site is more "
        "suitable. LOW_SUPPORT means at least one site is below the "
        "precaution. UNAVAILABLE means at least one site has no "
        "retained pixels, so no gap exists.",
        "",
        "T1, T2 and X1 retained all pixels only for these two site "
        "blocks in June 2024, so their gaps equal the T0 gap. This "
        "says nothing about other grid cells or other months.",
        "",
        "## T4: Kunlun low-support case",
        "",
        f"Under T4, {k('T4')['n_kept']} of the {n} MODIS pixels in "
        f"Kunlun's project cell remain ({pct(k('T4'))} retention); "
        f"Vinchina retains {v('T4')['n_kept']} of {n} "
        f"({pct(v('T4'))}). The Kunlun T4 median is therefore based "
        "on two pixels, and the median of two values is simply their "
        "mean. This is a major limitation of the Kunlun T4 result, "
        "not a minor footnote.",
        "",
        f"The Kunlun T4 score ({fmt_score(k('T4')['qc_score'])}) is "
        "calculated with the original formula, but it rests on two "
        "pixels and should be interpreted cautiously. The T4 pair "
        "status is LOW_SUPPORT, and the T4 gap should not be read as "
        "a reliable site comparison.",
        "",
        "Unequal support: under T4 the two sites have very different "
        f"support ({kept(k('T4'))} versus {kept(v('T4'))}), so the T4 "
        "changes are not like-for-like. The larger Kunlun shift "
        f"({k4_shift:+.2f} K, against {v4_shift:+.2f} K at Vinchina) "
        "should not be read as Kunlun being intrinsically more "
        f"QC-sensitive: Kunlun lost {k('T0')['n_kept'] - k('T4')['n_kept']} "
        f"pixels and Vinchina lost {v('T0')['n_kept'] - v('T4')['n_kept']}.",
        "",
        "Which pixels were excluded (derived from the tier counts "
        "only; this script reads no pixel-level data): T1 and T2 "
        f"retained all {n} pixels at both sites, and T4 is a subset of "
        f"T2. The {k_error_cat1} Kunlun pixels excluded by T4 were "
        "therefore not excluded for failing mandatory QA; they have "
        "LST error category 1 (estimated <= 2 K) rather than "
        f"category 0 (estimated <= 1 K). At Vinchina, {v_error_cat1} "
        "pixel is excluded by T4 for the same reason.",
        "",
        "Retained Kunlun T4 pixel values:",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Retained pixel values (T4) | {pixels[0]:.2f} K, "
        f"{pixels[1]:.2f} K |",
        f"| Mean of the two (equals the T4 median) | "
        f"{pixel_mean:.2f} K |",
        f"| Original {n}-pixel median (T0) | {t0_median:.2f} K |",
        "",
        "Provenance: these two pixel values were manually transcribed "
        "from the earlier June 2024 HDF pixel inspection. They are "
        "not computed or generated by this script and are not a "
        "reproducible output of it. As a consistency check only, the "
        "script confirms that their mean matches the T4 median in the "
        "QC CSV.",
        "",
    ])

    if both_above_t0:
        lines.append(
            "Both retained values lie above the original T0 median. "
            "This is a descriptive observation about two pixels. It "
            "does not show that they are outliers or unrepresentative, "
            "which has not been tested."
        )
        lines.append("")

    lines.extend([
        "Pixels that pass a stricter filter are a selected subset of "
        "the block, not a random sample, so the T4 median describes "
        "that subset. It does not show that the original median was "
        "biased or that the T4 value is more accurate. Why particular "
        "pixels received a higher error category was not examined.",
        "",
        "## T5: no two-site comparison",
        "",
        f"Under T5, Kunlun retains {kept(k('T5'))} pixels "
        f"({pct(k('T5'))}; median {fmt_lst(k('T5')['median_k'])} K) "
        f"and Vinchina retains {kept(v('T5'))}. T5 is T1 plus QC bit 2 "
        f"= 0, and T1 retained all {n} Vinchina pixels, so all "
        f"{v_bit2_set} Vinchina pixels have QC bit 2 (L1B input data "
        f"quality) set to \"other\"; the same is true for "
        f"{k_bit2_set} of {n} Kunlun pixels (derived from tier "
        "counts). Why this flag is set on every Vinchina pixel was "
        "not investigated.",
        "",
        "Because no Vinchina pixels remain, no T5 Vinchina score or "
        "gap exists. T5 therefore cannot show which site has the "
        "lower score. Kunlun's T5 result is a Kunlun-only result. The "
        "T5 pair status is UNAVAILABLE.",
        "",
        "## What these results do and do not show",
        "",
        "They show how retained pixel support, nighttime-LST medians "
        "and the resulting scores for two site blocks depend on the "
        "chosen QC criterion in one monthly composite (June 2024).",
        "",
        "They do not show which filter is more accurate, and stricter "
        "QC does not automatically mean more accurate data. They do "
        "not show which site is more suitable for a mission, and they "
        "support no statistical significance claim.",
        "",
        "## Limitations",
        "",
        f"- Kunlun T4 retains {kept(k('T4'))} pixels ({pct(k('T4'))}), "
        "so its median and score have very limited spatial support.",
        "- Support is unequal between sites under T4, and the T5 "
        "comparison is impossible because Vinchina has no retained "
        "pixels.",
        "- Filtered pixels are a selected subset, not a random "
        "sample. QC categories are algorithm estimates and do not "
        "establish ground-truth accuracy.",
        "- June 2024 is a single monthly composite, not a climate "
        "normal and not independent daily observations.",
        "- T1, T2 and X1 retained all pixels only for these two site "
        "blocks in June 2024.",
        "- The LOW_SUPPORT limit of fewer than "
        f"{MIN_PIXELS_FOR_STANDARD_SUPPORT} pixels is a reporting "
        "precaution. It is not an official MODIS threshold or a "
        "statistically validated confidence threshold, and passing it "
        "does not make a median robust.",
        "- Neighboring pixels are not independent, so no significance "
        "claims are made from them.",
        "- The score is a partial-match heuristic, not a probability "
        "of mission success or a definitive site-suitability ranking. "
        "No rover field trial, site-access, safety or logistics "
        "assessment is included.",
        "",
        "## Methodological note",
        "",
        "- Tier rules follow `notes/qc-robustness-bit-definitions.md`. "
        "LST validity uses fill value 0, valid range 7500-65535 and "
        "scale factor 0.02.",
        "- 0.05 degree MODIS pixels are aggregated into 0.2 degree "
        f"project cells ({n} pixels per cell) using the median.",
        "- Monthly QC aggregation semantics are incompletely "
        "documented, so the exact meaning of a QC flag in a monthly "
        "composite is uncertain.",
        "- Clear-sky sampling can bias temperature relative to "
        "all-sky conditions, and rugged terrain and mixed surfaces "
        "complicate interpretation.",
        "- Baseline check: the script recomputes both original scores "
        "from the feature table and stops if either differs from the "
        "published score by more than 0.000002.",
        "- T0 consistency check: the script stops if the T0 QC median "
        "differs from the original feature-table LST by more than "
        f"{LST_MATCH_TOLERANCE_K} K.",
        "",
        "## Reproducibility",
        "",
        "Inputs:",
        "- `data/processed/features.csv`",
        "- `results/qc_robustness/site_tiers_june2024.csv`",
        "",
        "Run from the repository root:",
        "",
        "```",
        "python src/analyze_qc_score_sensitivity.py",
        "```",
        "",
        "Outputs: `score_sensitivity_june2024.csv` and this report, "
        "both in `results/qc_robustness/`.",
        "",
        "The two Kunlun T4 pixel values in this report are the one "
        "manually transcribed input; everything else is computed from "
        "the inputs above.",
        "",
        "Original scoring parameters are held fixed. Original "
        "project outputs are not overwritten.",
        "",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------
# 8. Main execution
# ---------------------------------------------------------

def main():
    original = read_original_features()
    qc = read_qc_summaries()

    check_t0_matches_original(original, qc)

    results = build_results(original, qc)
    write_outputs(results)

    print("QC score sensitivity analysis completed.")
    print()
    print(
        f'{"Site":9} {"Tier":5} {"Kept":7} '
        f'{"QC score":>10} {"Delta":>10} {"Status"}'
    )

    for row in results:
        score = (
            "N/A"
            if row["qc_score"] is None
            else f'{row["qc_score"]:.6f}'
        )
        delta = (
            "N/A"
            if row["delta_score"] is None
            else f'{row["delta_score"]:+.6f}'
        )

        kept = f'{row["n_kept"]}/{row["n_pixels"]}'

        print(
            f'{row["site"]:9} {row["tier"]:5} {kept:7} '
            f'{score:>10} {delta:>10} {row["status"]}'
        )

    print()
    print("Wrote:", OUT_CSV.relative_to(ROOT))
    print("Wrote:", OUT_MD.relative_to(ROOT))


if __name__ == "__main__":
    main()
