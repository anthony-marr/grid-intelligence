import datetime as dt
from pathlib import Path

import duckdb

from grid_intelligence.sources import nrc

FIXTURES = Path(__file__).parent / "data"


def test_parse_status_page():
    rows = nrc.parse_status_page(
        (FIXTURES / "sample_nrc_status.html").read_text(),
        dt.date(2026, 11, 1))
    assert len(rows) == 4
    bv1 = rows[0]
    assert bv1.unit == "Beaver Valley 1" and bv1.power_pct == 100
    cc2 = rows[2]
    assert cc2.power_pct == 0 and cc2.down_date == "10/30/2026"
    assert cc2.reason_or_comment == "Refueling Outage"


def test_ingest_day_writes_parquet(tmp_path):
    dest = nrc.ingest_day(dt.date(2026, 11, 1), tmp_path,
                          client_html=(FIXTURES / "sample_nrc_status.html").read_text())
    count = duckdb.connect().execute(
        f"SELECT count(*) FROM read_parquet('{dest}')").fetchone()[0]
    assert count == 4
