"""MCP server over the gold tables: natural-language access to the grid data.

    grid-mcp-server                 # stdio, what MCP hosts use

Tools read the same DuckDB marts as the dashboard, so answers always match
what the charts show.
"""
from __future__ import annotations

import datetime as dt
from typing import Annotated, Optional

import duckdb
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .carbon import KG_CO2_PER_MWH
from .config import DUCKDB_PATH

Ba = Annotated[str, Field(min_length=2, max_length=32,
                          description="EIA-930 balancing authority, e.g. 'PJM'")]
Days = Annotated[int, Field(ge=1, le=366, description="days of history")]


def _query(sql: str, params: list | None = None) -> list[dict]:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        cur = con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [{c: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v)
                 for c, v in zip(cols, row)} for row in cur.fetchall()]
    finally:
        con.close()


def create_server() -> FastMCP:
    mcp = FastMCP(
        "grid-intelligence",
        instructions=(
            "US grid and nuclear fleet data: hourly fuel mix and carbon "
            "intensity per balancing authority (EIA-930), daily reactor "
            "status and capacity factors (NRC), and demand-vs-weather. "
            "Carbon factors are static combustion-only averages."
        ),
    )

    @mcp.tool()
    def get_fuel_mix(ba: Ba, date: Optional[str] = None) -> dict:
        """Hourly generation by fuel (MW) for one day, latest day by default."""
        rows = _query(
            "select hour_ending_utc, fuel, mw from fct_fuel_mix_hourly "
            "where ba = ? and data_date = coalesce("
            "  ?::date, (select max(data_date) from fct_fuel_mix_hourly "
            "   where ba = ? and mw > 0)) "
            "order by hour_ending_utc, fuel",
            [ba.upper(), date, ba.upper()])
        return {"ba": ba.upper(), "rows": rows}

    @mcp.tool()
    def get_carbon_intensity(ba: Ba, days: Days = 30) -> dict:
        """Daily grid carbon intensity (kg CO2/MWh) and carbon-free share."""
        rows = _query(
            "select data_date, round(kg_co2_per_mwh, 1) as kg_co2_per_mwh, "
            "round(carbon_free_share, 3) as carbon_free_share "
            "from agg_carbon_intensity_daily where ba = ? and kg_co2_per_mwh is not null "
            "and data_date >= (select max(data_date) from agg_carbon_intensity_daily "
            "                 where ba = ?) - ? * interval '1 day' "
            "order by data_date",
            [ba.upper(), ba.upper(), days])
        return {"ba": ba.upper(), "days": days,
                "factors_kg_co2_per_mwh": KG_CO2_PER_MWH, "rows": rows}

    @mcp.tool()
    def get_reactor_fleet_status() -> dict:
        """Latest NRC report: percent power for every US power reactor."""
        rows = _query(
            "select unit, power_pct, down_date, reason_or_comment "
            "from fct_reactor_power_daily "
            "where report_date = (select max(report_date) from fct_reactor_power_daily) "
            "order by power_pct is null, power_pct desc, unit")
        return {"rows": rows}

    @mcp.tool()
    def get_reactor_capacity_factors(min_days: Days = 7) -> dict:
        """Average reported percent power per reactor (capacity-factor proxy)."""
        rows = _query(
            "select plant, unit, days_reported, avg_power_pct, days_at_zero "
            "from agg_reactor_capacity_factor where days_reported >= ? "
            "order by avg_power_pct asc",
            [min_days])
        return {"rows": rows}

    @mcp.tool()
    def get_demand_vs_weather(days: Days = 30) -> dict:
        """PJM daily demand vs local temperature."""
        rows = _query(
            "select data_date, round(avg_demand_mw, 0) as avg_demand_mw, "
            "round(peak_demand_mw, 0) as peak_demand_mw, "
            "round(avg_temp_c, 1) as avg_temp_c "
            "from agg_demand_vs_weather_daily "
            "order by data_date desc limit ?",
            [days])
        return {"rows": rows}

    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
