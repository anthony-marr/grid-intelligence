"""dbt/seeds/emission_factors.csv must mirror carbon.KG_CO2_PER_MWH.

The carbon gold model joins the hourly fuel mix to the dbt seed, while the
MCP server and Python callers read carbon.KG_CO2_PER_MWH. carbon.py's
docstring says to keep the two in sync; this test enforces it. It matters
because the SQL join is inner: a fuel present in the mix but missing from
the seed would silently drop its MWh from the carbon aggregate.
"""
import csv
from pathlib import Path

from grid_intelligence.carbon import KG_CO2_PER_MWH

SEED = Path(__file__).parent.parent / "dbt" / "seeds" / "emission_factors.csv"


def seed_factors() -> dict[str, float]:
    with open(SEED, newline="") as fh:
        return {row["fuel"]: float(row["kg_co2_per_mwh"])
                for row in csv.DictReader(fh)}


def test_seed_covers_exactly_the_python_fuels():
    assert set(seed_factors()) == set(KG_CO2_PER_MWH)


def test_seed_values_match_python():
    assert seed_factors() == KG_CO2_PER_MWH
