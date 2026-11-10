import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from grid_intelligence.sources import eia930, nrc, weather  # noqa: E402

FIXTURES = Path(__file__).parent / "data"
DBT_DIR = Path(__file__).parent.parent / "dbt"


@pytest.fixture(scope="session")
def bronze_dir(tmp_path_factory):
    """Bronze Parquet built from local fixtures (no network)."""
    dest = tmp_path_factory.mktemp("bronze")
    eia930.ingest_balance_csv(FIXTURES / "sample_eia930_balance.csv",
                              ("PJM",), dest)
    nrc.ingest_day(dt.date(2026, 11, 1), dest,
                   client_html=(FIXTURES / "sample_nrc_status.html").read_text())
    payload = {
        "hourly": {
            "time": ["2026-11-01T00:00", "2026-11-01T01:00"],
            "temperature_2m": [7.5, 6.8],
        }
    }
    weather.ingest(dt.date(2026, 11, 1), dt.date(2026, 11, 1),
                   dest_dir=dest, payload=payload)
    return dest


@pytest.fixture(scope="session")
def duckdb_path(bronze_dir, tmp_path_factory):
    """Full dbt build over the fixture bronze layer."""
    db_path = tmp_path_factory.mktemp("duckdb") / "grid.duckdb"
    env = dict(os.environ, GRID_BRONZE_DIR=str(bronze_dir),
               GRID_DUCKDB_PATH=str(db_path))
    result = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "build",
         "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)],
        env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    return db_path
