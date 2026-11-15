"""Tests for src/qc_site_tiers.py using a synthetic 4x4 block (no real data needed).

Run from the repository root:
    python -m unittest discover -s tests -p "test_qc_site_tiers.py" -v
"""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import qc_site_tiers as s  # noqa: E402

# 8 pixels QC 73 @258.0 K, 4 pixels QC 13 @260.0 K, 4 pixels QC 105 @262.0 K
LST = [[12900] * 4, [12900] * 4, [13000] * 4, [13100] * 4]
QC = [[73] * 4, [73] * 4, [13] * 4, [105] * 4]


def by_tier(rows):
    return {r["tier"]: r for r in rows}


class SummaryTests(unittest.TestCase):
    def test_counts_and_medians(self):
        t = by_tier(s.tier_summary("Synthetic", LST, QC))
        self.assertEqual((t["T0"]["n_kept"], t["T0"]["median_k"]), (16, 259.0))   # mean of 258 and 260
        self.assertEqual((t["T1"]["n_kept"], t["T2"]["n_kept"], t["X1"]["n_kept"]), (16, 16, 16))
        self.assertEqual((t["T4"]["n_kept"], t["T4"]["median_k"]), (4, 260.0))     # only QC 13 (LST error <= 1 K)
        self.assertEqual((t["T5"]["n_kept"], t["T5"]["median_k"]), (12, 258.0))    # QC 73 and 105 (good L1B)
        self.assertEqual(t["T4"]["delta_vs_t0_k"], 1.0)
        self.assertEqual(t["T5"]["n_lost_vs_t0"], 4)

    def test_tier_keeping_nothing_gives_none_not_zero(self):
        t = by_tier(s.tier_summary("Synthetic", [[13000] * 4] * 4, [[13] * 4] * 4))
        self.assertEqual(t["T5"]["n_kept"], 0)
        self.assertIsNone(t["T5"]["median_k"])
        self.assertIsNone(t["T5"]["delta_vs_t0_k"])

    def test_fill_pixel_is_excluded_not_zero(self):
        lst = [[0, 12900, 12900, 12900]] + [[12900] * 4] * 3
        qc = [[0, 73, 73, 73]] + [[73] * 4] * 3
        t = by_tier(s.tier_summary("Synthetic", lst, qc))
        self.assertEqual(t["T0"]["n_kept"], 15)
        self.assertEqual(t["T0"]["median_k"], 258.0)

    def test_out_of_range_inputs_rejected(self):
        with self.assertRaises(ValueError):
            s.tier_summary("x", [[70000]], [[0]])
        with self.assertRaises(ValueError):
            s.tier_summary("x", [[12900]], [[300]])

    def test_pixel_table_matches_tiers(self):
        rows = s.pixel_table("Synthetic", LST, QC)
        self.assertEqual(len(rows), 16)
        self.assertEqual(sum(r["keep_T4"] for r in rows), 4)
        self.assertEqual({r["qc"] for r in rows if r["keep_T5"] == 0}, {13})
        self.assertTrue(all(r["combined_use"] == 1 for r in rows))   # bit 3 set in 73, 13 and 105


class GapAndRunTests(unittest.TestCase):
    def test_run_writes_csvs_and_checks_published_t0(self):
        blk_k = {"lst_raw": LST, "qc_raw": QC}                      # T0 median 259.0
        blk_v = {"lst_raw": [[12700] * 4] * 4, "qc_raw": [[13] * 4] * 4}  # 254.0 K, all QC 13
        rep = {"datasets": {"LST_Night_CMG": {"attrs": {"_FillValue": 0, "valid_range": [7500, 65535]}}},
               "sites": {"Kunlun": blk_k, "Vinchina": blk_v}}
        with tempfile.TemporaryDirectory() as d:
            jp = Path(d) / "in.json"
            jp.write_text(json.dumps(rep))
            summaries, gaps = s.run(jp, d, published={"Kunlun": 259.0, "Vinchina": 254.0})
            g = {r["tier"]: r for r in gaps}
            self.assertEqual(g["T0"]["gap_k"], -5.0)
            self.assertIsNone(g["T5"]["gap_k"])                     # Vinchina keeps nothing under T5
            self.assertTrue((Path(d) / "site_tiers_june2024.csv").exists())
            with open(Path(d) / "site_pixels_june2024.csv", newline="") as fh:
                self.assertEqual(len(list(csv.DictReader(fh))), 32)
            with self.assertRaises(SystemExit):                      # wrong published value must stop the run
                s.run(jp, d, published={"Kunlun": 258.8})


if __name__ == "__main__":
    unittest.main()
