"""Ingest EIA-930 hourly balance data (bronze layer).

EIA-930 publishes rolling half-year CSV files of hourly demand and generation
by fuel for every US balancing authority, no API key needed:
https://www.eia.gov/electricity/930-content/about.html

Raw CSVs are cached under data/raw (replayable), and the rows for the
configured balancing authorities land as Parquet under
data/bronze/eia930_balance/.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import duckdb
import httpx
from pydantic import ValidationError

from ..config import (
    BRONZE_DIR, DEFAULT_BAS, EIA930_BALANCE_URL, EIA930_HALVES,
    HTTP_TIMEOUT, RAW_DIR, USER_AGENT,
)
from ..schemas import Eia930BalanceRow

FUEL_SELECT = """
    "Balancing Authority" AS balancing_authority,
    strptime("Data Date", '%m/%d/%Y')::DATE AS data_date,
    strptime("UTC Time at End of Hour", '%m/%d/%Y %I:%M:%S %p')::TIMESTAMP
        AS hour_ending_utc,
    "Demand (MW)"::DOUBLE AS demand_mw,
    "Demand Forecast (MW)"::DOUBLE AS demand_forecast_mw,
    "Net Generation (MW)"::DOUBLE AS net_generation_mw,
    coalesce("Net Generation (MW) from Coal"::DOUBLE, 0) AS ng_coal_mw,
    coalesce("Net Generation (MW) from Natural Gas"::DOUBLE, 0)
        AS ng_natural_gas_mw,
    coalesce("Net Generation (MW) from Nuclear"::DOUBLE, 0) AS ng_nuclear_mw,
    coalesce("Net Generation (MW) from All Petroleum Products"::DOUBLE, 0)
        AS ng_petroleum_mw,
    coalesce("Net Generation (MW) from Hydropower Excluding Pumped Storage"::DOUBLE, 0)
        AS ng_hydropower_mw,
    coalesce("Net Generation (MW) from Pumped Storage"::DOUBLE, 0)
        AS ng_pumped_storage_mw,
    coalesce("Net Generation (MW) from Solar without Integrated Battery Storage"::DOUBLE, 0)
        + coalesce("Net Generation (MW) from Solar with Integrated Battery Storage"::DOUBLE, 0)
        AS ng_solar_mw,
    coalesce("Net Generation (MW) from Wind without Integrated Battery Storage"::DOUBLE, 0)
        + coalesce("Net Generation (MW) from Wind with Integrated Battery Storage"::DOUBLE, 0)
        AS ng_wind_mw,
    coalesce("Net Generation (MW) from Battery Storage"::DOUBLE, 0)
        + coalesce("Net Generation (MW) from Other Energy Storage"::DOUBLE, 0)
        + coalesce("Net Generation (MW) from Unknown Energy Storage"::DOUBLE, 0)
        AS ng_battery_storage_mw,
    coalesce("Net Generation (MW) from Geothermal"::DOUBLE, 0)
        AS ng_geothermal_mw,
    coalesce("Net Generation (MW) from Other Fuel Sources"::DOUBLE, 0)
        AS ng_other_mw,
    coalesce("Net Generation (MW) from Unknown Fuel Sources"::DOUBLE, 0)
        AS ng_unknown_mw
"""


def halves_for_range(start: dt.date, end: dt.date) -> list[tuple[int, str]]:
    """Half-year file keys covering [start, end]."""
    out = []
    for year in range(start.year, end.year + 1):
        for half in EIA930_HALVES:
            half_start = dt.date(year, 1 if half == "Jan_Jun" else 7, 1)
            half_end = dt.date(year, 6 if half == "Jan_Jun" else 12,
                               30 if half == "Jan_Jun" else 31)
            if half_end >= start and half_start <= end:
                out.append((year, half))
    return out


def download_balance_csv(year: int, half: str, dest_dir: Path = RAW_DIR,
                         timeout: float = HTTP_TIMEOUT) -> Path:
    """Download one half-year balance CSV (cached on disk for replay)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"EIA930_BALANCE_{year}_{half}.csv"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    url = EIA930_BALANCE_URL.format(year=year, half=half)
    with httpx.stream("GET", url, timeout=timeout,
                      headers={"User-Agent": USER_AGENT},
                      follow_redirects=True) as resp:
        resp.raise_for_status()
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_bytes():
                fh.write(chunk)
        tmp.rename(dest)
    return dest


def _validate_sample(parquet_path: Path, sample_size: int = 50) -> int:
    """Validate a sample of rows against the pydantic model; return row count."""
    con = duckdb.connect()
    total = con.execute(
        f"SELECT count(*) FROM read_parquet('{parquet_path}')").fetchone()[0]
    cur = con.execute(
        f"SELECT * FROM read_parquet('{parquet_path}') "
        f"USING SAMPLE {min(sample_size, total)} ROWS")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    for rec in rows:
        Eia930BalanceRow.model_validate(rec)
    return total


def ingest_balance_csv(csv_path: Path, bas: tuple[str, ...] = DEFAULT_BAS,
                       dest_dir: Path = BRONZE_DIR) -> Path:
    """Filter one raw balance CSV to the target BAs and write bronze Parquet."""
    csv_path = Path(csv_path)
    dest_dir = Path(dest_dir) / "eia930_balance"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (csv_path.stem + ".parquet")
    ba_list = ", ".join(f"'{b.upper()}'" for b in bas)
    con = duckdb.connect()
    con.execute(f"""
        COPY (
            SELECT {FUEL_SELECT}
            FROM read_csv_auto('{csv_path}', header=true, all_varchar=true)
            WHERE upper("Balancing Authority") IN ({ba_list})
        ) TO '{dest}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    total = _validate_sample(dest)
    if total == 0:
        raise ValueError(f"no rows for BAs {bas} in {csv_path}")
    return dest


def ingest(start: dt.date, end: dt.date, bas: tuple[str, ...] = DEFAULT_BAS,
           raw_dir: Path = RAW_DIR, dest_dir: Path = BRONZE_DIR) -> list[Path]:
    """Download and bronze-load every half-year file covering [start, end]."""
    written = []
    for year, half in halves_for_range(start, end):
        csv_path = download_balance_csv(year, half, raw_dir)
        written.append(ingest_balance_csv(csv_path, bas, dest_dir))
    return written
