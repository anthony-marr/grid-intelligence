"""FastAPI dashboard over the gold (mart) tables in DuckDB.

    grid-server                      # serves on :8000

The dashboard (static/index.html) reads the JSON endpoints below. DuckDB is
opened read-only, so the API can sit next to a fresh `dbt build` without
locking the file.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import duckdb
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .config import DUCKDB_PATH

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Grid Intelligence", version="0.1.0")


def _query(sql: str, params: list | None = None) -> list[dict]:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        cur = con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        out = []
        for row in cur.fetchall():
            out.append({c: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v)
                        for c, v in zip(cols, row)})
        return out
    except duckdb.CatalogException as exc:
        raise HTTPException(
            503, f"mart tables not built yet - run dbt build ({exc})")
    finally:
        con.close()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/overview")
def overview() -> dict:
    return {
        "fuel_mix_days": _query(
            "select ba, min(data_date) as first_day, max(data_date) as last_day, "
            "count(distinct data_date) as days from fct_fuel_mix_hourly group by 1"),
        "reactor_reports": _query(
            "select min(report_date) as first_day, max(report_date) as last_day, "
            "count(distinct report_date) as days, count(distinct unit) as units "
            "from fct_reactor_power_daily"),
    }


@app.get("/api/mix")
def fuel_mix(ba: str = "PJM", date: dt.date | None = Query(None)) -> list[dict]:
    """Hourly fuel mix (MW) for one day; defaults to the latest loaded day."""
    if date is None:
        rows = _query("select max(data_date) from fct_fuel_mix_hourly "
                      "where ba = ? and mw > 0", [ba.upper()])
        date = dt.date.fromisoformat(rows[0]["max(data_date)"])
    return _query(
        "select hour_ending_utc, fuel, mw, demand_mw from fct_fuel_mix_hourly "
        "where ba = ? and data_date = ? order by hour_ending_utc, fuel",
        [ba.upper(), date])


@app.get("/api/carbon")
def carbon(ba: str = "PJM", days: int = Query(30, ge=1, le=366)) -> list[dict]:
    """Daily grid carbon intensity (kg CO2/MWh) and carbon-free share."""
    return _query(
        "select data_date, round(kg_co2_per_mwh, 1) as kg_co2_per_mwh, "
        "round(carbon_free_share, 3) as carbon_free_share, "
        "round(total_mwh, 0) as total_mwh "
        "from agg_carbon_intensity_daily where ba = ? and kg_co2_per_mwh is not null "
        "and data_date >= (select max(data_date) from agg_carbon_intensity_daily "
        "                 where ba = ?) - ? * interval '1 day' "
        "order by data_date",
        [ba.upper(), ba.upper(), days])


@app.get("/api/reactors/latest")
def reactors_latest() -> list[dict]:
    """Every reactor's status from the most recent NRC report."""
    return _query(
        "select unit, power_pct, down_date, reason_or_comment, change_in_report "
        "from fct_reactor_power_daily "
        "where report_date = (select max(report_date) from fct_reactor_power_daily) "
        "order by power_pct is null, power_pct desc, unit")


@app.get("/api/reactors/capacity")
def reactor_capacity(min_days: int = Query(7, ge=1)) -> list[dict]:
    """Average reported percent power per reactor over the loaded period."""
    return _query(
        "select plant, unit, days_reported, avg_power_pct, days_at_zero "
        "from agg_reactor_capacity_factor where days_reported >= ? "
        "order by avg_power_pct asc, unit",
        [min_days])


@app.get("/api/demand-weather")
def demand_weather(days: int = Query(30, ge=1, le=366)) -> list[dict]:
    """PJM daily demand vs local temperature (scatter data)."""
    return _query(
        "select data_date, round(avg_demand_mw, 0) as avg_demand_mw, "
        "round(peak_demand_mw, 0) as peak_demand_mw, "
        "round(avg_temp_c, 1) as avg_temp_c "
        "from agg_demand_vs_weather_daily where ba = 'PJM' "
        "and data_date >= (select max(data_date) from agg_demand_vs_weather_daily) "
        "        - ? * interval '1 day' "
        "order by data_date",
        [days])


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
