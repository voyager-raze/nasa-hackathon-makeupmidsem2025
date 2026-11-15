from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src import download_monthly_range as downloader


class FakeGranule(dict):
    def __init__(self, filename: str, year: int, month: int):
        super().__init__()
        self.size = 10.0
        self._url = f"https://example.test/{filename}"
        self.update(
            {
                "umm": {
                    "TemporalExtent": {
                        "RangeDateTime": {
                            "BeginningDateTime": (
                                f"{year:04d}-{month:02d}-01T00:00:00Z"
                            )
                        }
                    }
                }
            }
        )

    def data_links(self) -> list[str]:
        return [self._url]


def fake_granule(short_name: str, year: int, month: int) -> FakeGranule:
    if short_name == "GPM_3IMERGM":
        name = (
            f"3B-MO.MS.MRG.3IMERG.{year}{month:02d}01-S000000-E235959."
            "06.V07B.HDF5"
        )
    else:
        doy = date(year, month, 1).timetuple().tm_yday
        name = f"{short_name}.A{year}{doy:03d}.061.fake.hdf"
    return FakeGranule(name, year, month)


def test_resolves_one_exactly_dated_granule_per_product_and_month():
    calls = []

    def search_data(**kwargs):
        calls.append(kwargs)
        year = int(kwargs["temporal"][0][:4])
        return [
            fake_granule(kwargs["short_name"], year, month)
            for month in range(1, 13)
        ]

    granules = downloader.resolve_monthly_granules(2019, 2019, search_data)

    assert len(granules) == 36
    assert len(calls) == 3
    assert calls[0]["temporal"] == ("2019-01", "2019-12")
    assert calls[0]["count"] == 13
    assert {call["short_name"] for call in calls} == {
        "MOD13C2",
        "MOD11C3",
        "GPM_3IMERGM",
    }


@pytest.mark.parametrize("match_count", [0, 2])
def test_rejects_missing_or_ambiguous_monthly_granules(match_count: int):
    def search_data(**kwargs):
        year = int(kwargs["temporal"][0][:4])
        granules = [
            fake_granule(kwargs["short_name"], year, month)
            for month in range(1, 13)
        ]
        if match_count == 0:
            return granules[1:]
        return [*granules, granules[0]]

    expected_error = (
        "CMR is missing MOD13C2 granules"
        if match_count == 0
        else "CMR returned multiple MOD13C2 granules"
    )
    with pytest.raises(ValueError, match=expected_error):
        downloader.resolve_monthly_granules(2019, 2019, search_data)


def test_download_preflight_stops_before_auth_or_transfer_when_a_month_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    def empty_search(**query):
        assert query["count"] == 13
        return []

    def unexpected_login(strategy: str, persist: bool):
        assert strategy in {"environment", "netrc"}
        assert not persist
        pytest.fail("login started before metadata preflight")

    def unexpected_download(granules, local_path, threads: int, force: bool):
        assert granules
        assert local_path == tmp_path
        assert threads == 4
        assert not force
        pytest.fail("download started with an incomplete range")

    monkeypatch.setattr(
        downloader.earthaccess,
        "search_data",
        empty_search,
    )
    monkeypatch.setattr(
        downloader.earthaccess,
        "login",
        unexpected_login,
    )
    monkeypatch.setattr(
        downloader.earthaccess,
        "download",
        unexpected_download,
    )

    with pytest.raises(ValueError, match="CMR is missing MOD13C2 granules"):
        downloader.download_range(2019, 2019, tmp_path)
