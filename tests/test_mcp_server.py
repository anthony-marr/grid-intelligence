import asyncio
import importlib
import json
import os

import pytest


@pytest.fixture(scope="module")
def server(duckdb_path):
    os.environ["GRID_DUCKDB_PATH"] = str(duckdb_path)
    import grid_intelligence.config as config
    importlib.reload(config)
    import grid_intelligence.mcp_server as mcp_server
    importlib.reload(mcp_server)
    return mcp_server.create_server()


def call(server, name, **args):
    result = asyncio.run(server.call_tool(name, args))
    # Depending on the mcp version, call_tool returns the content blocks,
    # or (content blocks, structured result). Tool output is JSON text.
    blocks = result[0] if isinstance(result, tuple) else result
    return json.loads(blocks[0].text)


def test_exposes_the_five_tools(server):
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert names == {"get_fuel_mix", "get_carbon_intensity",
                     "get_reactor_fleet_status",
                     "get_reactor_capacity_factors", "get_demand_vs_weather"}


def test_fuel_mix_uppercases_ba(server):
    out = call(server, "get_fuel_mix", ba="pjm")
    assert out["ba"] == "PJM" and out["rows"]


def test_fuel_mix_unknown_ba_is_empty(server):
    assert call(server, "get_fuel_mix", ba="NOPE")["rows"] == []


def test_carbon_intensity_includes_factors(server):
    out = call(server, "get_carbon_intensity", ba="PJM")
    assert out["factors_kg_co2_per_mwh"]["coal"] == 1025.0
    assert out["rows"] and out["rows"][0]["kg_co2_per_mwh"] > 0


def test_reactor_fleet_status_lists_reactors(server):
    assert len(call(server, "get_reactor_fleet_status")["rows"]) == 4


def test_days_out_of_range_is_rejected(server):
    with pytest.raises(Exception) as exc:
        call(server, "get_carbon_intensity", ba="PJM", days=0)
    assert "days" in str(exc.value)
