"""Configuration: data paths, source URLs, and defaults (env-overridable)."""
from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("GRID_DATA_DIR", "data"))
BRONZE_DIR = Path(os.environ.get("GRID_BRONZE_DIR", str(DATA_DIR / "bronze")))
RAW_DIR = Path(os.environ.get("GRID_RAW_DIR", str(DATA_DIR / "raw")))
DUCKDB_PATH = os.environ.get("GRID_DUCKDB_PATH", str(DATA_DIR / "grid.duckdb"))

# EIA-930 hourly grid data is published as rolling half-year CSV files, no key
# needed: https://www.eia.gov/electricity/930-content/about.html
EIA930_BALANCE_URL = (
    "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/"
    "EIA930_BALANCE_{year}_{half}.csv"
)
EIA930_HALVES = ("Jan_Jun", "Jul_Dec")
DEFAULT_BAS = tuple(
    b.strip() for b in os.environ.get("GRID_BAS", "PJM").split(",") if b.strip()
)

# NRC Power Reactor Status Reports: one HTML page per day with a table of
# every US reactor's percent power:
# https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/
NRC_STATUS_URL = (
    "https://www.nrc.gov/documents-reports/document-collections/"
    "events-reports-associated-with/power-reactor-status-reports/"
    "{year}/{yyyymmdd}ps"
)

# Open-Meteo historical weather (no key), used for demand-vs-weather analysis.
# Defaults to downtown Washington DC, inside the PJM footprint.
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_LATITUDE = float(os.environ.get("GRID_WEATHER_LAT", "38.9072"))
WEATHER_LONGITUDE = float(os.environ.get("GRID_WEATHER_LON", "-77.0369"))

HTTP_TIMEOUT = float(os.environ.get("GRID_HTTP_TIMEOUT", "120"))
USER_AGENT = "grid-intelligence/0.1 (personal data project)"
