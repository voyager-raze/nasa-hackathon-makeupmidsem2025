"""Unit tests for src/mod11c3_qc.py using small synthetic values (no HDF file needed).

Run from the repository root:
    python -m unittest discover -s tests -p "test_mod11c3_qc.py" -v
"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mod11c3_qc as q  # noqa: E402

GOOD_LST = 15000  # 300.0 K, a valid stored value
FIELDS = ("mandatory_qa", "l1b_data_quality", "combined_use", "emis_consistency", "lst_error_category")
LADDER = ("T0", "T1", "T2", "T4", "T5")


def kept(qc_value, tier, lst=GOOD_LST):
    return bool(q.tier_mask(np.uint8(qc_value), np.uint16(lst), tier))


class DecodeTests(unittest.TestCase):
    def check(self, value, expected):
        f = q.decode_qc(np.uint8(value))
        self.assertEqual(tuple(int(f[k]) for k in FIELDS), expected, f"QC {value}")

    def test_field_names_are_exactly_the_documented_ones(self):
        self.assertEqual(tuple(q.decode_qc(np.uint8(0))), FIELDS)

    def test_observed_values(self):
        # (mandatory, L1B quality, combined-use, emissivity consistency, LST error category)
        self.check(13, (1, 1, 1, 0, 0))    # 0b00001101
        self.check(73, (1, 0, 1, 0, 1))    # 0b01001001
        self.check(77, (1, 1, 1, 0, 1))    # 0b01001101
        self.check(89, (1, 0, 1, 1, 1))    # 0b01011001
        self.check(105, (1, 0, 1, 2, 1))   # 0b01101001

    def test_each_field_isolated(self):
        self.check(0b00000011, (3, 0, 0, 0, 0))
        self.check(0b00000100, (0, 1, 0, 0, 0))
        self.check(0b00001000, (0, 0, 1, 0, 0))
        self.check(0b00110000, (0, 0, 0, 3, 0))
        self.check(0b11000000, (0, 0, 0, 0, 3))

    def test_extremes(self):
        self.check(0, (0, 0, 0, 0, 0))
        self.check(255, (3, 1, 1, 3, 3))

    def test_array_shape_preserved(self):
        f = q.decode_qc(np.array([[13, 73], [77, 89]], dtype=np.uint8))
        self.assertEqual(f["lst_error_category"].shape, (2, 2))

    def test_rejects_non_uint8(self):
        for bad in (np.array([13], dtype=np.int64), np.array([13.0]), np.array([13], dtype=np.int8)):
            with self.assertRaises(TypeError):
                q.decode_qc(bad)


class ValidityTests(unittest.TestCase):
    def test_fill_and_range_edges(self):
        raw = np.array([0, 1, 7499, 7500, 15000, 65535], dtype=np.uint16)
        self.assertEqual(q.lst_valid_mask(raw).tolist(), [False, False, False, True, True, True])

    def test_custom_fill_value(self):
        raw = np.array([7500, 8000], dtype=np.uint16)
        self.assertEqual(q.lst_valid_mask(raw, fill_value=8000).tolist(), [True, False])


class FillAndMandatoryTests(unittest.TestCase):
    def test_qc_zero_on_fill_pixel_is_never_good(self):
        for tier in (*q.TIERS, *q.EXPLORATORY_TIERS):
            self.assertFalse(kept(0, tier, lst=0), tier)

    def test_qc_zero_on_valid_pixel_is_kept_everywhere(self):
        for tier in (*q.TIERS, *q.EXPLORATORY_TIERS):
            self.assertTrue(kept(0, tier), tier)

    def test_mandatory_10_and_11_dropped_from_T1_up_but_not_T0(self):
        for value in (2, 3):
            self.assertTrue(kept(value, "T0"))
            for tier in ("T1", "T2", "T4", "T5", "X1"):
                self.assertFalse(kept(value, tier), (value, tier))

    def test_mandatory_01_is_kept_by_T1(self):
        self.assertTrue(kept(1, "T1"))


class TierTableTests(unittest.TestCase):
    # expected keep/drop for valid-LST pixels:   T0 T1 T2 T4 T5 X1
    EXPECTED = {
        13:  (1, 1, 1, 1, 0, 1),
        73:  (1, 1, 1, 0, 1, 1),
        77:  (1, 1, 1, 0, 0, 1),
        89:  (1, 1, 1, 0, 1, 1),
        105: (1, 1, 1, 0, 1, 1),   # emissivity category 2: kept (the retired T3 wrongly dropped it)
    }

    def test_observed_values_per_tier(self):
        for value, row in self.EXPECTED.items():
            got = tuple(int(kept(value, t)) for t in (*LADDER, "X1"))
            self.assertEqual(got, row, f"QC {value}")

    def test_combined_use_bit_is_ignored_by_every_tier(self):
        qc = np.arange(256, dtype=np.uint8)
        flipped = qc ^ np.uint8(0b00001000)
        lst = np.full(256, GOOD_LST, dtype=np.uint16)
        for tier in (*q.TIERS, *q.EXPLORATORY_TIERS):
            self.assertTrue(np.array_equal(q.tier_mask(qc, lst, tier), q.tier_mask(flipped, lst, tier)), tier)

    def test_emissivity_bits_are_ignored_by_the_primary_ladder(self):
        qc = np.arange(256, dtype=np.uint8)
        flipped = qc ^ np.uint8(0b00110000)
        lst = np.full(256, GOOD_LST, dtype=np.uint16)
        for tier in LADDER:
            self.assertTrue(np.array_equal(q.tier_mask(qc, lst, tier), q.tier_mask(flipped, lst, tier)), tier)

    def test_exploratory_X1_drops_only_emissivity_category_3(self):
        self.assertFalse(kept(0b00110000, "X1"))   # category 3, otherwise perfect
        self.assertTrue(kept(0b00110000, "T2"))
        for cat in (0, 1, 2):
            self.assertTrue(kept(cat << 4, "X1"), cat)

    def test_tiers_are_nested_as_designed(self):
        qc = np.arange(256, dtype=np.uint8)
        lst = np.full(256, GOOD_LST, dtype=np.uint16)
        m = {t: q.tier_mask(qc, lst, t) for t in (*q.TIERS, *q.EXPLORATORY_TIERS)}
        for inner, outer in (("T1", "T0"), ("T2", "T1"), ("T4", "T2"), ("T5", "T1"), ("X1", "T2")):
            self.assertFalse((m[inner] & ~m[outer]).any(), f"{inner} not within {outer}")

    def test_T3_is_retired_and_cannot_be_used_silently(self):
        self.assertNotIn("T3", q.TIERS)
        with self.assertRaises(ValueError) as ctx:
            q.tier_mask(np.uint8(0), np.uint16(GOOD_LST), "T3")
        self.assertIn("retired", str(ctx.exception))

    def test_unknown_tier_and_shape_mismatch(self):
        with self.assertRaises(ValueError):
            q.tier_mask(np.uint8(0), np.uint16(GOOD_LST), "T9")
        with self.assertRaises(ValueError):
            q.tier_mask(np.zeros(3, dtype=np.uint8), np.zeros(4, dtype=np.uint16), "T0")

    def test_no_description_claims_emissivity_error_thresholds(self):
        text = " ".join([*q.TIERS.values(), *q.EXPLORATORY_TIERS.values()])
        for bad in ("0.01", "0.02", "0.04", "emissivity error"):
            self.assertNotIn(bad, text)


class KelvinTests(unittest.TestCase):
    def test_scaling_and_nan_not_zero(self):
        raw = np.array([15000, 0, 12900], dtype=np.uint16)
        k = q.to_kelvin(raw, q.lst_valid_mask(raw))
        self.assertAlmostEqual(float(k[0]), 300.0)
        self.assertTrue(np.isnan(k[1]))
        self.assertAlmostEqual(float(k[2]), 258.0)


if __name__ == "__main__":
    unittest.main()
