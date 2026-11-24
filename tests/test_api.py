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


def test_fuel_mix_unknown_ba_returns_404(client):
    resp = client.get("/api/mix", params={"ba": "NOPE"})
    assert resp.status_code == 404


def test_fuel_mix_ba_is_case_insensitive(client):
    assert client.get("/api/mix", params={"ba": "pjm"}).json() == \
        client.get("/api/mix", params={"ba": "PJM"}).json()


def test_fuel_mix_explicit_date_without_data_is_empty(client):
    resp = client.get("/api/mix", params={"date": "1999-01-01"})
    assert resp.status_code == 200 and resp.json() == []


def test_reactor_capacity_min_days_filters_reactors(client):
    assert client.get("/api/reactors/capacity", params={"min_days": 1}).json()
    assert client.get("/api/reactors/capacity",
                      params={"min_days": 1000}).json() == []


def test_day_window_parameters_are_validated(client):
    assert client.get("/api/carbon", params={"days": 0}).status_code == 422
    assert client.get("/api/carbon", params={"days": 367}).status_code == 422
    assert client.get("/api/demand-weather",
                      params={"days": 0}).status_code == 422
