# Grid Intelligence

[![Tests](https://github.com/anthony-marr/grid-intelligence/actions/workflows/tests.yml/badge.svg)](https://github.com/anthony-marr/grid-intelligence/actions/workflows/tests.yml)

A lakehouse-style pipeline over public US grid and nuclear fleet data. It
pulls EIA-930 hourly grid data, NRC Power Reactor Status Reports, and
Open-Meteo weather into bronze / silver / gold layers (DuckDB + dbt), and
serves the results through a dashboard and an MCP query layer. The angle is
nuclear fleet reliability and grid carbon intensity: what the PJM mix looked
like yesterday, which reactors were down, and how demand tracks temperature.

Started November 2026. Live demo: https://grid-intelligence-pjm.fly.dev/
(deployed on a scale-to-zero Fly machine; first load after idle takes a few
seconds). The deployed image carries a data snapshot, so "yesterday" advances
when a new image ships until scheduled ingest lands.

## How it fits together

```
 EIA-930 hourly balance         NRC Power Reactor        Open-Meteo archive
 (demand + generation by        Status Reports           (hourly temperature,
  fuel per balancing            (daily % power per        no key)
  authority; free bulk          US reactor, HTML
  CSVs, no key)                 tables)
        |                             |                        |
        v                             v                        v
 +------------------------- bronze: raw Parquet (replayable) -----------+
 |                    data/bronze/{eia930_balance,                     |
 |                     nrc_reactor_status, weather_hourly}             |
 +----------------------------------+----------------------------------+
                                    v
 +------------------------- dbt + DuckDB ------------------------------+
 |  staging: stg_eia930_balance, stg_nrc_reactor_status,               |
 |           stg_weather_hourly                                        |
 |  gold:    fct_fuel_mix_hourly, fct_reactor_power_daily,             |
 |           agg_carbon_intensity_daily,                               |
 |           agg_reactor_capacity_factor,                              |
 |           agg_demand_vs_weather_daily                               |
 +-----------+----------------------------+---------------------------+
             v                            v
 +------------------------+   +-----------------------------+
 |  FastAPI dashboard     |   |  MCP server (stdio)         |
 |  (REST + charts)       |   |  grid-intelligence tools    |
 +------------------------+   +-----------------------------+
```

Every raw row validates through the pydantic models in
`src/grid_intelligence/schemas.py` before it lands in bronze, so a surprise
column from EIA or a layout change on the NRC page fails at the boundary.

## Quickstart

```bash
pip install -r requirements-dev.txt
python -m pytest -q

# bronze: pull one week of PJM grid data, NRC fleet status, and DC weather
grid-ingest all --start 2026-11-02 --end 2026-11-08

# silver + gold: build the marts (DuckDB at data/grid.duckdb)
export GRID_BRONZE_DIR=$PWD/data/bronze GRID_DUCKDB_PATH=$PWD/data/grid.duckdb
dbt build --project-dir dbt --profiles-dir dbt

# serve the dashboard
grid-server            # http://localhost:8000
```

`grid-ingest` defaults to PJM (which covers DC); pass `--ba PJM,NYISO,MISO`
for more balancing authorities. The MCP server (`grid-mcp-server`) exposes
`get_fuel_mix`, `get_carbon_intensity`, `get_reactor_fleet_status`,
`get_reactor_capacity_factors`, and `get_demand_vs_weather` over the same
gold tables.

## Data sources (all public, all free)

- **EIA-930**: hourly demand and generation by fuel for every US balancing
  authority, rolling half-year CSVs, no key:
  https://www.eia.gov/electricity/930-content/about.html
- **NRC Power Reactor Status Reports**: daily percent power, outage dates,
  and comments for every US power reactor:
  https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/
- **Open-Meteo archive**: hourly temperature, no key (default location is
  downtown DC, inside the PJM footprint):
  https://open-meteo.com/en/docs/historical-weather-api

Carbon intensity is a combustion-only estimate using EIA electric-power-
sector average factors (coal 1025, natural gas 413, petroleum 1107 kg
CO2/MWh; `dbt/seeds/emission_factors.csv` documents each one). It is a mix
comparison metric, not a marginal-emissions claim.

## Notes and roadmap

- The current day's EIA-930 rows are partial until EIA finishes publishing,
  so "yesterday" is the most recent complete day on the dashboard.
- NRC capacity factors here are unweighted averages of reported percent
  power (a unit at 100% every day averages 100); nameplate weighting is a
  future step.
- Next: next-day PJM carbon-intensity forecasting from weather + history,
  GridStatus.io prices/fuel mix as an extra source (free API key), and
  scheduled daily ingest.
