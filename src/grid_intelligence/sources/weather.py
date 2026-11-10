"""Ingest Open-Meteo historical weather (bronze layer), no key needed.

Hourly temperature for the analysis location (default: downtown Washington
DC, inside the PJM footprint) feeds the demand-vs-weather gold model.
https://open-meteo.com/en/docs/historical-weather-api
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import duckdb
import httpx
import pyarrow as pa

from ..config import (
    BRONZE_DIR, HTTP_TIMEOUT, OPEN_METEO_ARCHIVE_URL, USER_AGENT,
    WEATHER_LATITUDE, WEATHER_LONGITUDE,
)
from ..schemas import WeatherHourRow


def fetch_hourly_temperature(
    start: dt.date,
    end: dt.date,
    latitude: float = WEATHER_LATITUDE,
    longitude: float = WEATHER_LONGITUDE,
    timeout: float = HTTP_TIMEOUT,
) -> list[WeatherHourRow]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": "temperature_2m",
        "timezone": "UTC",
    }
    resp = httpx.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=timeout,
                     headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return parse_archive_payload(resp.json())


def parse_archive_payload(payload: dict) -> list[WeatherHourRow]:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    rows = []
    for ts, temp in zip(times, temps):
        rows.append(WeatherHourRow(
            ts_utc=dt.datetime.fromisoformat(ts), temperature_c=temp))
    if not rows:
        raise ValueError("no hourly weather rows in payload")
    return rows


def ingest(start: dt.date, end: dt.date,
           latitude: float = WEATHER_LATITUDE,
           longitude: float = WEATHER_LONGITUDE,
           dest_dir: Path = BRONZE_DIR,
           payload: dict | None = None) -> Path:
    rows = (parse_archive_payload(payload) if payload is not None
            else fetch_hourly_temperature(start, end, latitude, longitude))
    dest_dir = Path(dest_dir) / "weather_hourly"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{latitude}_{longitude}_{start}_{end}.parquet"
    con = duckdb.connect()
    con.register("weather_rows", pa.Table.from_pylist([r.model_dump() for r in rows]))
    con.execute(f"""
        COPY (SELECT * FROM weather_rows)
        TO '{dest}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    return dest
