import numpy as np
import pytest

from src.export_map_data import NULL_I32, delta_micro, delta_tenths


def test_coordinate_deltas_round_trip_across_grid_gaps():
    coordinates = np.array([353, 353, 355, 0, -279], dtype="<i2")

    encoded = delta_tenths(coordinates, "latitude")

    assert np.array_equal(np.cumsum(encoded.astype(np.int32)), coordinates.astype(np.int32))


def test_measurement_deltas_preserve_nulls_and_restart_after_gaps():
    values = np.array([5, 7, NULL_I32, 3, 10, NULL_I32, NULL_I32, 4], dtype="<i4")

    encoded = delta_micro(values, "sample")
    restored = np.empty_like(values)
    previous = NULL_I32
    for index, delta in enumerate(encoded):
        restored[index] = NULL_I32 if delta == NULL_I32 else (
            delta if previous == NULL_I32 else previous + delta
        )
        previous = restored[index]

    assert np.array_equal(restored, values)


def test_coordinate_deltas_reject_values_that_overflow_int16(capsys):
    coordinates = np.array([-20000, 20000], dtype=np.int32)

    with pytest.raises(SystemExit):
        delta_tenths(coordinates, "latitude")
    assert "do not fit a 16-bit delta" in capsys.readouterr().err


def test_measurement_deltas_reject_values_that_overflow_int32(capsys):
    values = np.array([np.iinfo(np.int32).max, np.iinfo(np.int32).min + 1], dtype="<i4")

    with pytest.raises(SystemExit):
        delta_micro(values, "sample")
    assert "do not fit a 32-bit delta" in capsys.readouterr().err
