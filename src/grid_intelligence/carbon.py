"""Combustion-only CO2 factors per fuel, kg CO2 per MWh.

Sources: EIA, "How much carbon dioxide is produced per kilowatthour of U.S.
electricity generation?" (electric power sector averages): coal 2.26 lb/kWh,
natural gas 0.91 lb/kWh, petroleum 2.44 lb/kWh. 'Other fuel sources' is
assumed gas-like; 'unknown fuel sources' is excluded (treated as 0). These
are static national averages - good enough for mix comparisons, not for
marginal-emissions claims.

dbt/seeds/emission_factors.csv mirrors this table for the SQL models; keep
the two in sync.
"""
from __future__ import annotations

KG_CO2_PER_MWH: dict[str, float] = {
    "coal": 1025.0,
    "natural_gas": 413.0,
    "petroleum": 1107.0,
    "nuclear": 0.0,
    "hydropower": 0.0,
    "pumped_storage": 0.0,
    "solar": 0.0,
    "wind": 0.0,
    "battery_storage": 0.0,
    "geothermal": 0.0,
    "other": 413.0,
    "unknown": 0.0,
}


def weighted_carbon_intensity(mix_mwh: dict[str, float]) -> float | None:
    """kg CO2 per MWh for an energy mix {fuel: MWh}; None if no energy."""
    total = sum(v for v in mix_mwh.values() if v)
    if not total:
        return None
    emissions = sum((mix_mwh.get(fuel) or 0) * kg
                    for fuel, kg in KG_CO2_PER_MWH.items())
    return emissions / total
