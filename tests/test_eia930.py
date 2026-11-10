import datetime as dt
from pathlib import Path

import duckdb

from grid_intelligence.sources import eia930

FIXTURES = Path(__file__).parent / "data"


def test_halves_for_range():
    assert eia930.halves_for_range(dt.date(2026, 3, 1), dt.date(2026, 4, 1)) == [
        (2026, "Jan_Jun")]
    assert eia930.halves_for_range(dt.date(2025, 6, 30), dt.date(2026, 7, 1)) == [
        (2025, "Jan_Jun"), (2025, "Jul_Dec"), (2026, "Jan_Jun"),
        (2026, "Jul_Dec")]


def test_ingest_balance_csv_filters_and_sums(tmp_path):
    dest = eia930.ingest_balance_csv(
        FIXTURES / "sample_eia930_balance.csv", ("PJM",), tmp_path)
    rows = duckdb.connect().execute(
        f"SELECT * FROM read_parquet('{dest}') ORDER BY hour_ending_utc"
    ).fetchdf().to_dict("records")
    assert len(rows) == 2  # ERCO row filtered out
    first = rows[0]
    assert first["balancing_authority"] == "PJM"
    assert first["data_date"].date() == dt.date(2026, 11, 1)
    assert first["hour_ending_utc"] == dt.datetime(2026, 11, 1, 5, 0)
    # solar with + without integrated battery storage are summed
    assert first["ng_solar_mw"] == 15.0
    assert first["ng_wind_mw"] == 1500.0
    # battery + other + unknown storage are summed
    assert first["ng_battery_storage_mw"] == 50.0
