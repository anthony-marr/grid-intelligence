import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(duckdb_path):
    os.environ["GRID_DUCKDB_PATH"] = str(duckdb_path)
    import grid_intelligence.config as config
    importlib.reload(config)
    import grid_intelligence.api as api
    importlib.reload(api)
    return TestClient(api.app)


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_fuel_mix(client):
    rows = client.get("/api/mix").json()
    assert rows and rows[0]["fuel"]


def test_carbon(client):
    rows = client.get("/api/carbon").json()
    assert rows and rows[0]["kg_co2_per_mwh"] > 0


def test_reactors_latest(client):
    rows = client.get("/api/reactors/latest").json()
    assert len(rows) == 4


def test_demand_weather(client):
    rows = client.get("/api/demand-weather").json()
    assert rows and rows[0]["avg_temp_c"] in (7.1, 7.2)


def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200 and "Grid Intelligence" in resp.text
