import duckdb


def test_marts_built(duckdb_path):
    con = duckdb.connect(str(duckdb_path), read_only=True)
    mix = con.execute(
        "select fuel, mw from fct_fuel_mix_hourly where ba = 'PJM' "
        "and hour_ending_utc = '2026-11-01 05:00:00'").fetchall()
    fuels = dict(mix)
    assert fuels["nuclear"] == 30000.0
    assert fuels["coal"] == 20000.0

    carbon = con.execute(
        "select round(kg_co2_per_mwh, 1), round(carbon_free_share, 3) "
        "from agg_carbon_intensity_daily where ba = 'PJM'").fetchone()
    # daily sums across the two fixture hours
    coal, gas, nuc, petro = 20000 + 19000, 25000 + 24000, 30000 + 30000, 100 + 50
    hydro, pumped = 2000 + 2000, -500 - 400
    solar, wind, batt = 15 + 0, 1500 + 1600, 50 + 60
    other, unknown = 300 + 290, 5 + 0
    total = coal + gas + nuc + petro + hydro + pumped + solar + wind + batt + other + unknown
    expected = (coal * 1025 + gas * 413 + petro * 1107 + other * 413) / total
    assert carbon[0] == round(expected, 1)
    assert carbon[1] == round((nuc + hydro + solar + wind) / total, 3)

    cap = con.execute(
        "select unit, avg_power_pct, days_at_zero from agg_reactor_capacity_factor "
        "order by unit").fetchall()
    assert ("Calvert Cliffs 2", 0.0, 1) in cap

    dw = con.execute("select avg_temp_c from agg_demand_vs_weather_daily").fetchone()
    assert dw[0] == 7.15
