"""Ingest NRC Power Reactor Status Reports (bronze layer).

The NRC publishes one HTML page per day with a table of every US power
reactor's percent power, outage dates, and comments:
https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/

Each day's table lands as one Parquet file under
data/bronze/nrc_reactor_status/.
"""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

import duckdb
import httpx
import pyarrow as pa
from lxml import html as lxml_html

from ..config import (
    BRONZE_DIR, HTTP_TIMEOUT, NRC_STATUS_URL, USER_AGENT,
)
from ..schemas import NrcReactorStatusRow

_POLL_SECONDS = 0.25  # be polite to a .gov site


def parse_status_page(html_text: str,
                      report_date: dt.date) -> list[NrcReactorStatusRow]:
    """Parse every reactor status table in one daily report page.

    The report splits the fleet into several tables (by NRC region); each
    has Unit / Power / Down / Reason or Comment / Change / Scrams headers,
    and may include spacer rows with fewer cells.
    """
    doc = lxml_html.fromstring(html_text)
    rows: list[NrcReactorStatusRow] = []
    for table in doc.iter("table"):
        headers = [h.text_content().strip().lower()
                   for h in table.iter("th")]
        if len(headers) < 2 or "unit" not in headers[0] or "power" not in headers[1]:
            continue
        for tr in table.iter("tr"):
            cells = [c.text_content().strip() for c in tr.iter("td")]
            if len(cells) < 2 or not cells[0]:
                continue
            power_raw = cells[1]
            try:
                power = float(power_raw) if power_raw else None
            except ValueError:
                continue  # header-repeat or notes row
            rows.append(NrcReactorStatusRow(
                report_date=report_date,
                unit=cells[0],
                power_pct=power,
                down_date=cells[2] or None if len(cells) > 2 else None,
                reason_or_comment=cells[3] or None if len(cells) > 3 else None,
                change_in_report=cells[4] or None if len(cells) > 4 else None,
                scrams=cells[5] or None if len(cells) > 5 else None,
            ))
    if not rows:
        raise ValueError(f"no reactor status table found for {report_date}")
    return rows


def fetch_status_page(report_date: dt.date,
                      timeout: float = HTTP_TIMEOUT) -> str | None:
    """Fetch one daily report page; None if the NRC has not published it."""
    url = NRC_STATUS_URL.format(
        year=report_date.year, yyyymmdd=report_date.strftime("%Y%m%d"))
    resp = httpx.get(url, timeout=timeout,
                     headers={"User-Agent": USER_AGENT},
                     follow_redirects=True)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.text


def ingest_day(report_date: dt.date, dest_dir: Path = BRONZE_DIR,
               client_html: str | None = None) -> Path | None:
    """Fetch, parse, and bronze-load one day's reactor status report."""
    html_text = client_html if client_html is not None else fetch_status_page(report_date)
    if html_text is None:
        return None
    rows = parse_status_page(html_text, report_date)
    dest_dir = Path(dest_dir) / "nrc_reactor_status"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{report_date.isoformat()}.parquet"
    con = duckdb.connect()
    con.register("status_rows", pa.Table.from_pylist([r.model_dump() for r in rows]))
    con.execute(f"""
        COPY (SELECT * FROM status_rows)
        TO '{dest}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    return dest


def ingest(start: dt.date, end: dt.date,
           dest_dir: Path = BRONZE_DIR) -> list[Path]:
    """Bronze-load every published daily report in [start, end]."""
    written = []
    day = start
    while day <= end:
        dest = ingest_day(day, dest_dir)
        if dest is not None:
            written.append(dest)
        day += dt.timedelta(days=1)
        time.sleep(_POLL_SECONDS)
    return written
