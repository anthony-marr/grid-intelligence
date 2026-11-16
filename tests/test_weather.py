import datetime as dt

import pytest

from grid_intelligence.sources import weather


def test_parse_archive_payload():
    payload = {"hourly": {"time": ["2026-11-01T00:00", "2026-11-01T01:00"],
                          "temperature_2m": [7.5, 6.8]}}
    rows = weather.parse_archive_payload(payload)
    assert len(rows) == 2
    assert rows[0].ts_utc == dt.datetime(2026, 11, 1, 0, 0)
    assert rows[0].temperature_c == 7.5


def test_parse_archive_payload_empty():
    with pytest.raises(ValueError):
        weather.parse_archive_payload({"hourly": {"time": [], "temperature_2m": []}})


def test_parse_archive_payload_missing_temperature():
    # Open-Meteo returns null for a missing hour; it must land as None,
    # not fail validation of the whole payload.
    payload = {"hourly": {"time": ["2026-11-01T00:00", "2026-11-01T01:00"],
                          "temperature_2m": [7.5, None]}}
    rows = weather.parse_archive_payload(payload)
    assert len(rows) == 2
    assert rows[0].temperature_c == 7.5
    assert rows[1].temperature_c is None
